from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Protocol

from sentinel.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, assessment_input
from sentinel.config import Settings
from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory, Severity
from sentinel.schemas.incident import AIAssessment, AIModelAssessment, Incident


class TriageError(RuntimeError):
    """Safe error surfaced to the UI; raw provider details are intentionally not exposed."""


class TransientTriageError(TriageError):
    pass


class TriageProvider(Protocol):
    mode: str
    model_name: str

    def assess(self, incident: Incident, evidence_references: list[str]) -> AIModelAssessment: ...


@dataclass
class DemoTriageProvider:
    model_name: str = "sentinel-deterministic-demo-v1"
    mode: str = "demo"

    def assess(self, incident: Incident, evidence_references: list[str]) -> AIModelAssessment:
        text = f"{incident.title} {incident.description}".lower()
        category = IncidentCategory.OTHER_UNCLASSIFIED
        if any(word in text for word in ("privacy", "personal data", "leak", "exposed")):
            category = IncidentCategory.PRIVACY_DATA_LEAKAGE
        elif any(word in text for word in ("bias", "discriminat", "fairness")):
            category = IncidentCategory.BIAS_DISCRIMINATION
        elif any(word in text for word in ("security", "vulnerability", "exploit")):
            category = IncidentCategory.SECURITY_VULNERABILITY_ABUSE
        elif any(word in text for word in ("outage", "failure", "unavailable", "reliability")):
            category = IncidentCategory.RELIABILITY_SYSTEM_FAILURE
        severity = Severity.HIGH if any(word in text for word in ("critical", "many users", "sensitive")) else Severity.MEDIUM
        return AIModelAssessment(
            suggested_category=category, suggested_severity=severity, risk_score=65 if severity == Severity.HIGH else 40,
            confidence=0.55, concise_summary="Deterministic demo assessment based on report keywords.",
            observed_failure_or_concern="The submitted report describes a potential concern; it has not been independently verified.",
            potential_harms=["Potential user, organizational, or system impact requires human review."],
            affected_stakeholders=[incident.affected_population] if incident.affected_population else [],
            evidence=[], missing_information=["Scope, impact, and independent verification are not established by this demo assessment."],
            immediate_containment_steps=["Assign a reviewer and preserve available evidence."],
            recommended_corrective_actions=["Investigate the report and document a human determination."],
            urgent_human_review_recommended=severity == Severity.HIGH,
            severity_explanation="This advisory severity reflects reported keywords and uncertainty, not verified harm.",
        )


class OpenAITriageProvider:
    mode = "openai"

    def __init__(self, api_key: str, model_name: str, client: object | None = None) -> None:
        self.model_name = model_name
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, timeout=30.0, max_retries=0)
        except Exception as error:
            raise TriageError("AI triage is not available. Check the application configuration.") from error

    def assess(self, incident: Incident, evidence_references: list[str]) -> AIModelAssessment:
        try:
            completion = self._client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": assessment_input(incident, evidence_references)}],
                response_format=AIModelAssessment,
                temperature=0,
            )
            message = completion.choices[0].message
            if getattr(message, "refusal", None) or not getattr(message, "parsed", None):
                raise TriageError("The AI service could not produce a valid assessment.")
            return AIModelAssessment.model_validate(message.parsed)
        except TriageError:
            raise
        except Exception as error:
            name = type(error).__name__
            if name in {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}:
                raise TransientTriageError("AI triage is temporarily unavailable. Please try again shortly.") from error
            if name in {"AuthenticationError", "PermissionDeniedError"}:
                raise TriageError("AI triage is unavailable because its credentials are not configured correctly.") from error
            raise TriageError("AI triage could not complete. The incident was not changed.") from error


class AITriageService:
    def __init__(self, repository: IncidentRepository, provider: TriageProvider, retries: int = 2) -> None:
        self._repository, self._provider, self._retries = repository, provider, retries

    @classmethod
    def from_settings(cls, repository: IncidentRepository, settings: Settings) -> "AITriageService":
        provider: TriageProvider = DemoTriageProvider() if settings.effective_demo_mode else OpenAITriageProvider(settings.openai_api_key or "", settings.openai_model)
        return cls(repository, provider)

    def assess_incident(self, incident_id: str) -> AIAssessment:
        incident = self._repository.get_incident(incident_id)
        evidence = self._repository.list_evidence_references(incident_id)
        for attempt in range(self._retries + 1):
            try:
                output = AIModelAssessment.model_validate(self._provider.assess(incident, evidence))
                assessment = AIAssessment(incident_id=incident_id, provider_mode=self._provider.mode, model_name=self._provider.model_name, prompt_version=PROMPT_VERSION, **output.model_dump())
                return self._repository.add_ai_assessment(assessment)
            except TransientTriageError:
                if attempt == self._retries:
                    raise
                sleep(0.2 * (2 ** attempt))
        raise TriageError("AI triage could not complete.")
