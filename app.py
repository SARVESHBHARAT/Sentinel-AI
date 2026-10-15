"""Sentinel AI Streamlit application."""
from collections import deque
from pathlib import Path
import sys
import time

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sentinel.config import Settings
from sentinel.ai import AITriageService
from sentinel.database.repositories import IncidentRepository
from sentinel.services import AnalyticsService, IncidentService, ReportService
from sentinel.ui.pages import details, explorer, model_intelligence, overview, report_incident, reports, settings, triage
from sentinel.ui.styles import apply_theme, page_header


class _ReadOnlyIncidentService(IncidentService):
    """Block every mutating service call when SENTINEL_READ_ONLY=true."""

    def _blocked(self) -> None:
        raise RuntimeError("Read-only mode is enabled; changes are disabled.")

    def submit(self, *args, **kwargs):
        self._blocked()

    def update(self, *args, **kwargs):
        self._blocked()

    def transition(self, *args, **kwargs):
        self._blocked()

    def add_note(self, *args, **kwargs):
        self._blocked()

    def add_corrective_action(self, *args, **kwargs):
        self._blocked()

    def review_ai_suggestion(self, *args, **kwargs):
        self._blocked()

    def verify(self, *args, **kwargs):
        self._blocked()

    def dispute(self, *args, **kwargs):
        self._blocked()

    def mark_unverified(self, *args, **kwargs):
        self._blocked()


class _ReadOnlyRepository(IncidentRepository):
    """Block direct repository writes (triage persistence, verification, demo reset)."""

    def _blocked(self) -> None:
        raise RuntimeError("Read-only mode is enabled; changes are disabled.")

    def create_incident(self, *args, **kwargs):
        self._blocked()

    def update_incident(self, *args, **kwargs):
        self._blocked()

    def transition_status(self, *args, **kwargs):
        self._blocked()

    def transition_verification(self, *args, **kwargs):
        self._blocked()

    def add_ai_assessment(self, *args, **kwargs):
        self._blocked()

    def add_reviewer_note(self, *args, **kwargs):
        self._blocked()

    def add_corrective_action(self, *args, **kwargs):
        self._blocked()

    def reset_demo_incidents(self, *args, **kwargs):
        self._blocked()


st.set_page_config(page_title="Sentinel AI", page_icon="S", layout="wide", initial_sidebar_state="expanded")
apply_theme()
settings_value = Settings.from_environment()
repository = IncidentRepository(settings_value.database_path)
if settings_value.read_only:
    repository.__class__ = _ReadOnlyRepository
repository.initialize()
incident_service: IncidentService = (_ReadOnlyIncidentService(repository) if settings_value.read_only
                                     else IncidentService(repository))


def _submission_allowed() -> bool:
    """In-memory per-process submission throttle (resets on restart; not shared across workers)."""
    now = time.monotonic()
    window = settings_value.submission_rate_window_seconds
    history: deque = st.session_state.setdefault("submission_times", deque())
    while history and now - history[0] > window:
        history.popleft()
    if len(history) >= settings_value.submission_rate_limit:
        return False
    history.append(now)
    return True
analytics_service = AnalyticsService(repository)
triage_service = AITriageService.from_settings(repository, settings_value)
report_service = ReportService(repository)


def open_incident(incident_id: str) -> None:
    st.session_state["selected_incident_id"] = incident_id
    st.session_state["active_page"] = "Incident Details"


_PAGE_ICONS = {
    "Overview": "▦",
    "Report an Incident": "✎",
    "Incident Explorer": "⌕",
    "Incident Details": "◫",
    "AI Triage": "✦",
    "Model Intelligence": "◈",
    "Reports": "⇩",
    "Settings": "⚙",
}


def _nav_label(page_name: str) -> str:
    return f"{_PAGE_ICONS.get(page_name, '•')}   {page_name}"


with st.sidebar:
    st.markdown(
        '<div class="sp-brand">'
        '<div class="sp-brand-mark">S</div>'
        '<div><div class="sp-brand-name">SENTINEL AI</div>'
        '<div class="sp-brand-sub">AI Incident Governance</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("")
    pills = []
    if settings_value.effective_demo_mode:
        pills.append('<span class="sp-pill sp-pill-demo">Demo mode</span>')
    if settings_value.read_only:
        pills.append('<span class="sp-pill sp-pill-readonly">Read-only</span>')
    if pills:
        st.markdown(" ".join(pills), unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["Overview", "Report an Incident", "Incident Explorer", "Incident Details", "AI Triage", "Model Intelligence", "Reports", "Settings"],
        key="active_page",
        label_visibility="collapsed",
        format_func=_nav_label,
    )
    st.markdown(
        '<div class="sp-side-note">Reviewer names are typed, not authenticated — '
        'use in a local or trusted environment only.</div>',
        unsafe_allow_html=True,
    )

if page == "Overview":
    overview.render(analytics_service, open_incident)
elif page == "Report an Incident":
    if settings_value.read_only:
        page_header("Report", "Report an Incident")
        st.warning("Read-only mode is enabled; new reports are disabled.")
    elif not _submission_allowed():
        page_header("Report", "Report an Incident")
        st.warning("Submission rate limit reached. Please try again later.")
    else:
        report_incident.render(incident_service, open_incident)
elif page == "Incident Explorer":
    explorer.render(repository, open_incident)
elif page == "Incident Details":
    details.render(repository, incident_service)
elif page == "AI Triage":
    triage.render(repository, incident_service, triage_service, settings_value)
elif page == "Model Intelligence":
    model_intelligence.render(repository, settings_value, open_incident)
elif page == "Reports":
    reports.render(repository, report_service)
else:
    settings.render(settings_value, repository)
