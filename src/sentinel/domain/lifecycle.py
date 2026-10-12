from sentinel.domain.enums import IncidentStatus


ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.SUBMITTED: {IncidentStatus.UNDER_REVIEW},
    IncidentStatus.UNDER_REVIEW: {IncidentStatus.ACTION_REQUIRED, IncidentStatus.RESOLVED},
    IncidentStatus.ACTION_REQUIRED: {IncidentStatus.UNDER_REVIEW, IncidentStatus.RESOLVED},
    IncidentStatus.RESOLVED: {IncidentStatus.CLOSED, IncidentStatus.ACTION_REQUIRED},
    IncidentStatus.CLOSED: set(),
}


def can_transition(current: IncidentStatus, target: IncidentStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def validate_transition(current: IncidentStatus, target: IncidentStatus) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Cannot transition incident from {current.value} to {target.value}")
