"""Phase 7 integration tests: new UI wiring, services, hardening (no Streamlit runtime)."""
import pytest

from sentinel.config import Settings
from sentinel.domain.enums import IncidentCategory, Severity, SeveritySource, VerificationStatus
from sentinel.schemas.incident import CreateIncident
from sentinel.services.incident_service import IncidentService
from sentinel.services.model_intelligence_service import ModelIntelligenceService
from sentinel.services.report_service import ReportService


def _payload(title="Phase7 case", **overrides):
    base = dict(title=title, description="Detailed description for phase 7.",
                category=IncidentCategory.HARMFUL_OUTPUT)
    base.update(overrides)
    return CreateIncident(**base)


def test_submit_with_and_without_model_metadata(repository):
    with_model = repository.create_incident(_payload(
        "With model", provider="Acme", affected_model_name="acme-chat", affected_model_version="v2"))
    without_model = repository.create_incident(_payload("Without model"))
    assert repository.get_incident(with_model.incident_id).affected_model_version == "v2"
    assert repository.get_incident(without_model.incident_id).affected_model_name is None


def test_model_intelligence_compare_uses_filters(repository):
    repository.create_incident(_payload("Keep", provider="Acme", affected_model_name="m"))
    repository.create_incident(_payload("Skip", provider="Beta", affected_model_name="n"))
    service = ModelIntelligenceService(repository, min_sample=1)
    comparison = service.compare()
    assert comparison.sufficient_data is True
    assert comparison.total_matching_reports == 2
    assert {group.provider for group in comparison.groups} == {"Acme", "Beta"}
    filtered = service.summary(verification_status="reported")
    assert filtered["total"] == 2
    assert filtered["verification_status"] == {"reported": 2}


def test_verification_requires_reason_and_audits(repository):
    incident = repository.create_incident(_payload("Verify me"))
    service = IncidentService(repository)
    repository.transition_verification(incident.incident_id, VerificationStatus.AI_ASSESSED)
    repository.transition_verification(incident.incident_id, VerificationStatus.HUMAN_REVIEWED)
    try:
        service.verify(incident.incident_id, reviewer="R", justification=None)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    verified = service.verify(incident.incident_id, reviewer="R", justification="Checked logs.")
    assert verified.verification_status == VerificationStatus.VERIFIED
    events = repository.list_audit_events(incident.incident_id)
    assert any(event.event_type == "verification_changed" and "human_reviewed -> verified" in (event.details or "")
               for event in events)


def test_export_redaction_does_not_change_stored_data(repository):
    incident = repository.create_incident(_payload(
        "PII case", reporter_name="Ada", reporter_contact="ada@example.test"))
    service = ReportService(repository)
    redacted = service.markdown(incident.incident_id, redact_reporter=True)
    assert "[redacted]" in redacted and "ada@example.test" not in redacted
    plain = service.markdown(incident.incident_id)
    assert "ada@example.test" in plain
    assert repository.get_incident(incident.incident_id).reporter_contact == "ada@example.test"


def test_read_only_settings_flag_defaults_off():
    assert Settings.from_environment().read_only is False


def test_severity_filter_reaches_model_intelligence(repository):
    repository.create_incident(_payload("High", provider="Acme",
                                        severity=Severity.HIGH, severity_source=SeveritySource.HUMAN))
    repository.create_incident(_payload("Low", provider="Acme",
                                        severity=Severity.LOW, severity_source=SeveritySource.HUMAN))
    service = ModelIntelligenceService(repository)
    assert service.summary()["severity"] == {"high": 1, "low": 1}


def test_read_only_wrappers_block_every_write_path(repository):
    import app as sentinel_app
    from sentinel.domain.enums import IncidentStatus
    from sentinel.schemas.incident import CorrectiveAction, IncidentUpdate, ReviewerNote

    readonly_repo = sentinel_app._ReadOnlyRepository(repository.database_path)
    readonly_service = sentinel_app._ReadOnlyIncidentService(readonly_repo)
    incident = repository.create_incident(_payload("Writable seed"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.submit(_payload("Blocked"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.update(incident.incident_id, IncidentUpdate(title="Blocked"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.transition(incident.incident_id, IncidentStatus.UNDER_REVIEW)
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.verify(incident.incident_id, reviewer="R", justification="x")
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.dispute(incident.incident_id, reviewer="R", justification="x")
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.mark_unverified(incident.incident_id, reviewer="R", justification="x")
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.add_note(ReviewerNote(incident_id=incident.incident_id, body="Blocked note."))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.add_corrective_action(CorrectiveAction(incident_id=incident.incident_id, title="Blocked"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_service.review_ai_suggestion(incident.incident_id, None, category=IncidentCategory.HARMFUL_OUTPUT,
                                              severity=Severity.HIGH, reviewer="R", justification="x")
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.update_incident(incident.incident_id, IncidentUpdate(title="Blocked"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.add_ai_assessment(None)
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.add_reviewer_note(ReviewerNote(incident_id=incident.incident_id, body="Blocked"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.add_corrective_action(CorrectiveAction(incident_id=incident.incident_id, title="Blocked"))
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.transition_status(incident.incident_id, IncidentStatus.UNDER_REVIEW)
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.transition_verification(incident.incident_id, VerificationStatus.AI_ASSESSED)
    with pytest.raises(RuntimeError, match="Read-only"):
        readonly_repo.reset_demo_incidents()
    # Seeded record untouched.
    assert repository.get_incident(incident.incident_id).title == "Writable seed"


def test_backup_script_copies_database(tmp_path):
    import subprocess
    import sys

    source = tmp_path / "src.db"
    repo_module = __import__("sentinel.database.repositories", fromlist=["IncidentRepository"])
    repo = repo_module.IncidentRepository(source)
    repo.initialize()
    repo.create_incident(_payload("Backup me"))
    out_dir = tmp_path / "backups"
    completed = subprocess.run([sys.executable, "scripts/backup_db.py", "--db", str(source),
                                "--out-dir", str(out_dir), "--keep", "3"],
                               capture_output=True, text=True, cwd="d:\\Chrome Downloads\\ERA")
    assert completed.returncode == 0, completed.stderr
    assert len(list(out_dir.glob("sentinel-*.db"))) == 1

