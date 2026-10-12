import streamlit as st

from sentinel.database.repositories import IncidentRepository
from sentinel.services.report_service import ReportService
from sentinel.time_utils import display_local


def render(repository: IncidentRepository, report_service: ReportService) -> None:
    st.title("Reports")
    st.markdown('<p class="sentinel-subtitle">Generate a formal, portable case summary from the stored incident record.</p>', unsafe_allow_html=True)
    incident_id = st.session_state.get("selected_incident_id")
    if not incident_id:
        incidents = repository.list_incidents(limit=100)
        if not incidents:
            st.info("No incidents are available for reporting.")
            return
        incident_id = st.selectbox("Select incident", [item.incident_id for item in incidents], key="report_incident_choice")
    incident = repository.get_incident(incident_id)
    st.caption(f"Preparing report for {incident.incident_id} · Last updated {display_local(incident.updated_at)}")
    report = report_service.markdown(incident_id)
    st.text_area("Report preview", report, height=360, disabled=True, key=f"report_preview_{incident_id}")
    st.download_button("Download Markdown report", data=report, file_name=f"{incident_id.lower()}-report.md", mime="text/markdown", type="primary")
    try:
        pdf = report_service.pdf(incident_id)
        st.download_button("Download PDF report", data=pdf, file_name=f"{incident_id.lower()}-report.pdf", mime="application/pdf")
    except RuntimeError as error:
        st.info(str(error))
