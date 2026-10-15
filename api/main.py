"""Sentinel AI — Unified FastAPI backend + React SPA server.

Wraps the existing Python services with REST endpoints and serves the
React production build as the primary frontend.

Development:  uvicorn api.main:app --reload --port 8000
              (Run Vite dev server separately for HMR: cd frontend && npm run dev)

Production:   cd frontend && npm run build
              uvicorn api.main:app --host 0.0.0.0 --port 8000
              (React is served at http://localhost:8000)
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path
from datetime import date
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sentinel.config import Settings
from sentinel.ai import AITriageService
from sentinel.database.repositories import IncidentNotFoundError, IncidentRepository
from sentinel.domain.enums import (
    IncidentCategory,
    IncidentStatus,
    Severity,
    VerificationStatus,
)
from sentinel.schemas.incident import (
    AIAssessment,
    CorrectiveAction,
    CreateIncident,
    Incident,
    IncidentUpdate,
    ReviewerNote,
)
from sentinel.services import AnalyticsService, IncidentService, ReportService
from sentinel.services.model_intelligence_service import ModelIntelligenceService

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

settings = Settings.from_environment()
repository = IncidentRepository(settings.database_path)
repository.initialize()

incident_service = IncidentService(repository)
analytics_service = AnalyticsService(repository)
report_service = ReportService(repository)
model_intel_service = ModelIntelligenceService(
    repository, settings.model_intelligence_min_sample
)
triage_service = AITriageService.from_settings(repository, settings)

# In-memory submission throttle — mirrors app.py behaviour
_submission_times: deque = deque()


def _submission_allowed() -> bool:
    now = time.monotonic()
    window = settings.submission_rate_window_seconds
    while _submission_times and now - _submission_times[0] > window:
        _submission_times.popleft()
    if len(_submission_times) >= settings.submission_rate_limit:
        return False
    _submission_times.append(now)
    return True


app = FastAPI(
    title="Sentinel AI API",
    description="REST API for the Sentinel AI incident governance platform.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — allow Vite dev server and unified production origin.
# In production, same-origin requests don't need CORS, but keep Vite origins for dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",  # vite preview
        "http://127.0.0.1:4173",
        "http://localhost:8000",  # unified production origin
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


# ---------------------------------------------------------------------------
# Read-only guard helpers
# ---------------------------------------------------------------------------

def _assert_writable() -> None:
    if settings.read_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only mode is enabled; this operation is not permitted.",
        )


# ---------------------------------------------------------------------------
# Shared error handler
# ---------------------------------------------------------------------------

def _not_found(incident_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Incident {incident_id!r} was not found.",
    )


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


# ---------------------------------------------------------------------------
# Pydantic request/response models for endpoints that need custom shapes
# ---------------------------------------------------------------------------

class OverviewResponse(BaseModel):
    total: int
    open_incidents: int
    high_critical: int
    awaiting_review: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_verification: dict[str, int]
    trend: dict[str, int]


class IncidentListResponse(BaseModel):
    incidents: list[Incident]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatusTransitionRequest(BaseModel):
    target_status: IncidentStatus
    actor: str | None = Field(default=None, max_length=150)


class VerificationRequest(BaseModel):
    action: str = Field(pattern="^(verify|dispute|mark_unverified)$")
    reviewer: str = Field(min_length=1, max_length=150)
    justification: str = Field(min_length=1, max_length=2000)


class ReviewerNoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    author: str | None = Field(default=None, max_length=150)


class CorrectiveActionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    action_kind: str = Field(default="corrective", pattern="^(corrective|preventive)$")
    owner: str | None = Field(default=None, max_length=150)
    status: str = Field(default="open", pattern="^(open|in_progress|completed|cancelled)$")
    due_date: date | None = None
    evidence: str | None = Field(default=None, max_length=5000)


class TriageRequest(BaseModel):
    """Trigger AI triage on a specific incident. Does not expose reviewed results."""
    pass  # No body needed; action is triggered on the incident in the path.


class ReviewAISuggestionRequest(BaseModel):
    assessment_created_at: str  # ISO timestamp to identify which assessment is being reviewed
    category: IncidentCategory
    severity: Severity
    reviewer: str | None = Field(default=None, max_length=150)
    justification: str | None = Field(default=None, max_length=2000)


class ModelIntelligenceSummaryParams(BaseModel):
    dataset: str | None = None
    category: str | None = None
    severity: str | None = None
    verification_status: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class CompareRequest(BaseModel):
    targets: list[tuple[str, str, str | None]]
    dataset: str | None = None
    category: str | None = None
    severity: str | None = None
    verification_status: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class SettingsResponse(BaseModel):
    demo_mode: bool
    effective_demo_mode: bool
    read_only: bool
    openai_model: str
    has_api_key: bool
    model_intelligence_min_sample: int
    submission_rate_limit: int
    submission_rate_window_seconds: int
    database_path: str


# ---------------------------------------------------------------------------
# Routes: Health
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Sentinel AI API"}


# ---------------------------------------------------------------------------
# Routes: Overview / Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/overview", response_model=OverviewResponse, tags=["Dashboard"])
def get_overview(
    category: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> OverviewResponse:
    incidents = analytics_service.filtered_incidents(
        category=category, date_from=date_from, date_to=date_to
    )
    metrics = analytics_service.metrics(incidents)
    return OverviewResponse(
        total=metrics.total,
        open_incidents=metrics.open_incidents,
        high_critical=metrics.high_critical,
        awaiting_review=metrics.awaiting_review,
        by_category=analytics_service.distribution(incidents, "category"),
        by_severity=analytics_service.distribution(incidents, "severity"),
        by_status=analytics_service.distribution(incidents, "status"),
        by_verification=analytics_service.distribution(incidents, "verification_status"),
        trend=analytics_service.trend(incidents),
    )


# ---------------------------------------------------------------------------
# Routes: Incidents
# ---------------------------------------------------------------------------

@app.get("/api/incidents", response_model=IncidentListResponse, tags=["Incidents"])
def list_incidents(
    q: str | None = Query(default=None, description="Search ID or title"),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    affected_model_name: str | None = Query(default=None),
    affected_model_version: str | None = Query(default=None),
    is_demo: bool | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    descending: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> IncidentListResponse:
    try:
        offset = (page - 1) * page_size
        items, total = repository.search_incidents(
            query=q,
            category=category,
            severity=severity,
            status=status,
            verification_status=verification_status,
            provider=provider,
            affected_model_name=affected_model_name,
            affected_model_version=affected_model_version,
            is_demo=is_demo,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            descending=descending,
            limit=page_size,
            offset=offset,
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    total_pages = max(1, (total + page_size - 1) // page_size)
    return IncidentListResponse(
        incidents=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@app.post(
    "/api/incidents",
    response_model=Incident,
    status_code=status.HTTP_201_CREATED,
    tags=["Incidents"],
)
def create_incident(payload: CreateIncident) -> Incident:
    _assert_writable()
    if not _submission_allowed():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Submission rate limit reached. Please try again later.",
        )
    try:
        return incident_service.submit(payload, actor="API")
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed.") from exc


@app.get("/api/incidents/{incident_id}", response_model=Incident, tags=["Incidents"])
def get_incident(incident_id: str) -> Incident:
    try:
        return repository.get_incident(incident_id)
    except IncidentNotFoundError:
        raise _not_found(incident_id)


@app.patch("/api/incidents/{incident_id}", response_model=Incident, tags=["Incidents"])
def update_incident(incident_id: str, update: IncidentUpdate) -> Incident:
    _assert_writable()
    try:
        return incident_service.update(incident_id, update, actor="API")
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc


@app.post(
    "/api/incidents/{incident_id}/status",
    response_model=Incident,
    tags=["Incidents"],
)
def transition_status(incident_id: str, body: StatusTransitionRequest) -> Incident:
    _assert_writable()
    try:
        return incident_service.transition(
            incident_id, body.target_status, actor=body.actor or "API"
        )
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    except ValueError as exc:
        raise _conflict(str(exc)) from exc


# ---------------------------------------------------------------------------
# Routes: Assessments and Triage
# ---------------------------------------------------------------------------

@app.get(
    "/api/incidents/{incident_id}/assessments",
    response_model=list[AIAssessment],
    tags=["Triage"],
)
def list_assessments(incident_id: str) -> list[AIAssessment]:
    try:
        repository.get_incident(incident_id)  # 404 guard
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    return repository.list_ai_assessments(incident_id)


@app.post(
    "/api/incidents/{incident_id}/triage",
    response_model=AIAssessment,
    status_code=status.HTTP_201_CREATED,
    tags=["Triage"],
)
def run_triage(incident_id: str) -> AIAssessment:
    _assert_writable()
    try:
        repository.get_incident(incident_id)  # 404 guard
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    try:
        return triage_service.assess_incident(incident_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/incidents/{incident_id}/triage/review",
    response_model=Incident,
    tags=["Triage"],
)
def review_ai_suggestion(incident_id: str, body: ReviewAISuggestionRequest) -> Incident:
    _assert_writable()
    try:
        incident = repository.get_incident(incident_id)
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    assessments = repository.list_ai_assessments(incident_id)
    if not assessments:
        raise _bad_request("No AI assessment exists for this incident.")
    # Use the most recent assessment as the one being reviewed
    latest = assessments[-1]
    try:
        return incident_service.review_ai_suggestion(
            incident_id,
            latest,
            category=body.category,
            severity=body.severity,
            reviewer=body.reviewer,
            justification=body.justification,
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc


# ---------------------------------------------------------------------------
# Routes: Verification
# ---------------------------------------------------------------------------

@app.post(
    "/api/incidents/{incident_id}/verification",
    response_model=Incident,
    tags=["Verification"],
)
def update_verification(incident_id: str, body: VerificationRequest) -> Incident:
    _assert_writable()
    try:
        if body.action == "verify":
            return incident_service.verify(incident_id, body.reviewer, body.justification)
        elif body.action == "dispute":
            return incident_service.dispute(incident_id, body.reviewer, body.justification)
        elif body.action == "mark_unverified":
            return incident_service.mark_unverified(incident_id, body.reviewer, body.justification)
        else:
            raise _bad_request(f"Unknown action: {body.action}")
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    except ValueError as exc:
        raise _conflict(str(exc)) from exc


# ---------------------------------------------------------------------------
# Routes: Activity / Audit
# ---------------------------------------------------------------------------

@app.get(
    "/api/incidents/{incident_id}/activity",
    response_model=dict[str, Any],
    tags=["Incidents"],
)
def list_activity(incident_id: str) -> dict[str, Any]:
    try:
        repository.get_incident(incident_id)
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    events = repository.list_audit_events(incident_id)
    notes = repository.list_reviewer_notes(incident_id)
    actions = repository.list_corrective_actions(incident_id)
    return {
        "audit_events": [e.model_dump(mode="json") for e in events],
        "reviewer_notes": [n.model_dump(mode="json") for n in notes],
        "corrective_actions": [a.model_dump(mode="json") for a in actions],
    }


@app.post(
    "/api/incidents/{incident_id}/notes",
    response_model=ReviewerNote,
    status_code=status.HTTP_201_CREATED,
    tags=["Incidents"],
)
def add_note(incident_id: str, body: ReviewerNoteRequest) -> ReviewerNote:
    _assert_writable()
    try:
        repository.get_incident(incident_id)
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    return incident_service.add_note(
        ReviewerNote(incident_id=incident_id, body=body.body, author=body.author)
    )


@app.post(
    "/api/incidents/{incident_id}/actions",
    response_model=CorrectiveAction,
    status_code=status.HTTP_201_CREATED,
    tags=["Incidents"],
)
def add_corrective_action(incident_id: str, body: CorrectiveActionRequest) -> CorrectiveAction:
    _assert_writable()
    try:
        repository.get_incident(incident_id)
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    return incident_service.add_corrective_action(
        CorrectiveAction(
            incident_id=incident_id,
            title=body.title,
            action_kind=body.action_kind,
            owner=body.owner,
            status=body.status,
            due_date=body.due_date,
            evidence=body.evidence,
        )
    )


# ---------------------------------------------------------------------------
# Routes: Model Intelligence
# ---------------------------------------------------------------------------

@app.get(
    "/api/model-intelligence/overview",
    tags=["Model Intelligence"],
)
def model_intelligence_overview(
    dataset: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict[str, Any]:
    return model_intel_service.overview_metrics(
        dataset=dataset, category=category, severity=severity,
        verification_status=verification_status, date_from=date_from, date_to=date_to,
    )


@app.get(
    "/api/model-intelligence/leaderboard",
    tags=["Model Intelligence"],
)
def model_intelligence_leaderboard(
    sort_by: str = Query(default="most_reported"),
    dataset: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[dict[str, Any]]:
    rows = model_intel_service.leaderboard(
        sort_by=sort_by, dataset=dataset, category=category, severity=severity,
        verification_status=verification_status, date_from=date_from, date_to=date_to,
    )
    import dataclasses
    return [dataclasses.asdict(row) for row in rows]


@app.get(
    "/api/model-intelligence/groups",
    tags=["Model Intelligence"],
)
def model_intelligence_groups(
    dataset: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict[str, Any]:
    import dataclasses
    comparison = model_intel_service.compare(
        dataset=dataset, category=category, severity=severity,
        verification_status=verification_status, date_from=date_from, date_to=date_to,
    )
    return {
        "groups": [dataclasses.asdict(g) for g in comparison.groups],
        "total_matching_reports": comparison.total_matching_reports,
        "min_sample": comparison.min_sample,
        "sufficient_data": comparison.sufficient_data,
        "note": comparison.note,
        "formula": comparison.formula,
    }


@app.get(
    "/api/model-intelligence/detail",
    tags=["Model Intelligence"],
)
def model_intelligence_detail(
    provider: str = Query(),
    model: str = Query(),
    dataset: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict[str, Any]:
    import dataclasses
    detail = model_intel_service.model_detail(
        provider, model, dataset=dataset, category=category, severity=severity,
        verification_status=verification_status, date_from=date_from, date_to=date_to,
    )
    return {
        "provider": detail.provider,
        "affected_model_name": detail.affected_model_name,
        "total": detail.total,
        "sufficient": detail.sufficient,
        "versions": [dataclasses.asdict(v) for v in detail.versions],
        "recent_incidents": [i.model_dump(mode="json") for i in detail.recent_incidents],
    }


@app.post(
    "/api/model-intelligence/compare",
    tags=["Model Intelligence"],
)
def compare_models(body: CompareRequest) -> dict[str, Any]:
    import dataclasses
    workspace = model_intel_service.compare_models(
        targets=[(t[0], t[1], t[2]) for t in body.targets],
        dataset=body.dataset, category=body.category, severity=body.severity,
        verification_status=body.verification_status, date_from=body.date_from, date_to=body.date_to,
    )
    return {
        "selected": [dataclasses.asdict(v) for v in workspace.selected],
        "sufficient": workspace.sufficient,
    }


# ---------------------------------------------------------------------------
# Routes: Reports / Exports
# ---------------------------------------------------------------------------

@app.get(
    "/api/reports/markdown/{incident_id}",
    response_class=Response,
    tags=["Reports"],
)
def export_markdown(
    incident_id: str,
    redact_reporter: bool = Query(default=False),
) -> Response:
    try:
        content = report_service.markdown(incident_id, redact_reporter=redact_reporter)
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="sentinel-{incident_id}.md"'},
    )


@app.get(
    "/api/reports/pdf/{incident_id}",
    tags=["Reports"],
)
def export_pdf(
    incident_id: str,
    redact_reporter: bool = Query(default=False),
) -> Response:
    try:
        pdf_bytes = report_service.pdf(incident_id, redact_reporter=redact_reporter)
    except IncidentNotFoundError:
        raise _not_found(incident_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sentinel-{incident_id}.pdf"'},
    )


@app.get(
    "/api/reports/csv",
    tags=["Reports"],
)
def export_csv(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    is_demo: bool | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> Response:
    try:
        items, _ = repository.search_incidents(
            query=q, category=category, severity=severity, status=status,
            is_demo=is_demo, date_from=date_from, date_to=date_to,
            limit=500, offset=0,
        )
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    csv_content = ReportService.register_csv(items)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sentinel-incidents.csv"'},
    )


# ---------------------------------------------------------------------------
# Routes: Settings and demo data
# ---------------------------------------------------------------------------

@app.get("/api/settings", response_model=SettingsResponse, tags=["Settings"])
def get_settings() -> SettingsResponse:
    return SettingsResponse(
        demo_mode=settings.demo_mode,
        effective_demo_mode=settings.effective_demo_mode,
        read_only=settings.read_only,
        openai_model=settings.openai_model,
        has_api_key=bool(settings.openai_api_key),
        model_intelligence_min_sample=settings.model_intelligence_min_sample,
        submission_rate_limit=settings.submission_rate_limit,
        submission_rate_window_seconds=settings.submission_rate_window_seconds,
        database_path=str(settings.database_path),
    )


@app.post("/api/settings/seed-demo", tags=["Settings"])
def seed_demo_data() -> dict[str, Any]:
    _assert_writable()
    try:
        from sentinel.demo_seed import seed_demo_incidents
        created = seed_demo_incidents(repository)
        return {"message": f"Seeded {created} new demo record(s).", "created": created}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demo seeding failed: {exc}",
        ) from exc


@app.delete("/api/settings/demo-data", tags=["Settings"])
def reset_demo_data() -> dict[str, Any]:
    _assert_writable()
    removed = repository.reset_demo_incidents()
    return {"message": f"Removed {removed} demo record(s).", "removed": removed}


# ---------------------------------------------------------------------------
# Enum / metadata helpers for the frontend
# ---------------------------------------------------------------------------

@app.get("/api/meta/enums", tags=["Meta"])
def get_enums() -> dict[str, list[str]]:
    """Return all valid enum values for form dropdowns."""
    from sentinel.domain.enums import (
        CategorySource, IncidentCategory, IncidentStatus,
        Severity, SeveritySource, VerificationStatus,
    )
    return {
        "categories": [e.value for e in IncidentCategory if e.value not in {"harmful_output", "privacy", "discrimination", "security", "reliability", "other"}],
        "severities": [e.value for e in Severity],
        "statuses": [e.value for e in IncidentStatus],
        "verification_statuses": [e.value for e in VerificationStatus],
        "category_sources": [e.value for e in CategorySource],
        "severity_sources": [e.value for e in SeveritySource],
    }


# ---------------------------------------------------------------------------
# React SPA static file serving
# ---------------------------------------------------------------------------

_FRONTEND_BUILD = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_BUILD.is_dir():
    # Serve static assets (JS, CSS, images, fonts) under /assets
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_BUILD / "assets")),
        name="static-assets",
    )

    # Serve any other static files at the root level (favicon, manifest, etc.)
    # IMPORTANT: This catch-all must be AFTER all /api routes.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve the React SPA. Returns index.html for all non-API routes."""
        # Check if the requested file exists as a static asset in the build
        file_path = _FRONTEND_BUILD / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise, return index.html for client-side routing
        return FileResponse(str(_FRONTEND_BUILD / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    async def dev_redirect() -> HTMLResponse:
        """In development (no build), show a helpful redirect message."""
        return HTMLResponse(
            "<html><body style='background:#0a0a0a;color:#f5f5f5;font-family:system-ui;"
            "display:flex;align-items:center;justify-content:center;height:100vh;'"
            ">"
            "<div style='text-align:center'>"
            "<h1>Sentinel AI API</h1>"
            "<p>API is running. Visit <a href='http://localhost:5173' "
            "style='color:#4dd9e8'>http://localhost:5173</a> for the React dev server,</p>"
            "<p>or run <code style='color:#22c55e'>cd frontend && npm run build</code> "
            "to serve the production build from here.</p>"
            "<p><a href='/api/docs' style='color:#4dd9e8'>API Documentation →</a></p>"
            "</div></body></html>"
        )
