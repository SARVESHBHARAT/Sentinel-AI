"""Sentinel AI Streamlit application."""
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sentinel.config import Settings
from sentinel.ai import AITriageService
from sentinel.database.repositories import IncidentRepository
from sentinel.services import AnalyticsService, IncidentService, ReportService
from sentinel.ui.pages import details, explorer, overview, report_incident, reports, settings, triage
from sentinel.ui.styles import apply_theme


st.set_page_config(page_title="Sentinel AI", page_icon="S", layout="wide", initial_sidebar_state="expanded")
apply_theme()
settings_value = Settings.from_environment()
repository = IncidentRepository(settings_value.database_path)
repository.initialize()
incident_service = IncidentService(repository)
analytics_service = AnalyticsService(repository)
triage_service = AITriageService.from_settings(repository, settings_value)
report_service = ReportService(repository)


def open_incident(incident_id: str) -> None:
    st.session_state["selected_incident_id"] = incident_id
    st.session_state["active_page"] = "Incident Details"


with st.sidebar:
    st.title("Sentinel AI")
    st.caption("Incident governance portal")
    if settings_value.effective_demo_mode:
        st.caption("DEMO MODE")
    page = st.radio(
        "Navigation",
        ["Overview", "Report an Incident", "Incident Explorer", "Incident Details", "AI Triage", "Reports", "Settings"],
        key="active_page",
        label_visibility="collapsed",
    )

if page == "Overview":
    overview.render(analytics_service, open_incident)
elif page == "Report an Incident":
    report_incident.render(incident_service, open_incident)
elif page == "Incident Explorer":
    explorer.render(repository, open_incident)
elif page == "Incident Details":
    details.render(repository, incident_service)
elif page == "AI Triage":
    triage.render(repository, incident_service, triage_service, settings_value)
elif page == "Reports":
    reports.render(repository, report_service)
else:
    settings.render(settings_value, repository)
