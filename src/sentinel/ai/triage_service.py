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
    model_version: str | None
    system_fingerprint: str | None = None

    def assess(self, incident: Incident, evidence_references: list[str]) -> AIModelAssessment: ...


@dataclass
class DemoTriageProvider:
    model_name: str = "sentinel-deterministic-demo-v1"
    mode: str = "demo"
    model_version: str | None = "sentinel-deterministic-demo-v1"
    system_fingerprint: str | None = None

    def assess(self, incident: Incident, evidence_references: list[str]) -> AIModelAssessment:
        title = (incident.title or "").strip()
        description = (incident.description or "").strip()
        text = f"{title} {description}".lower()

        # 1. Category Detection based on domain keywords
        category = IncidentCategory.OTHER_UNCLASSIFIED

        if any(w in text for w in (
            "prompt injection", "jailbreak", "adversarial", "system prompt", "instruction bypass",
            "override", "rce", "remote code execution", "vulnerability", "exploit", "unauthorized access",
            "privilege escalation", "malicious prompt", "backdoor", "attack", "injection", "security"
        )):
            category = IncidentCategory.SECURITY_VULNERABILITY_ABUSE
        elif any(w in text for w in (
            "privacy", "pii", "personal data", "leak", "leakage", "exfiltrat", "exposed", "exposure",
            "credentials", "api key", "ssn", "secret", "private data", "sensitive customer", "sensitive data"
        )):
            category = IncidentCategory.PRIVACY_DATA_LEAKAGE
        elif any(w in text for w in (
            "harmful", "unsafe", "self-harm", "hate speech", "violence", "toxic", "dangerous",
            "harassment", "abusive", "weapon", "threat", "offensive", "illegal", "content moderation"
        )):
            category = IncidentCategory.HARMFUL_UNSAFE_OUTPUT
        elif any(w in text for w in (
            "hallucinat", "misinform", "false claim", "fabricated", "inaccurate", "untrue", "invented",
            "deceptive", "fake citation", "confabulat", "incorrect notice", "notice-period", "misinformation"
        )):
            category = IncidentCategory.HALLUCINATION_MISINFORMATION
        elif any(w in text for w in (
            "bias", "discriminat", "unfair", "prejudice", "racism", "sexist", "stereotyping",
            "disparate impact", "demographic", "fairness"
        )):
            category = IncidentCategory.BIAS_DISCRIMINATION
        elif any(w in text for w in (
            "copyright", "infringement", "intellectual property", "proprietary", "trademark", "plagiarism", "patent"
        )):
            category = IncidentCategory.COPYRIGHT_IP_CONCERN
        elif any(w in text for w in (
            "outage", "downtime", "crash", "latency", "timeout", "unavailable", "reliability",
            "formatting", "misalign", "malformed", "syntax error", "parsing error", "csv columns", "failure"
        )):
            category = IncidentCategory.RELIABILITY_SYSTEM_FAILURE
        elif incident.category and incident.category != IncidentCategory.OTHER_UNCLASSIFIED:
            category = incident.category

        # 2. Suggested Severity
        critical_keywords = (
            "critical", "rce", "remote code execution", "catastrophic", "all users", "emergency",
            "severe breach", "mass exposure", "unauthenticated", "safety-critical", "safety critical"
        )
        high_keywords = (
            "high", "prompt injection", "jailbreak", "adversarial", "exploit", "pii", "credentials",
            "exfiltration", "data leak", "harmful", "toxic", "violence", "many users", "sensitive",
            "production database", "legal liability", "regulatory"
        )
        low_keywords = (
            "minor", "low", "cosmetic", "formatting", "whitespace", "misalign", "typo",
            "isolated", "single user", "non-blocking", "non-critical", "csv"
        )

        has_critical = any(w in text for w in critical_keywords)
        has_high = any(w in text for w in high_keywords)
        has_low = any(w in text for w in low_keywords)

        if has_critical:
            severity = Severity.CRITICAL
        elif category in (IncidentCategory.SECURITY_VULNERABILITY_ABUSE, IncidentCategory.HARMFUL_UNSAFE_OUTPUT):
            if has_low and not has_high:
                severity = Severity.MEDIUM
            else:
                severity = Severity.HIGH
        elif category == IncidentCategory.PRIVACY_DATA_LEAKAGE:
            if has_low and not has_high:
                severity = Severity.MEDIUM
            else:
                severity = Severity.HIGH
        elif has_high:
            severity = Severity.HIGH
        elif has_low or (category == IncidentCategory.RELIABILITY_SYSTEM_FAILURE and any(w in text for w in ("formatting", "misalign", "csv", "typo", "cosmetic"))):
            severity = Severity.LOW
        else:
            severity = Severity.MEDIUM

        # 3. Deterministic Risk Score (1 to 100)
        base_risk = {
            Severity.CRITICAL: 88,
            Severity.HIGH: 72,
            Severity.MEDIUM: 45,
            Severity.LOW: 20,
        }[severity]

        category_risk_mod = {
            IncidentCategory.SECURITY_VULNERABILITY_ABUSE: 8,
            IncidentCategory.HARMFUL_UNSAFE_OUTPUT: 7,
            IncidentCategory.PRIVACY_DATA_LEAKAGE: 6,
            IncidentCategory.BIAS_DISCRIMINATION: 3,
            IncidentCategory.HALLUCINATION_MISINFORMATION: 2,
            IncidentCategory.COPYRIGHT_IP_CONCERN: 0,
            IncidentCategory.RELIABILITY_SYSTEM_FAILURE: -4,
            IncidentCategory.OTHER_UNCLASSIFIED: -5,
        }.get(category, 0)

        scope_mod = 0
        if incident.affected_population:
            scope_mod += 3
        if any(w in text for w in ("all users", "many users", "enterprise", "mass", "broad", "fleet")):
            scope_mod += 4
        elif any(w in text for w in ("isolated", "single user", "one user", "minor", "formatting")):
            scope_mod -= 4

        calculated_risk = base_risk + category_risk_mod + scope_mod
        risk_score = max(1, min(100, calculated_risk))

        # 4. Deterministic Confidence Score (0.0 to 1.0)
        text_len = len(text)
        if text_len < 30:
            confidence = 0.20
        elif text_len < 80:
            confidence = 0.40
        elif text_len < 160:
            confidence = 0.55
        elif text_len < 300:
            confidence = 0.68
        else:
            confidence = 0.78

        if incident.provider or incident.affected_model_name or incident.affected_system:
            confidence += 0.06
        if any(c in text for c in ('"', "'", "[", "]", "error:", "exception", "status code", "prompt:")):
            confidence += 0.05
        if evidence_references:
            confidence += min(0.08, len(evidence_references) * 0.04)
        if category == IncidentCategory.OTHER_UNCLASSIFIED:
            confidence -= 0.12

        confidence = max(0.10, min(0.92, round(confidence, 2)))

        if severity == Severity.CRITICAL:
            summary = "Critical severity indicated by potential system compromise or widespread severe harm."
            concern = "The report indicates high-impact failure characteristics that require immediate investigation; it has not been independently verified."
            explanation = "Elevated risk score reflects potential security breach, unsafe harm, or broad impact."
        elif severity == Severity.HIGH:
            summary = f"High severity assessment for {category.value.replace('_', ' ')}."
            concern = "The report describes a significant failure pattern that could compromise safety, security, or data privacy; it has not been independently verified."
            explanation = "Advisory high severity based on domain risk factors; human validation is essential."
        elif severity == Severity.LOW:
            summary = "Low severity assessment for minor or non-blocking concern."
            concern = "The submitted report describes a low-impact or formatting-related issue with limited operational risk; it has not been independently verified."
            explanation = "Advisory low severity reflecting limited scope or minor non-harmful behavior."
        else:
            summary = f"Moderate severity assessment for {category.value.replace('_', ' ')}."
            concern = "The submitted report describes a potential concern; it has not been independently verified."
            explanation = "Advisory medium severity reflects standard operational uncertainty without verified high-impact harm."

        missing_info = ["Scope, impact, and independent verification are not established by this demo assessment."]
        if text_len < 50:
            missing_info.insert(0, "Incident description contains minimal details; further factual context is needed.")

        return AIModelAssessment(
            suggested_category=category,
            suggested_severity=severity,
            risk_score=risk_score,
            confidence=confidence,
            concise_summary=summary,
            observed_failure_or_concern=concern,
            potential_harms=[
                "Potential user, organizational, or system impact requires human review."
            ],
            affected_stakeholders=[incident.affected_population] if incident.affected_population else [],
            evidence=[],
            missing_information=missing_info,
            immediate_containment_steps=["Assign a reviewer and preserve available evidence."],
            recommended_corrective_actions=["Investigate the report and document a human determination."],
            urgent_human_review_recommended=severity in (Severity.CRITICAL, Severity.HIGH),
            severity_explanation=explanation,
        )


class OpenAITriageProvider:
    mode = "openai"

    def __init__(self, api_key: str, model_name: str, client: object | None = None,
                 model_version_override: str | None = None) -> None:
        self.model_name = model_name
        self.model_version_override = model_version_override
        # Populated per assessment from reliable provider evidence only; never invented.
        self.model_version: str | None = model_version_override
        self.system_fingerprint: str | None = None
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, timeout=30.0, max_retries=0)
        except Exception as error:
            raise TriageError("AI triage is not available. Check the application configuration.") from error

    def assess(self, incident: Incident, evidence_references: list[str]) -> AIModelAssessment:
        # Reset per-call evidence so a failed call cannot leak a prior fingerprint.
        self.system_fingerprint = None
        if self.model_version_override is not None:
            self.model_version = self.model_version_override
        else:
            self.model_version = None
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
            # Capture genuine model identity when the provider returns it.
            returned_model = getattr(completion, "model", None)
            if isinstance(returned_model, str) and returned_model.strip() and returned_model.strip() != self.model_name:
                self.model_name = returned_model.strip()
            fingerprint = getattr(completion, "system_fingerprint", None)
            if isinstance(fingerprint, str) and fingerprint.strip():
                # Diagnostic metadata only; never presented as a model version.
                self.system_fingerprint = fingerprint.strip()
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
        if settings.effective_demo_mode:
            provider: TriageProvider = DemoTriageProvider()
        else:
            provider = OpenAITriageProvider(settings.openai_api_key or "", settings.openai_model,
                                            model_version_override=settings.openai_model_version_override)
        return cls(repository, provider)

    def assess_incident(self, incident_id: str) -> AIAssessment:
        incident = self._repository.get_incident(incident_id)
        evidence = self._repository.list_evidence_references(incident_id)
        for attempt in range(self._retries + 1):
            try:
                output = AIModelAssessment.model_validate(self._provider.assess(incident, evidence))
                assessment = AIAssessment(incident_id=incident_id, provider_mode=self._provider.mode, model_name=self._provider.model_name,
                                          model_version=getattr(self._provider, "model_version", None),
                                          system_fingerprint=getattr(self._provider, "system_fingerprint", None),
                                          prompt_version=PROMPT_VERSION, **output.model_dump())
                stored = self._repository.add_ai_assessment(assessment)
                # Verification side-effect lives in add_ai_assessment (same
                # transaction, reported/unverified -> ai_assessed, never verified).
                return stored
            except TransientTriageError:
                if attempt == self._retries:
                    raise
                sleep(0.2 * (2 ** attempt))
        raise TriageError("AI triage could not complete.")
