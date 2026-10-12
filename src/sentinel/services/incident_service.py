from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import CategorySource, IncidentCategory, IncidentStatus, Severity, SeveritySource
from sentinel.schemas.incident import AIAssessment, CorrectiveAction, CreateIncident, Incident, IncidentUpdate, ReviewerNote


class IncidentService:
    """Business-facing interface used by UI pages and future APIs."""

    def __init__(self, repository: IncidentRepository) -> None:
        self._repository = repository

    def submit(self, payload: CreateIncident, actor: str | None = None) -> Incident:
        return self._repository.create_incident(payload, actor)

    def update(self, incident_id: str, changes: IncidentUpdate, actor: str | None = None) -> Incident:
        return self._repository.update_incident(incident_id, changes, actor)

    def transition(self, incident_id: str, status: IncidentStatus, actor: str | None = None) -> Incident:
        return self._repository.transition_status(incident_id, status, actor)

    def add_note(self, note: ReviewerNote) -> ReviewerNote:
        return self._repository.add_reviewer_note(note)

    def add_corrective_action(self, action: CorrectiveAction) -> CorrectiveAction:
        return self._repository.add_corrective_action(action)

    def review_ai_suggestion(
        self, incident_id: str, assessment: AIAssessment, *, category: IncidentCategory, severity: Severity,
        reviewer: str | None, justification: str | None,
    ) -> Incident:
        overridden = category != assessment.suggested_category or severity != assessment.suggested_severity
        if overridden and not (justification or "").strip():
            raise ValueError("A justification is required when overriding an AI suggestion")
        updated = self._repository.update_incident(
            incident_id,
            IncidentUpdate(
                category=category,
                category_source=CategorySource.HUMAN if category != assessment.suggested_category else CategorySource.AI_SUGGESTION,
                severity=severity,
                severity_source=SeveritySource.HUMAN if severity != assessment.suggested_severity else SeveritySource.AI_SUGGESTION,
                assigned_reviewer=reviewer or None,
            ),
            actor=reviewer or "Reviewer",
        )
        if overridden:
            self._repository.add_reviewer_note(ReviewerNote(
                incident_id=incident_id, author=reviewer or "Reviewer",
                body=f"AI triage override justification: {justification.strip()}",
            ))
        return updated
