from sentinel.domain.enums import IncidentCategory, IncidentStatus
from sentinel.schemas.incident import CreateIncident, IncidentUpdate, ReviewerNote


def test_creation_and_meaningful_updates_are_audited(repository) -> None:
    created = repository.create_incident(
        CreateIncident(title="Data exposure", description="Potential exposed data needs investigation.", category=IncidentCategory.PRIVACY),
        actor="reporter",
    )
    repository.update_incident(created.incident_id, IncidentUpdate(assigned_reviewer="Priya"), actor="triage")
    repository.transition_status(created.incident_id, IncidentStatus.UNDER_REVIEW, actor="Priya")
    repository.add_reviewer_note(ReviewerNote(incident_id=created.incident_id, body="Initial review started.", author="Priya"))

    events = repository.list_audit_events(created.incident_id)
    assert [event.event_type for event in events] == [
        "incident_created", "incident_updated", "status_changed", "reviewer_note_added"
    ]
    assert all(event.created_at and event.created_at.tzinfo is not None for event in events)
