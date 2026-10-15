from sentinel.domain.enums import IncidentStatus, VerificationStatus


#: Allowed verification-state transitions. Separate from the incident status
#: lifecycle; AI triage may never move an incident to ``verified``.
ALLOWED_VERIFICATION_TRANSITIONS: dict[VerificationStatus, set[VerificationStatus]] = {
    VerificationStatus.REPORTED: {VerificationStatus.AI_ASSESSED, VerificationStatus.HUMAN_REVIEWED, VerificationStatus.UNVERIFIED},
    VerificationStatus.AI_ASSESSED: {VerificationStatus.HUMAN_REVIEWED, VerificationStatus.DISPUTED, VerificationStatus.UNVERIFIED},
    VerificationStatus.HUMAN_REVIEWED: {VerificationStatus.VERIFIED, VerificationStatus.DISPUTED, VerificationStatus.UNVERIFIED},
    VerificationStatus.VERIFIED: {VerificationStatus.DISPUTED},
    VerificationStatus.DISPUTED: {VerificationStatus.HUMAN_REVIEWED, VerificationStatus.VERIFIED, VerificationStatus.UNVERIFIED},
    VerificationStatus.UNVERIFIED: {VerificationStatus.HUMAN_REVIEWED},
}


def can_verify(current: VerificationStatus, target: VerificationStatus) -> bool:
    return target in ALLOWED_VERIFICATION_TRANSITIONS[current]


def validate_verification_transition(current: VerificationStatus, target: VerificationStatus) -> None:
    if not can_verify(current, target):
        raise ValueError(f"Cannot transition verification from {current.value} to {target.value}")


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
