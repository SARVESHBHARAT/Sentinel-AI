"""Model-intelligence + verification tests (Phase 6)."""
from datetime import date
import sqlite3

import pytest

from sentinel.ai.triage_service import AITriageService, DemoTriageProvider
from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory, Severity, SeveritySource, VerificationStatus
from sentinel.schemas.incident import CreateIncident
from sentinel.services.incident_service import IncidentService
from sentinel.services.model_intelligence_service import ModelIntelligenceService


def _payload(title="Model case", **overrides):
    base = dict(title=title, description="Detailed description of the event.",
                category=IncidentCategory.HARMFUL_OUTPUT)
    base.update(overrides)
    return CreateIncident(**base)


def test_migration_from_old_schema(tmp_path):
    """Old DB without new columns opens and backfills safely."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE incident_sequences (year INTEGER PRIMARY KEY, last_value INTEGER NOT NULL)")
    conn.execute("""CREATE TABLE incidents (incident_id TEXT PRIMARY KEY, title TEXT NOT NULL,
        description TEXT NOT NULL, category TEXT NOT NULL, category_source TEXT NOT NULL DEFAULT 'reporter',
        affected_system TEXT, provider TEXT, occurrence_date TEXT, report_date TEXT NOT NULL,
        severity TEXT, severity_source TEXT, potential_impact TEXT, affected_population TEXT,
        reporter_name TEXT, reporter_contact TEXT, anonymous_report INTEGER NOT NULL,
        assigned_reviewer TEXT, resolution_summary TEXT, status TEXT NOT NULL,
        is_demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE evidence_references (id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL, reference TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE ai_assessments (id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL, provider_mode TEXT NOT NULL, model_name TEXT NOT NULL,
        suggested_category TEXT NOT NULL, suggested_severity TEXT NOT NULL, risk_score INTEGER NOT NULL,
        confidence REAL NOT NULL, rationale TEXT NOT NULL, recommendations_json TEXT NOT NULL,
        concise_summary TEXT NOT NULL DEFAULT '', observed_failure_or_concern TEXT NOT NULL DEFAULT '',
        potential_harms_json TEXT NOT NULL DEFAULT '[]', affected_stakeholders_json TEXT NOT NULL DEFAULT '[]',
        evidence_json TEXT NOT NULL DEFAULT '[]', missing_information_json TEXT NOT NULL DEFAULT '[]',
        immediate_containment_steps_json TEXT NOT NULL DEFAULT '[]', corrective_actions_json TEXT NOT NULL DEFAULT '[]',
        urgent_human_review_recommended INTEGER NOT NULL DEFAULT 0, severity_explanation TEXT NOT NULL DEFAULT '',
        prompt_version TEXT NOT NULL DEFAULT 'legacy', created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE reviewer_notes (id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL, body TEXT NOT NULL, author TEXT, created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE corrective_actions (id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL, title TEXT NOT NULL, action_kind TEXT NOT NULL DEFAULT 'corrective',
        owner TEXT, status TEXT NOT NULL, due_date TEXT, evidence TEXT, created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL, event_type TEXT NOT NULL, actor TEXT, details TEXT, created_at TEXT NOT NULL)""")
    now = "2026-01-05T00:00:00+00:00"
    conn.execute("""INSERT INTO incidents (incident_id, title, description, category, report_date,
        anonymous_report, status, created_at, updated_at) VALUES
        ('INC-2026-0001', 'Legacy case', 'Legacy description.', 'harmful_unsafe_output',
         '2026-01-05', 0, 'submitted', ?, ?)""", (now, now))
    conn.commit()
    conn.close()
    repo = IncidentRepository(path)
    repo.initialize()  # must not destroy data
    incident = repo.get_incident("INC-2026-0001")
    assert incident.verification_status == VerificationStatus.REPORTED
    assert incident.affected_model_name is None
    cols = {row[1] for row in sqlite3.connect(path).execute("PRAGMA table_info(incidents)")}
    assert {"affected_model_name", "affected_model_version", "verification_status"} <= cols


def test_historical_record_defaults(repository):
    incident = repository.create_incident(_payload())
    assert incident.verification_status == VerificationStatus.REPORTED
    assert incident.affected_model_name is None


def test_model_and_version_persistence(repository):
    incident = repository.create_incident(_payload(
        provider="Acme", affected_model_name="acme-chat", affected_model_version="2026.01"))
    fetched = repository.get_incident(incident.incident_id)
    assert fetched.provider == "Acme"
    assert fetched.affected_model_name == "acme-chat"
    assert fetched.affected_model_version == "2026.01"


def test_assessment_model_separate_from_affected_model(repository):
    incident = repository.create_incident(_payload(
        provider="Acme", affected_model_name="acme-chat", affected_model_version="v1"))
    assessment = AITriageService(repository, DemoTriageProvider()).assess_incident(incident.incident_id)
    assert assessment.provider_mode == "demo"
    assert assessment.model_version == "sentinel-deterministic-demo-v1"
    fetched = repository.get_incident(incident.incident_id)
    assert fetched.affected_model_name == "acme-chat"
    assert assessment.model_name != fetched.affected_model_name


def test_grouping_by_provider_model_version(repository):
    repository.create_incident(_payload("A1", provider="Acme", affected_model_name="m1",
                                        affected_model_version="v1"))
    repository.create_incident(_payload("A2", provider="Acme", affected_model_name="m1",
                                        affected_model_version="v2"))
    repository.create_incident(_payload("B1", provider="Beta", affected_model_name="m1",
                                        affected_model_version="v1"))
    service = ModelIntelligenceService(repository)
    groups = service.groups()
    keys = {(group.provider, group.affected_model_name, group.affected_model_version) for group in groups}
    assert ("Acme", "m1", "v1") in keys
    assert ("Acme", "m1", "v2") in keys
    assert ("Beta", "m1", "v1") in keys


def test_counts_and_distributions(repository):
    repository.create_incident(_payload("S1", provider="Acme", affected_model_name="m",
                                        severity=Severity.HIGH, severity_source=SeveritySource.HUMAN))
    repository.create_incident(_payload("S2", provider="Acme", affected_model_name="m",
                                        severity=Severity.LOW, severity_source=SeveritySource.HUMAN))
    service = ModelIntelligenceService(repository)
    summary = service.summary()
    assert summary["total"] == 2
    assert summary["severity"] == {"high": 1, "low": 1}
    assert summary["category"]["harmful_unsafe_output"] == 2


def test_date_and_verification_filters(repository):
    first = repository.create_incident(_payload("Old", provider="Acme",
                                                report_date=date(2026, 1, 5)))
    repository.create_incident(_payload("New", provider="Acme", report_date=date(2026, 3, 5)))
    repository.transition_verification(first.incident_id, VerificationStatus.AI_ASSESSED)
    service = ModelIntelligenceService(repository)
    assert service.summary(date_from=date(2026, 3, 1))["total"] == 1
    assert service.summary(verification_status="ai_assessed")["total"] == 1
    assert service.summary(date_to=date(2026, 1, 31))["total"] == 1


def test_unknown_model_grouping(repository):
    repository.create_incident(_payload("No meta"))
    repository.create_incident(_payload("Named", provider="Acme", affected_model_name="m",
                                        affected_model_version="v9"))
    service = ModelIntelligenceService(repository)
    groups = service.groups()
    unknown = [group for group in groups if group.affected_model_name == "Unknown"]
    assert len(unknown) == 1 and unknown[0].total == 1
    named = [group for group in groups if group.affected_model_version == "v9"][0]
    assert named.total == 1


def test_empty_dataset(repository):
    service = ModelIntelligenceService(repository)
    assert service.summary() == {"total": 0, "severity": {}, "category": {},
                                 "verification_status": {}}
    assert service.groups() == []
    comparison = service.compare()
    assert comparison.sufficient_data is False
    assert "Insufficient data" in comparison.note


def test_insufficient_data_threshold(repository):
    repository.create_incident(_payload("Only one", provider="Acme"))
    comparison = ModelIntelligenceService(repository, min_sample=5).compare()
    assert comparison.sufficient_data is False
    assert comparison.total_matching_reports == 1
    assert "minimum required is 5" in comparison.note


def test_sufficient_data_comparison(repository):
    for index in range(5):
        repository.create_incident(_payload(f"Bulk {index}", provider="Acme"))
    comparison = ModelIntelligenceService(repository, min_sample=5).compare()
    assert comparison.sufficient_data is True
    assert "usage" in comparison.note.lower()
    assert "no usage denominator" in comparison.formula


def test_ai_triage_never_verifies(repository):
    incident = repository.create_incident(_payload("Triage flow"))
    AITriageService(repository, DemoTriageProvider()).assess_incident(incident.incident_id)
    fetched = repository.get_incident(incident.incident_id)
    assert fetched.verification_status == VerificationStatus.AI_ASSESSED


def test_verify_dispute_require_justification(repository):
    incident = repository.create_incident(_payload("Verify flow"))
    service = IncidentService(repository)
    repository.transition_verification(incident.incident_id, VerificationStatus.AI_ASSESSED)
    repository.transition_verification(incident.incident_id, VerificationStatus.HUMAN_REVIEWED)
    with pytest.raises(ValueError, match="justification"):
        service.verify(incident.incident_id, reviewer="R", justification=None)
    with pytest.raises(ValueError, match="reviewer"):
        service.verify(incident.incident_id, reviewer=None, justification="Confirmed.")
    verified = service.verify(incident.incident_id, reviewer="R", justification="Confirmed by logs.")
    assert verified.verification_status == VerificationStatus.VERIFIED
    with pytest.raises(ValueError, match="justification"):
        service.dispute(verified.incident_id, reviewer="R", justification=" ")
    disputed = service.dispute(verified.incident_id, reviewer="R2", justification="New evidence.")
    assert disputed.verification_status == VerificationStatus.DISPUTED


def test_invalid_verification_transition_rejected(repository):
    incident = repository.create_incident(_payload("Bad transition"))
    with pytest.raises(ValueError, match="Cannot transition verification"):
        repository.transition_verification(incident.incident_id, VerificationStatus.VERIFIED)


def test_verification_audit_events(repository):
    incident = repository.create_incident(_payload("Audit flow"))
    service = IncidentService(repository)
    repository.transition_verification(incident.incident_id, VerificationStatus.AI_ASSESSED)
    repository.transition_verification(incident.incident_id, VerificationStatus.HUMAN_REVIEWED)
    service.verify(incident.incident_id, reviewer="Auditor", justification="Confirmed.")
    events = repository.list_audit_events(incident.incident_id)
    verification_events = [event for event in events if event.event_type == "verification_changed"]
    assert len(verification_events) == 3
    assert verification_events[-1].details == "human_reviewed -> verified"


def test_assessment_history_append_only(repository):
    incident = repository.create_incident(_payload("History flow"))
    triage = AITriageService(repository, DemoTriageProvider())
    first = triage.assess_incident(incident.incident_id)
    second = triage.assess_incident(incident.incident_id)
    history = repository.list_ai_assessments(incident.incident_id)
    assert len(history) == 2
    assert history[0].model_version == first.model_version
    assert history[1].model_version == second.model_version



