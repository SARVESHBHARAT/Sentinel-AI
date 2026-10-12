import pytest

from sentinel.domain.enums import IncidentCategory, IncidentStatus
from sentinel.schemas.incident import CreateIncident


def _incident() -> CreateIncident:
    return CreateIncident(title="Availability failure", description="Service returned incorrect results for users.",
                          category=IncidentCategory.RELIABILITY)


def test_status_transition_lifecycle(repository) -> None:
    created = repository.create_incident(_incident())
    reviewing = repository.transition_status(created.incident_id, IncidentStatus.UNDER_REVIEW, actor="reviewer")
    required = repository.transition_status(reviewing.incident_id, IncidentStatus.ACTION_REQUIRED)
    resolved = repository.transition_status(required.incident_id, IncidentStatus.RESOLVED)
    closed = repository.transition_status(resolved.incident_id, IncidentStatus.CLOSED)
    assert closed.status == IncidentStatus.CLOSED


def test_invalid_status_transition_is_rejected(repository) -> None:
    created = repository.create_incident(_incident())
    with pytest.raises(ValueError, match="Cannot transition"):
        repository.transition_status(created.incident_id, IncidentStatus.CLOSED)
