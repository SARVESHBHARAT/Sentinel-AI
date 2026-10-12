import re

from sentinel.domain.enums import IncidentCategory, Severity, SeveritySource
from sentinel.schemas.incident import CreateIncident, IncidentUpdate


def _payload(title: str = "System produced an unsafe response") -> CreateIncident:
    return CreateIncident(
        title=title,
        description="The affected model generated output that requires review.",
        category=IncidentCategory.HARMFUL_OUTPUT,
        severity=Severity.HIGH,
        severity_source=SeveritySource.HUMAN,
        evidence_references=["case-42"],
    )


def test_create_retrieve_filter_and_update_incident(repository) -> None:
    created = repository.create_incident(_payload(), actor="intake@example.test")
    assert re.fullmatch(r"INC-\d{4}-0001", created.incident_id)
    assert created.status.value == "submitted"
    assert created.created_at.tzinfo is not None
    assert repository.list_evidence_references(created.incident_id) == ["case-42"]

    fetched = repository.get_incident(created.incident_id)
    assert fetched.title == created.title
    assert len(repository.list_incidents(category=IncidentCategory.HARMFUL_OUTPUT.value)) == 1

    updated = repository.update_incident(created.incident_id, IncidentUpdate(assigned_reviewer="Case Manager"), actor="manager")
    assert updated.assigned_reviewer == "Case Manager"
    assert updated.description == created.description


def test_identifier_increments_without_timestamp_dependence(repository) -> None:
    first = repository.create_incident(_payload("First"))
    second = repository.create_incident(_payload("Second"))
    assert first.incident_id.rsplit("-", 1)[0] == second.incident_id.rsplit("-", 1)[0]
    assert first.incident_id.endswith("0001")
    assert second.incident_id.endswith("0002")


def test_reset_demo_records_preserves_real_reports(repository) -> None:
    demo = repository.create_incident(_payload("[DEMO] Sample incident"), is_demo=True)
    real = repository.create_incident(_payload("User report"))
    assert repository.reset_demo_incidents() == 1
    assert repository.get_incident(real.incident_id).is_demo is False
    import pytest
    from sentinel.database.repositories import IncidentNotFoundError
    with pytest.raises(IncidentNotFoundError):
        repository.get_incident(demo.incident_id)
