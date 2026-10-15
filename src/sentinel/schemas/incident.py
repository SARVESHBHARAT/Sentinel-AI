from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sentinel.domain.enums import CategorySource, IncidentCategory, IncidentStatus, Severity, SeveritySource, VerificationStatus

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(min_length=1, max_length=10_000)]
ModelName = Annotated[str, Field(min_length=1, max_length=200)]
ModelVersion = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")]


class CreateIncident(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: ShortText
    description: LongText
    category: IncidentCategory
    affected_system: str | None = Field(default=None, max_length=200)
    provider: str | None = Field(default=None, max_length=200)
    affected_model_name: ModelName | None = None
    affected_model_version: ModelVersion | None = None
    occurrence_date: date | None = None
    report_date: date = Field(default_factory=date.today)
    severity: Severity | None = None
    severity_source: SeveritySource | None = None
    potential_impact: str | None = Field(default=None, max_length=5_000)
    affected_population: str | None = Field(default=None, max_length=2_000)
    evidence_references: list[ShortText] = Field(default_factory=list, max_length=20)
    reporter_name: str | None = Field(default=None, max_length=150)
    reporter_contact: str | None = Field(default=None, max_length=254)
    anonymous_report: bool = False
    assigned_reviewer: str | None = Field(default=None, max_length=150)
    resolution_summary: str | None = Field(default=None, max_length=5_000)

    @model_validator(mode="after")
    def validate_reporter_and_severity(self) -> "CreateIncident":
        if self.anonymous_report and (self.reporter_name or self.reporter_contact):
            raise ValueError("Anonymous reports cannot include reporter details")
        if (self.severity is None) != (self.severity_source is None):
            raise ValueError("Severity and severity source must be supplied together")
        if self.occurrence_date and self.occurrence_date > self.report_date:
            raise ValueError("Occurrence date cannot be later than report date")
        if self.report_date > date.today():
            raise ValueError("Report date cannot be in the future")
        return self


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: ShortText | None = None
    description: LongText | None = None
    category: IncidentCategory | None = None
    category_source: CategorySource | None = None
    affected_system: str | None = Field(default=None, max_length=200)
    provider: str | None = Field(default=None, max_length=200)
    affected_model_name: ModelName | None = Field(default=None, max_length=200)
    affected_model_version: ModelVersion | None = Field(default=None, max_length=100)
    verification_status: VerificationStatus | None = None
    occurrence_date: date | None = None
    report_date: date | None = None
    severity: Severity | None = None
    severity_source: SeveritySource | None = None
    potential_impact: str | None = Field(default=None, max_length=5_000)
    affected_population: str | None = Field(default=None, max_length=2_000)
    assigned_reviewer: str | None = Field(default=None, max_length=150)
    resolution_summary: str | None = Field(default=None, max_length=5_000)


class Incident(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    title: str
    description: str
    category: IncidentCategory
    category_source: CategorySource = CategorySource.REPORTER
    affected_system: str | None
    provider: str | None
    affected_model_name: str | None = None
    affected_model_version: str | None = None
    verification_status: VerificationStatus = VerificationStatus.REPORTED
    occurrence_date: date | None
    report_date: date
    severity: Severity | None
    severity_source: SeveritySource | None
    potential_impact: str | None
    affected_population: str | None
    anonymous_report: bool
    reporter_name: str | None = None
    reporter_contact: str | None = None
    assigned_reviewer: str | None
    resolution_summary: str | None
    status: IncidentStatus
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime


class AssessmentEvidence(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    report_reference: ShortText
    interpretation: ShortText
    is_factual_observation: bool


class AIModelAssessment(BaseModel):
    """Model-produced fields; all claims must be scoped to the supplied report."""
    model_config = ConfigDict(str_strip_whitespace=True)

    suggested_category: IncidentCategory
    suggested_severity: Severity
    risk_score: int = Field(ge=1, le=100)
    confidence: float = Field(ge=0, le=1)
    concise_summary: ShortText
    observed_failure_or_concern: LongText
    potential_harms: list[ShortText] = Field(max_length=10)
    affected_stakeholders: list[ShortText] = Field(max_length=10)
    evidence: list[AssessmentEvidence] = Field(max_length=10)
    missing_information: list[ShortText] = Field(max_length=10)
    immediate_containment_steps: list[ShortText] = Field(max_length=10)
    recommended_corrective_actions: list[ShortText] = Field(max_length=10)
    urgent_human_review_recommended: bool
    severity_explanation: LongText


class AIAssessment(AIModelAssessment):
    incident_id: str
    provider_mode: str = Field(pattern="^(openai|demo)$")
    model_name: str = Field(min_length=1, max_length=100)
    # Exact version/snapshot of the *assessing* model (not the reported system).
    # None when the provider does not return reliable version evidence; never invented.
    model_version: str | None = Field(default=None, max_length=100)
    # Provider diagnostic fingerprint; stored separately, never presented as a version.
    system_fingerprint: str | None = Field(default=None, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)
    created_at: datetime | None = None


class ReviewerNote(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: str
    body: LongText
    author: str | None = Field(default=None, max_length=150)
    created_at: datetime | None = None


class CorrectiveAction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: str
    title: ShortText
    action_kind: str = Field(default="corrective", pattern="^(corrective|preventive)$")
    owner: str | None = Field(default=None, max_length=150)
    status: str = Field(default="open", pattern="^(open|in_progress|completed|cancelled)$")
    due_date: date | None = None
    evidence: str | None = Field(default=None, max_length=5_000)
    created_at: datetime | None = None


class AuditEvent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: str
    event_type: str = Field(min_length=1, max_length=80)
    actor: str | None = Field(default=None, max_length=150)
    details: str | None = Field(default=None, max_length=2_000)
    created_at: datetime | None = None
