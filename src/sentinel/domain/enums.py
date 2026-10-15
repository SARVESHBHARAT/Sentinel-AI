from enum import Enum


class IncidentCategory(str, Enum):
    HARMFUL_UNSAFE_OUTPUT = "harmful_unsafe_output"
    HALLUCINATION_MISINFORMATION = "hallucination_misinformation"
    PRIVACY_DATA_LEAKAGE = "privacy_data_leakage"
    BIAS_DISCRIMINATION = "bias_discrimination"
    SECURITY_VULNERABILITY_ABUSE = "security_vulnerability_abuse"
    RELIABILITY_SYSTEM_FAILURE = "reliability_system_failure"
    COPYRIGHT_IP_CONCERN = "copyright_ip_concern"
    OTHER_UNCLASSIFIED = "other_unclassified"
    # Backward-compatible aliases for early persisted and API values.
    HARMFUL_OUTPUT = "harmful_unsafe_output"
    PRIVACY = "privacy_data_leakage"
    DISCRIMINATION = "bias_discrimination"
    SECURITY = "security_vulnerability_abuse"
    RELIABILITY = "reliability_system_failure"
    OTHER = "other_unclassified"


class CategorySource(str, Enum):
    REPORTER = "reporter"
    AI_SUGGESTION = "ai_suggestion"
    HUMAN = "human"


class IncidentStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACTION_REQUIRED = "action_required"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeveritySource(str, Enum):
    HUMAN = "human"
    AI_SUGGESTION = "ai_suggestion"


class VerificationStatus(str, Enum):
    """Independent verification lifecycle (separate from IncidentStatus).

    Lifecycle: reported -> ai_assessed -> human_reviewed -> verified | disputed.
    ``unverified`` is a terminal marker for reports deemed not verifiable;
    historical rows lacking verification info are read as ``reported``.
    AI triage may only move reported/unverified -> ai_assessed, never to verified.
    """

    REPORTED = "reported"
    AI_ASSESSED = "ai_assessed"
    HUMAN_REVIEWED = "human_reviewed"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"
