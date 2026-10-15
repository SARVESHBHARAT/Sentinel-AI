"""Deterministic synthetic demo dataset for classroom demonstrations.

Every record created here is fictional, marked ``is_demo=True``, titled
``[DEMO] ...`` and described as a SYNTHETIC DEMO RECORD. The scenarios are
plausible fictional examples only -- they are NOT allegations that any real
provider or model ever behaved this way, and they are not evidence of real
model performance.

Coverage: 160 records dated 2026-08-15..2026-10-15, spanning
weekdays/weekends, quiet/busy periods and a few clusters, across many
providers, models, versions, categories, severities and lifecycle states.

Guarantees:
- Reproducible: fixed data tables + fixed RNG seed (no wall-clock dependence).
- Idempotent: re-running skips records whose demo titles already exist.
  Legacy demo titles (pre-2026-08-15 dataset) are migrated in place to the
  new range; genuine reports are never read-modified or deleted.
- Isolated: only ``is_demo=True`` incidents are written; genuine reports are
  never read-modified or deleted. Cleanup uses ``reset_demo_incidents``.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from datetime import date, timedelta

from sentinel.ai.triage_service import AITriageService, DemoTriageProvider
from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import (
    IncidentCategory,
    IncidentStatus,
    Severity,
    SeveritySource,
    VerificationStatus,
)
from sentinel.schemas.incident import (
    CorrectiveAction,
    CreateIncident,
    IncidentUpdate,
    ReviewerNote,
)
from sentinel.services.incident_service import IncidentService

_RNG_SEED = 20260815
_TITLE_PREFIX = "[DEMO]"

_START_DATE = date(2026, 8, 15)
_END_DATE = date(2026, 10, 15)

# (provider, model, version, count) -- fictional demonstration slots.
_MODEL_SLOTS = [
    ("OpenAI", "gpt-4o", "2024-08-06", 13),
    ("OpenAI", "gpt-4o", "2024-05-13", 9),
    ("OpenAI", "gpt-4o-mini", "2024-07-18", 11),
    ("OpenAI", "gpt-4.1-mini", "2025-04-14", 9),
    ("Anthropic", "claude-3-5-sonnet", "20241022", 11),
    ("Anthropic", "claude-3-5-sonnet", "20240620", 7),
    ("Anthropic", "claude-3-haiku", "20240307", 9),
    ("Google", "gemini-1.5-pro", "002", 11),
    ("Google", "gemini-1.5-pro", "001", 7),
    ("Google", "gemini-1.5-flash", "002", 9),
    ("Meta", "llama-3.1-70b-instruct", None, 6),
    ("Meta", "llama-3.1-8b-instruct", "3.1", 7),
    ("Mistral", "mistral-large", "2411", 9),
    ("Mistral", "mistral-small", "2409", 7),
    ("Qwen", "qwen2.5-72b-instruct", "20240919", 8),
    ("Qwen", "qwen2-7b-instruct", "20240731", 7),
    ("Illustrative", "sentinel-demo-assistant", "v1.2", 7),
    ("Illustrative", "sentinel-demo-assistant", "v1.3", 6),
    (None, None, None, 7),
]
_THEMES_A = [
    {"label": "hallucination: fabricated citations",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "assistant invents a research-paper citation presented as verified source",
        "chatbot fabricates a court-case citation in a memo draft",
        "assistant cites a nonexistent clinical guideline by number",
        "model invents historical statistics with fake bibliography",
        "assistant hallucinates a product manual page that never existed",
        "chatbot attributes a fabricated quote to a public official",
        "model invents conference proceedings to support a claim",
        "assistant fabricates dataset download links that return 404",
     ]},
    {"label": "incorrect factual answers",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "assistant states the wrong capital city with high confidence",
        "chatbot gives an incorrect unit conversion for a recipe batch",
        "model misstates a recent election result in a summary",
        "assistant reports the wrong launch year for a satellite",
        "chatbot confuses two similarly named medications in a FAQ",
        "model gives a wrong time-zone offset for a flight itinerary",
        "assistant misquotes a regulation threshold value",
        "chatbot states an incorrect exchange-rate figure as current",
     ]},
    {"label": "reasoning and mathematical errors",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "assistant miscalculates compound interest over three steps",
        "model fails a multi-hop logic puzzle and contradicts itself",
        "chatbot divides by the wrong denominator in a dosage estimate",
        "assistant mishandles percentage-point vs percent change",
        "model drops a negative sign in an accounting reconciliation",
        "assistant misapplies order of operations in a spreadsheet formula",
        "chatbot misreads a chart axis and inverts a trend",
        "model rounds intermediate results and drifts off badly",
     ]},
]
_THEMES_B = [
    {"label": "coding errors and insecure code",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.CRITICAL],
     "heads": [
        "coding assistant generates login handler that skips permission checks",
        "model emits SQL query built with string concatenation",
        "assistant suggests disabling TLS verification to fix an error",
        "generated upload handler trusts file extensions without validation",
        "model produces an off-by-one pagination loop losing records",
        "assistant hardcodes a secret key in sample configuration",
        "generated auth token comparison uses non-constant-time check",
        "model suggests a database migration without a backup step",
     ]},
    {"label": "bias and unfair treatment",
     "category": IncidentCategory.BIAS_DISCRIMINATION,
     "severities": [Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.CRITICAL],
     "heads": [
        "screening model ranks comparable applicants inconsistently",
        "assistant uses different tone for identical queries across dialects",
        "model assigns stereotyped roles in generated stories",
        "loan-eligibility draft varies with neighbourhood proxies",
        "translation quality drops for one regional dialect",
        "hiring summary emphasises gaps for one group only",
        "image-caption draft describes people with unequal detail",
        "support triage prioritises one postcode area over another",
     ]},
    {"label": "privacy leakage",
     "category": IncidentCategory.PRIVACY_DATA_LEAKAGE,
     "severities": [Severity.HIGH, Severity.HIGH, Severity.CRITICAL, Severity.CRITICAL],
     "heads": [
        "assistant repeats text resembling another user's prior conversation",
        "model echoes a masked account number from earlier context",
        "chatbot includes a private address from retrieved notes verbatim",
        "assistant reveals an internal ticket ID with customer details",
        "model pastes hidden system prompt excerpt into an answer",
        "chatbot discloses meeting notes not shared with the requester",
        "assistant reconstructs a redacted phone number from fragments",
        "model attaches the wrong user's export file to a summary",
     ]},
]
_THEMES_C = [
    {"label": "prompt injection and instruction failures",
     "category": IncidentCategory.SECURITY_VULNERABILITY_ABUSE,
     "severities": [Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.CRITICAL],
     "heads": [
        "embedded webpage instruction makes assistant ignore safety preamble",
        "pasted email directive tricks model into exfiltrating summary",
        "document footer instructs model to reveal hidden instructions",
        "assistant follows a tool-output command as if user-authorised",
        "image caption payload steers model to disable a refusal",
        "spreadsheet cell formula injects an instruction the model obeys",
        "support transcript jailbreak convinces model to change roles",
        "assistant treats quoted untrusted text as a system command",
     ]},
    {"label": "unsafe or inappropriate recommendations",
     "category": IncidentCategory.HARMFUL_UNSAFE_OUTPUT,
     "severities": [Severity.HIGH, Severity.HIGH, Severity.CRITICAL, Severity.CRITICAL],
     "heads": [
        "assistant suggests an unsafe household-chemical mix for cleaning",
        "chatbot recommends ignoring a smoke-alarm fault overnight",
        "model gives risky foraging advice without an expert warning",
        "assistant outlines an unsafe vehicle repair shortcut",
        "chatbot encourages excessive exertion despite reported symptoms",
        "model recommends an unapproved electrical rewiring method",
        "assistant downplays a severe allergy exposure scenario",
        "chatbot provides unsafe storage advice for flammable material",
     ]},
    {"label": "medical misinformation",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.HIGH, Severity.HIGH, Severity.CRITICAL, Severity.CRITICAL],
     "heads": [
        "health chatbot misexplains a medication interaction and omits escalation advice",
        "assistant misstates fasting rules before a lab test",
        "model confuses two vaccines and their schedules",
        "chatbot understates warning signs after a head injury",
        "assistant gives an incorrect inhaler technique sequence",
        "model misquotes a screening-age threshold",
        "chatbot mislabels a benign symptom as definitively harmless",
        "assistant provides an outdated first-aid protocol",
     ]},
]
_THEMES_D = [
    {"label": "legal misinformation",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.CRITICAL],
     "heads": [
        "assistant misstates a filing deadline for a small claim",
        "chatbot invents a tenancy right not present in local rules",
        "model confuses copyright duration for a creative work",
        "assistant misexplains small-business record-keeping duties",
        "chatbot overstates eligibility for a fee waiver",
        "model cites a repealed regulation as current",
        "assistant misdescribes appeal-window counting rules",
        "chatbot gives an incorrect notice-period figure",
     ]},
    {"label": "financial misinformation",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.CRITICAL],
     "heads": [
        "assistant miscalculates a loan projection with unjustified confidence",
        "chatbot misstates tax-bracket math in a worked example",
        "model confuses APR with monthly rate in a comparison",
        "assistant overstates pension growth using wrong compounding",
        "chatbot mislabels a fee as tax-deductible",
        "model miscomputes currency conversion with stale rates",
        "assistant understates overdraft costs in a scenario",
        "chatbot gives an incorrect vesting-schedule illustration",
     ]},
    {"label": "incorrect classification and prediction",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "ticket classifier routes urgent outage reports to low priority",
        "sentiment model flips negation and marks complaints as praise",
        "fraud screen flags routine invoices while missing obvious anomalies",
        "resume parser mislabels employment gaps as skills",
        "demand forecast ignores a known holiday spike",
        "spam filter quarantines legitimate invoices from a new vendor",
        "maintenance predictor misses a recurring fault pattern",
        "language detector misroutes regional support requests",
     ]},
]
_THEMES_E = [
    {"label": "tool-use failures",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH, Severity.HIGH],
     "heads": [
        "agent calls the wrong API and reports success despite failure",
        "assistant deletes a draft instead of archiving it via tool call",
        "agent passes dates in the wrong format and silently retries",
        "model queries a production database instead of the sandbox replica",
        "assistant books a placeholder slot and confirms it as final",
        "agent uploads a file to the wrong workspace folder",
        "model chains two tools in the wrong order and corrupts state",
        "assistant ignores a tool error and fabricates the result",
     ]},
    {"label": "RAG failures",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "retrieval assistant answers from an outdated policy document",
        "model ignores the top-ranked source and cites a stale memo",
        "assistant merges two conflicting sources without flagging conflict",
        "RAG pipeline retrieves the wrong customer record for a summary",
        "model quotes a superseded price list as current",
        "assistant fails to retrieve the newest incident runbook",
        "retrieval returns an empty set and model answers anyway",
        "assistant cites sources that do not support its conclusion",
     ]},
    {"label": "multilingual and translation errors",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "assistant mistranslates a safety warning and softens its urgency",
        "model swaps formal and informal address in a customer letter",
        "chatbot mistranslates dosage units between languages",
        "assistant drops a negation when translating a contract clause",
        "model transliterates a name inconsistently across paragraphs",
        "chatbot mixes two dialects and confuses the reader",
        "assistant mistranslates a date format causing a missed appointment",
        "model mistranslates an idiom literally in a support reply",
     ]},
]
_THEMES_F = [
    {"label": "content moderation failures",
     "category": IncidentCategory.HARMFUL_UNSAFE_OUTPUT,
     "severities": [Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.CRITICAL],
     "heads": [
        "moderation draft allows harassing language through as benign",
        "assistant fails to flag graphic detail in a user story",
        "model over-blocks a benign health discussion as disallowed",
        "chat filter misses repeated slurs hidden with spacing",
        "assistant approves a scam message as legitimate outreach",
        "moderation summary omits the most severe violation",
        "model mislabels satire as extremist content",
        "assistant inconsistently enforces the same policy across turns",
     ]},
    {"label": "inconsistent and nondeterministic behaviour",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.LOW, Severity.LOW, Severity.MEDIUM, Severity.MEDIUM],
     "heads": [
        "assistant gives three different totals for the same invoice",
        "model flips its recommendation on identical re-prompts",
        "chatbot alternates between two policies across sessions",
        "assistant contradicts its own summary in the next paragraph",
        "model returns different classifications for duplicate tickets",
        "assistant changes cited figures when asked to double-check",
        "chatbot varies its refusal boundary on near-identical prompts",
        "model reorders ranked options randomly on refresh",
     ]},
    {"label": "excessive confidence in incorrect answers",
     "category": IncidentCategory.HALLUCINATION_MISINFORMATION,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "assistant asserts a wrong historical date with citations-grade certainty",
        "model declares an uncertain forecast as guaranteed",
        "chatbot presents a guessed regulation number as definitive",
        "assistant claims full coverage of sources after partial retrieval",
        "model states a disputed fact without any hedging",
        "assistant reports a computed total as audited when it is not",
        "chatbot dismisses valid uncertainty in a medical summary",
        "model overstates translation fidelity for a low-resource language",
     ]},
]
_THEMES_G = [
    {"label": "data extraction and formatting failures",
     "category": IncidentCategory.RELIABILITY_SYSTEM_FAILURE,
     "severities": [Severity.LOW, Severity.LOW, Severity.MEDIUM, Severity.MEDIUM],
     "heads": [
        "assistant drops table rows when converting a PDF extract",
        "model emits malformed JSON that breaks downstream parsing",
        "chatbot misaligns CSV columns after reordering fields",
        "assistant truncates long identifiers in an export",
        "model confuses decimal separators in a locale-sensitive export",
        "assistant omits footnotes when summarising a scanned form",
        "model hallucinates missing fields instead of marking them null",
        "assistant produces an inaccessible colour-coded status table",
     ]},
    {"label": "other reliability and safety incidents",
     "category": IncidentCategory.OTHER_UNCLASSIFIED,
     "severities": [Severity.LOW, Severity.MEDIUM, Severity.MEDIUM, Severity.HIGH],
     "heads": [
        "assistant times out on long inputs and returns a partial answer silently",
        "model leaks verbose debug traces into a user-facing reply",
        "chatbot loops and repeats the same paragraph five times",
        "assistant ignores an explicit output-length constraint",
        "model reproduces a short copyrighted lyric excerpt verbatim",
        "assistant fails to respect a requested reading-level setting",
        "model sends duplicate notifications for a single event",
        "assistant misattributes feedback to the wrong conversation thread",
     ]},
]

_THEMES = _THEMES_A + _THEMES_B + _THEMES_C + _THEMES_D + _THEMES_E + _THEMES_F + _THEMES_G

_COPYRIGHT_INDICES = {36, 143}

_CONTEXTS = [
    "fictional neighbourhood clinic pilot", "illustrative bank support sandbox",
    "simulated school helpdesk trial", "fictional travel-booking prototype",
    "offline retail-demo environment", "illustrative HR screening sandbox",
    "fictional municipal hotline drill", "simulated e-commerce test store",
    "illustrative logistics dashboard demo", "fictional library assistant pilot",
]

_IMPACTS = [
    "Fictional impact: a test user spots the error and corrects it; no real harm occurred.",
    "Fictional impact: simulated rework of about an hour for a demo reviewer.",
    "Fictional impact: demonstration workflow stalls until a human intervenes.",
    "Fictional impact: illustrative trust exercise shows why human review matters.",
    "Fictional impact: simulated customer confusion in a sandbox; resolved with a correction notice.",
    "Fictional impact: fictional exposure incident contained in test data; rotation of demo credentials.",
]
_VERIF_TARGETS = (
    [VerificationStatus.REPORTED] * 32
    + [VerificationStatus.AI_ASSESSED] * 32
    + [VerificationStatus.HUMAN_REVIEWED] * 24
    + [VerificationStatus.VERIFIED] * 32
    + [VerificationStatus.DISPUTED] * 16
    + [VerificationStatus.UNVERIFIED] * 24
)

_STATUS_TARGETS = (
    [IncidentStatus.SUBMITTED] * 48
    + [IncidentStatus.UNDER_REVIEW] * 40
    + [IncidentStatus.ACTION_REQUIRED] * 24
    + [IncidentStatus.RESOLVED] * 32
    + [IncidentStatus.CLOSED] * 16
)


@dataclass(frozen=True, slots=True)
class SeedResult:
    created: int
    skipped: int
    migrated: int = 0


def _cluster_weights() -> dict:
    weights = {}
    day = _START_DATE
    while day <= _END_DATE:
        weights[day] = 1.0
        day += timedelta(days=1)
    for iso in ("2026-08-16", "2026-08-17", "2026-08-18",
                "2026-09-06", "2026-09-07", "2026-09-08",
                "2026-09-27", "2026-09-28"):
        weights[date.fromisoformat(iso)] = 0.35
    for iso in ("2026-08-28", "2026-08-29", "2026-08-30",
                "2026-09-18", "2026-09-19", "2026-09-20",
                "2026-10-05", "2026-10-06"):
        weights[date.fromisoformat(iso)] = 3.0
    return weights


def _sample_dates(rng: random.Random, count: int) -> list:
    weights = _cluster_weights()
    days = sorted(weights)
    picks = rng.choices(days, weights=[weights[d] for d in days], k=count)
    picks.sort()
    for _ in range(count // 7):
        left = rng.randrange(count)
        right = min(count - 1, left + rng.randrange(1, 4))
        if abs((picks[left] - picks[right]).days) <= 2:
            picks[left], picks[right] = picks[right], picks[left]
    return picks
def _describe(style: int, head: str, context: str, impact: str,
              provider, model) -> tuple:
    sys = f"{provider or 'Unspecified provider'} / {model or 'unspecified system'}"
    if style == 0:
        desc = (f"SYNTHETIC DEMO RECORD -- fictional scenario for demonstration only. {head[0].upper() + head[1:]} "
                f"during the {context}. Affected system: {sys}. This record does not describe a real event.")
        wrong = f"In a fictional {context}, the system produced an incorrect or unsafe output ({head})."
        expected = "A careful, correct response with uncertainty flagged and escalation where needed."
        observed = f"The demo system instead produced the failure described ({head})."
    elif style == 1:
        desc = (f"SYNTHETIC DEMO RECORD -- offline red-team style vignette (fictional, {context}). What happened: {head}. "
                f"Contributing factors (illustrative): ambiguous prompt, stale retrieval snapshot, missing guardrail check. "
                f"Affected system: {sys}. No real users, data, or vendors are involved; do not treat as a real incident.")
        wrong = (f"Under simulated load in the {context}, the model mishandled the request: {head}. "
                 "Logs (fictional) show a plausible but unverified completion path.")
        expected = ("Retrieve current sources, validate tool arguments, refuse or escalate when confidence is low, "
                    "and record reasoning for human review.")
        observed = (f"The system returned the flawed output ({head}) without an adequate warning, "
                    "requiring a human correction in the simulation.")
    else:
        desc = (f"SYNTHETIC DEMO RECORD -- fictional user story from the {context}. A test persona asked a routine question "
                f"and the demo assistant {head}. The tester flagged it, captured the transcript (fictional), and filed this "
                f"demonstration report. Affected system: {sys}. Not a real event and not evidence about any real product.")
        wrong = f"A routine test prompt in the {context} led the assistant to fail: {head}."
        expected = "A helpful answer that acknowledges limits, cites checkable sources, and routes risky cases to a human."
        observed = f"Instead the assistant {head}, and the test reviewer had to intervene."
    return desc, wrong, expected, observed, impact


def _build_rows() -> list:
    rng = random.Random(_RNG_SEED)
    slot_pool = []
    for provider, model, version, count in _MODEL_SLOTS:
        slot_pool.extend([(provider, model, version)] * count)
    rng.shuffle(slot_pool)
    total = len(slot_pool)
    stems = []
    for theme_idx, theme in enumerate(_THEMES):
        for head in theme["heads"]:
            stems.append((theme_idx, head))
    assert len(stems) == total, f"theme heads ({len(stems)}) must match slots ({total})"
    rng.shuffle(stems)
    dates = _sample_dates(rng, total)
    verif = list(_VERIF_TARGETS)
    rng.shuffle(verif)
    statuses = list(_STATUS_TARGETS)
    rng.shuffle(statuses)
    rows = []
    for idx in range(total):
        theme_idx, head = stems[idx]
        theme = _THEMES[theme_idx]
        provider, model, version = slot_pool[idx]
        category = theme["category"]
        if idx in _COPYRIGHT_INDICES:
            category = IncidentCategory.COPYRIGHT_IP_CONCERN
        severity = rng.choice(theme["severities"])
        if severity == Severity.CRITICAL and theme["label"] in {
            "inconsistent and nondeterministic behaviour",
            "data extraction and formatting failures",
        }:
            severity = Severity.MEDIUM
        report_date = dates[idx]
        occurrence_date = report_date - timedelta(days=rng.choice([0, 0, 1, 1, 2, 3]))
        context = rng.choice(_CONTEXTS)
        impact = rng.choice(_IMPACTS)
        if severity in (Severity.HIGH, Severity.CRITICAL) and "no real harm" in impact:
            impact = "Fictional impact: simulated escalation to a human reviewer; contained within test data."
        style = idx % 3
        description, wrong, expected, observed, impact_text = _describe(
            style, head, context, impact, provider, model)
        slot_label = model or "unspecified system"
        title = f"{_TITLE_PREFIX} Fictional {theme['label'].split(':')[0]} -- {head} [{slot_label} SYN-{idx:03d}]"
        if len(title) > 300:
            title = title[:299] + "]"
        target = verif[idx]
        status_target = statuses[idx]
        if status_target in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED) and target in (
            VerificationStatus.REPORTED, VerificationStatus.AI_ASSESSED,
        ):
            target = VerificationStatus.HUMAN_REVIEWED
        resolution = None
        if status_target in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
            resolution = (f"SYNTHETIC resolution (fictional): reviewer confirmed the demo transcript, "
                          f"logged a correction, and closed the drill scenario SYN-{idx:03d}.")
        rows.append({
            "key": f"SYN-{idx:03d}",
            "title": title,
            "description": description,
            "what_wrong": wrong,
            "expected": expected,
            "observed": observed,
            "impact": impact_text,
            "category": category,
            "severity": severity,
            "report_date": report_date,
            "occurrence_date": occurrence_date,
            "provider": provider,
            "affected_model_name": model,
            "affected_model_version": version,
            "target": target,
            "status_target": status_target,
            "resolution": resolution,
            "population": "Simulated test population (fictional, no real personal data).",
        })
    rows.sort(key=lambda row: row["key"])
    return rows
def _bfs_path(start, target, neighbours: dict):
    queue = deque([[start]])
    seen = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == target:
            return path
        for nxt in neighbours.get(path[-1], set()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(path + [nxt])
    return None


def _drive_verification(repository, service, triage, incident_id: str, target) -> None:
    from sentinel.domain.lifecycle import ALLOWED_VERIFICATION_TRANSITIONS
    for _ in range(8):
        current = repository.get_incident(incident_id).verification_status
        if current == target:
            return
        path = _bfs_path(current, target, ALLOWED_VERIFICATION_TRANSITIONS)
        if not path or len(path) < 2:
            return
        nxt = path[1]
        # Assessment history must be truthful: any record leaving REPORTED gets
        # a labelled demo assessment first (reported/unverified -> ai_assessed).
        if current == VerificationStatus.REPORTED and nxt != VerificationStatus.AI_ASSESSED:
            triage.assess_incident(incident_id)
            continue
        if nxt == VerificationStatus.AI_ASSESSED:
            triage.assess_incident(incident_id)
        elif nxt == VerificationStatus.HUMAN_REVIEWED:
            repository.transition_verification(incident_id, nxt, actor="Demo seeding")
            repository.add_reviewer_note(ReviewerNote(
                incident_id=incident_id, author="Demo Reviewer",
                body="Demo human review: checked the fictional transcript against the test brief."))
        elif nxt == VerificationStatus.VERIFIED:
            service.verify(incident_id, reviewer="Demo Reviewer",
                           justification="Demo verification: transcript matches the scripted fictional failure.")
        elif nxt == VerificationStatus.DISPUTED:
            try:
                service.dispute(incident_id, reviewer="Demo Reviewer",
                                justification="Demo dispute: second reviewer questions the scripted expected behaviour.")
            except ValueError:
                repository.transition_verification(incident_id, nxt, actor="Demo seeding")
        elif nxt == VerificationStatus.UNVERIFIED:
            try:
                service.mark_unverified(incident_id, reviewer="Demo Reviewer",
                                        justification="Demo triage: not verifiable beyond the fictional transcript.")
            except ValueError:
                repository.transition_verification(incident_id, nxt, actor="Demo seeding")
        else:
            repository.transition_verification(incident_id, nxt, actor="Demo seeding")
def _drive_status(repository, incident_id: str, target, resolution) -> None:
    from sentinel.domain.lifecycle import ALLOWED_TRANSITIONS
    if resolution:
        try:
            repository.update_incident(
                incident_id, IncidentUpdate(resolution_summary=resolution),
                actor="Demo seeding")
        except ValueError:
            pass
    for _ in range(6):
        current = repository.get_incident(incident_id).status
        if current == target:
            return
        path = _bfs_path(current, target, ALLOWED_TRANSITIONS)
        if not path or len(path) < 2:
            return
        try:
            repository.transition_status(incident_id, path[1], actor="Demo seeding")
        except ValueError:
            return
    if target in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
        try:
            repository.add_corrective_action(CorrectiveAction(
                incident_id=incident_id,
                title="Demo corrective action: update test brief and add guardrail check (fictional)",
                action_kind="corrective", owner="Demo Reviewer",
                status="completed" if target == IncidentStatus.CLOSED else "in_progress"))
        except ValueError:
            pass


def _full_description(row: dict) -> str:
    return (f"{row['description']}\n\nWhat went wrong (fictional): {row['what_wrong']}\n"
            f"Expected behaviour (fictional): {row['expected']}\n"
            f"Observed behaviour (fictional): {row['observed']}")


def seed_demo_dataset(repository: IncidentRepository) -> SeedResult:
    rows = _build_rows()
    existing_demo = {}
    _, total = repository.search_incidents(is_demo=True, limit=1)
    for offset in range(0, total, 500):
        batch, _ = repository.search_incidents(is_demo=True, limit=500, offset=offset)
        for item in batch:
            existing_demo[item.title] = item
    missing = [row for row in rows if row["title"] not in existing_demo]
    legacy = sorted(title for title in existing_demo if title not in {r["title"] for r in rows})
    triage = AITriageService(repository, DemoTriageProvider())
    service = IncidentService(repository)
    created = 0
    migrated = 0
    skipped = len(rows) - len(missing)
    for old_title, row in zip(legacy, missing):
        incident = existing_demo[old_title]
        repository.update_incident(
            incident.incident_id,
            IncidentUpdate(
                title=row["title"], description=_full_description(row),
                category=row["category"], provider=row["provider"],
                affected_model_name=row["affected_model_name"],
                affected_model_version=row["affected_model_version"],
                occurrence_date=row["occurrence_date"], report_date=row["report_date"],
                severity=row["severity"], severity_source=SeveritySource.HUMAN,
                potential_impact=row["impact"],
                affected_population=row["population"],
            ),
            actor="Demo seeding",
        )
        _drive_verification(repository, service, triage, incident.incident_id, row["target"])
        _drive_status(repository, incident.incident_id, row["status_target"], row["resolution"])
        migrated += 1
    remaining = missing[len(legacy):] if legacy else missing
    for row in remaining:
        payload = CreateIncident(
            title=row["title"], description=_full_description(row), category=row["category"],
            severity=row["severity"], severity_source=SeveritySource.HUMAN,
            occurrence_date=row["occurrence_date"], report_date=row["report_date"],
            provider=row["provider"], affected_model_name=row["affected_model_name"],
            affected_model_version=row["affected_model_version"],
            potential_impact=row["impact"], affected_population=row["population"],
            anonymous_report=True,
        )
        incident = repository.create_incident(payload, actor="Demo seeding", is_demo=True)
        created += 1
        _drive_verification(repository, service, triage, incident.incident_id, row["target"])
        _drive_status(repository, incident.incident_id, row["status_target"], row["resolution"])
    return SeedResult(created=created, skipped=skipped, migrated=migrated)
