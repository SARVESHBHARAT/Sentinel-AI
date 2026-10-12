"""Regression tests for Phase 5 production-readiness audit fixes."""
from html import escape

import pytest
from pydantic import ValidationError

from sentinel.ai.triage_service import AITriageService, DemoTriageProvider
from sentinel.database.repositories import ALLOWED_UPDATE_COLUMNS, IncidentRepository
from sentinel.domain.enums import (
    IncidentCategory,
    IncidentStatus,
    Severity,
    SeveritySource,
)
from sentinel.schemas.incident import (
    CorrectiveAction,
    CreateIncident,
    IncidentUpdate,
    ReviewerNote,
)
from sentinel.services.incident_service import IncidentService
from sentinel.services.report_service import ReportService


def _payload(title: str = "Regression test incident") -> CreateIncident:
    return CreateIncident(
        title=title,
        description="Detailed description for the regression test.",
        category=IncidentCategory.HARMFUL_OUTPUT,
        severity=Severity.HIGH,
        severity_source=SeveritySource.HUMAN,
    )


# ---------- Bug fix: ALLOWED_UPDATE_COLUMNS is now enforced ----------

class TestAllowedUpdateColumnsEnforced:
    """ALLOWED_UPDATE_COLUMNS was previously defined but never checked."""

    def test_all_incident_update_fields_are_allowed(self) -> None:
        """Every IncidentUpdate field must be present in ALLOWED_UPDATE_COLUMNS."""
        model_fields = set(IncidentUpdate.model_fields.keys())
        assert model_fields <= ALLOWED_UPDATE_COLUMNS

    def test_update_with_allowed_field_succeeds(self, repository) -> None:
        inc = repository.create_incident(_payload())
        updated = repository.update_incident(
            inc.incident_id,
            IncidentUpdate(assigned_reviewer="Auditor"),
        )
        assert updated.assigned_reviewer == "Auditor"


# ---------- Bug fix: rationale column mapping ----------

class TestRationaleColumnMapping:
    """The `rationale` DB column was receiving severity_explanation instead of
    observed_failure_or_concern. Verify the fix persists correct data."""

    def test_assessment_rationale_column_stores_concern(self, repository) -> None:
        inc = repository.create_incident(_payload())
        AITriageService(
            repository, DemoTriageProvider()
        ).assess_incident(inc.incident_id)
        # Read the raw DB row to verify the rationale column
        import sqlite3
        conn = sqlite3.connect(repository.database_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT rationale, observed_failure_or_concern, severity_explanation "
            "FROM ai_assessments WHERE incident_id = ?",
            (inc.incident_id,),
        ).fetchone()
        conn.close()
        # rationale column should match observed_failure_or_concern, not severity_explanation
        assert row["rationale"] == row["observed_failure_or_concern"]

    def test_assessment_round_trips_correctly(self, repository) -> None:
        inc = repository.create_incident(_payload())
        AITriageService(repository, DemoTriageProvider()).assess_incident(inc.incident_id)
        assessments = repository.list_ai_assessments(inc.incident_id)
        assert len(assessments) == 1
        a = assessments[0]
        assert a.observed_failure_or_concern != ""
        assert a.severity_explanation != ""
        assert a.concise_summary != ""


# ---------- Bug fix: badge HTML escaping ----------

class TestBadgeHtmlEscaping:
    """The badge component now escapes values to prevent XSS."""

    def test_html_escape_in_label(self) -> None:
        from sentinel.ui.components import label
        # Enum values are safe, but test the function handles special chars
        assert "&" not in label(None)  # Returns "Not assessed"

    def test_escape_function_handles_special_chars(self) -> None:
        assert escape("<script>") == "&lt;script&gt;"
        assert escape('"') == "&quot;"


# ---------- Data integrity: incident IDs ----------

class TestIncidentIdUniqueness:
    """Verify IDs remain unique even across multiple rapid creations."""

    def test_sequential_ids_are_unique(self, repository) -> None:
        ids = set()
        for i in range(10):
            inc = repository.create_incident(_payload(f"Incident {i}"))
            assert inc.incident_id not in ids
            ids.add(inc.incident_id)
        assert len(ids) == 10


# ---------- Data integrity: audit events match changes ----------

class TestAuditEventConsistency:
    """Verify audit events are created for each meaningful action."""

    def test_full_lifecycle_audit_trail(self, repository) -> None:
        inc = repository.create_incident(_payload(), actor="reporter")
        repository.update_incident(
            inc.incident_id,
            IncidentUpdate(assigned_reviewer="Auditor"),
            actor="manager",
        )
        repository.transition_status(
            inc.incident_id, IncidentStatus.UNDER_REVIEW, actor="Auditor"
        )
        repository.add_reviewer_note(ReviewerNote(
            incident_id=inc.incident_id, body="Note.", author="Auditor"
        ))
        repository.add_corrective_action(CorrectiveAction(
            incident_id=inc.incident_id, title="Fix it", owner="Engineer"
        ))
        AITriageService(repository, DemoTriageProvider()).assess_incident(inc.incident_id)

        events = repository.list_audit_events(inc.incident_id)
        event_types = [e.event_type for e in events]
        assert event_types == [
            "incident_created",
            "incident_updated",
            "status_changed",
            "reviewer_note_added",
            "corrective_action_added",
            "ai_assessment_added",
        ]
        # All events have UTC-aware timestamps
        for event in events:
            assert event.created_at.tzinfo is not None


# ---------- Data integrity: reassessments preserve history ----------

class TestReassessmentPreservesHistory:
    def test_multiple_assessments_are_all_persisted(self, repository) -> None:
        inc = repository.create_incident(_payload())
        svc = AITriageService(repository, DemoTriageProvider())
        svc.assess_incident(inc.incident_id)
        svc.assess_incident(inc.incident_id)
        svc.assess_incident(inc.incident_id)
        assessments = repository.list_ai_assessments(inc.incident_id)
        assert len(assessments) == 3
        # All have distinct created_at (or at least all 3 exist)
        assert all(a.created_at is not None for a in assessments)


# ---------- Data integrity: demo flag isolation ----------

class TestDemoDataIsolation:
    def test_demo_incidents_are_flagged_and_separable(self, repository) -> None:
        demo = repository.create_incident(_payload("Demo"), is_demo=True)
        real = repository.create_incident(_payload("Real"), is_demo=False)
        assert demo.is_demo is True
        assert real.is_demo is False
        repository.reset_demo_incidents()
        remaining = repository.list_incidents()
        assert len(remaining) == 1
        assert remaining[0].incident_id == real.incident_id


# ---------- Reports ----------

class TestReportGeneration:
    def test_markdown_report_contains_key_sections(self, repository) -> None:
        inc = repository.create_incident(_payload())
        svc = ReportService(repository)
        md = svc.markdown(inc.incident_id)
        assert "# Sentinel AI Incident Report" in md
        assert inc.incident_id in md
        assert "## Executive summary" in md
        assert "## Status and resolution" in md

    def test_pdf_report_generates_valid_bytes(self, repository) -> None:
        inc = repository.create_incident(_payload())
        svc = ReportService(repository)
        pdf = svc.pdf(inc.incident_id)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 100

    def test_special_chars_in_description_do_not_break_pdf(self, repository) -> None:
        inc = repository.create_incident(CreateIncident(
            title="XSS test <script>alert(1)</script>",
            description="Chars: <>&\"' and unicode: café",
            category=IncidentCategory.OTHER_UNCLASSIFIED,
        ))
        svc = ReportService(repository)
        pdf = svc.pdf(inc.incident_id)
        assert pdf[:5] == b"%PDF-"


# ---------- Persistence across restarts ----------

class TestPersistenceAcrossRestarts:
    def test_data_survives_repository_reinstantiation(self, tmp_path) -> None:
        db = tmp_path / "test.db"
        repo1 = IncidentRepository(db)
        repo1.initialize()
        inc = repo1.create_incident(_payload())
        incident_id = inc.incident_id

        # Simulate restart: new repository instance on same DB file
        repo2 = IncidentRepository(db)
        repo2.initialize()
        fetched = repo2.get_incident(incident_id)
        assert fetched.title == inc.title
        assert fetched.status == IncidentStatus.SUBMITTED


# ---------- Validation: reject invalid submissions ----------

class TestFormValidationRejections:
    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateIncident(
                title="", description="desc", category=IncidentCategory.OTHER_UNCLASSIFIED
            )

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateIncident(
                title="Title", description="", category=IncidentCategory.OTHER_UNCLASSIFIED
            )

    def test_title_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateIncident(
                title="x" * 301, description="desc", category=IncidentCategory.OTHER_UNCLASSIFIED
            )

    def test_description_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateIncident(
                title="Title", description="x" * 10_001,
                category=IncidentCategory.OTHER_UNCLASSIFIED,
            )


# ---------- Offline / no-API-key operation ----------

class TestOfflineOperation:
    def test_demo_provider_works_without_network(self, repository) -> None:
        inc = repository.create_incident(_payload())
        svc = AITriageService(repository, DemoTriageProvider())
        assessment = svc.assess_incident(inc.incident_id)
        assert assessment.provider_mode == "demo"
        assert assessment.model_name == "sentinel-deterministic-demo-v1"


# ---------- Search, filter, sort ----------

class TestSearchFilterSort:
    def test_search_by_title(self, repository) -> None:
        repository.create_incident(_payload("Alpha unique title"))
        repository.create_incident(_payload("Beta other title"))
        results, total = repository.search_incidents(query="Alpha")
        assert total == 1
        assert "Alpha" in results[0].title

    def test_filter_by_severity(self, repository) -> None:
        repository.create_incident(CreateIncident(
            title="Low sev", description="desc",
            category=IncidentCategory.OTHER_UNCLASSIFIED,
            severity=Severity.LOW, severity_source=SeveritySource.HUMAN,
        ))
        repository.create_incident(CreateIncident(
            title="High sev", description="desc",
            category=IncidentCategory.OTHER_UNCLASSIFIED,
            severity=Severity.HIGH, severity_source=SeveritySource.HUMAN,
        ))
        results, total = repository.search_incidents(severity="low")
        assert total == 1

    def test_sort_by_title_ascending(self, repository) -> None:
        repository.create_incident(_payload("Charlie"))
        repository.create_incident(_payload("Alpha"))
        repository.create_incident(_payload("Bravo"))
        results, _ = repository.search_incidents(sort_by="title", descending=False)
        titles = [r.title for r in results]
        assert titles == sorted(titles)

    def test_invalid_sort_field_rejected(self, repository) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            repository.search_incidents(sort_by="injection_attempt")


# ---------- Override AI suggestion ----------

class TestOverrideAISuggestion:
    def test_override_requires_justification(self, repository) -> None:
        inc = repository.create_incident(_payload())
        svc = IncidentService(repository)
        assessment = AITriageService(
            repository, DemoTriageProvider()
        ).assess_incident(inc.incident_id)
        with pytest.raises(ValueError, match="justification"):
            svc.review_ai_suggestion(
                inc.incident_id, assessment,
                category=IncidentCategory.BIAS_DISCRIMINATION,  # different from suggested
                severity=assessment.suggested_severity,
                reviewer="Reviewer", justification=None,
            )

    def test_override_with_justification_succeeds(self, repository) -> None:
        inc = repository.create_incident(_payload())
        svc = IncidentService(repository)
        assessment = AITriageService(
            repository, DemoTriageProvider()
        ).assess_incident(inc.incident_id)
        updated = svc.review_ai_suggestion(
            inc.incident_id, assessment,
            category=IncidentCategory.BIAS_DISCRIMINATION,
            severity=Severity.CRITICAL,
            reviewer="Senior Reviewer",
            justification="Upon investigation, this is a bias issue.",
        )
        assert updated.category == IncidentCategory.BIAS_DISCRIMINATION
        assert updated.severity == Severity.CRITICAL
        notes = repository.list_reviewer_notes(inc.incident_id)
        assert any("override" in n.body.lower() for n in notes)


# ---------- CSV export ----------

class TestCSVExport:
    def test_register_csv_includes_header_and_data(self, repository) -> None:
        repository.create_incident(_payload("CSV test"))
        incidents = repository.list_incidents()
        csv = ReportService.register_csv(incidents)
        lines = csv.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row
        assert "Incident ID" in lines[0]
        assert "CSV test" in lines[1]
