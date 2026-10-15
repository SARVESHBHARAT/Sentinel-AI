from datetime import date

import streamlit as st
from pydantic import ValidationError

from sentinel.domain.enums import IncidentCategory
from sentinel.schemas.incident import CreateIncident
from sentinel.services.incident_service import IncidentService
from sentinel.ui.components import category_options, enum_label
from sentinel.ui.styles import page_header, section_label


def render(service: IncidentService, open_incident: callable) -> None:
    page_header("Report", "Report an Incident",
                "Provide enough context for a reviewer to assess the event. Avoid credentials and unnecessary personal data.")
    if "submitted_incident_id" in st.session_state:
        incident_id = st.session_state["submitted_incident_id"]
        st.success(f"Incident {incident_id} was submitted and is awaiting review.")
        st.button("Open incident details", key="open_new_incident", on_click=open_incident, args=(incident_id,))
    with st.form("incident_report_form", clear_on_submit=False):
        section_label("01 · What happened")
        title = st.text_input("Incident title *", max_chars=300, placeholder="Brief, factual summary")
        description = st.text_area("Detailed description *", max_chars=10_000, height=180, help="Include what occurred, where it was observed, and why it may matter.")
        first, second = st.columns(2)
        category_choice = first.selectbox("Incident category", category_options(include_unknown=True), format_func=enum_label, help="Choose ‘I don’t know’ if classification is uncertain.")
        occurrence = second.date_input("Occurrence date", value=None, max_value=date.today(), help="Leave blank if unknown.")
        section_label("02 · System and impact")
        st.caption("Describe the AI system involved in this incident — not the model that may later analyze this report.")
        left, right = st.columns(2)
        affected_system = left.text_input("Affected AI system", max_chars=200, placeholder="Optional")
        provider = right.text_input("Provider", max_chars=200, placeholder="Optional: e.g. Acme AI")
        model_left, model_right = st.columns(2)
        affected_model_name = model_left.text_input("Affected model name", max_chars=200, placeholder="Optional: leave blank if unknown")
        affected_model_version = model_right.text_input("Affected model version", max_chars=100, placeholder="Optional: leave blank if unknown",
                                                        help="Letters, numbers, dots, underscores, plus and hyphen only (e.g. 2026.01, v1, snapshot-abc).")
        impact = st.text_area("Potential impact", max_chars=5_000, height=100, placeholder="Optional: describe actual or plausible harm.")
        population = st.text_input("Affected population", max_chars=2_000, placeholder="Optional")
        evidence = st.text_area("Evidence references", max_chars=6_000, height=80, help="One reference per line. Do not paste secrets or sensitive raw data.")
        section_label("03 · Reporter")
        anonymous = st.checkbox("Submit anonymously", value=False)
        reporter_name = st.text_input("Name", max_chars=150, disabled=anonymous)
        reporter_contact = st.text_input("Contact", max_chars=254, disabled=anonymous)
        reviewed = st.checkbox("I have reviewed this report and confirm it is accurate to the best of my knowledge.")
        submitted = st.form_submit_button("Submit incident", type="primary")
    if not submitted:
        return
    if not reviewed:
        st.error("Please confirm that you have reviewed this report before submitting.")
        return
    try:
        payload = CreateIncident(
            title=title, description=description,
            category=IncidentCategory.OTHER if category_choice == "unknown" else IncidentCategory(category_choice),
            occurrence_date=occurrence, potential_impact=impact or None, affected_population=population or None,
            affected_system=affected_system or None, provider=provider or None,
            affected_model_name=affected_model_name or None, affected_model_version=affected_model_version or None,
            evidence_references=[line.strip() for line in evidence.splitlines() if line.strip()],
            anonymous_report=anonymous, reporter_name=None if anonymous else reporter_name or None,
            reporter_contact=None if anonymous else reporter_contact or None,
        )
        with st.spinner("Saving incident securely…"):
            incident = service.submit(payload)
        st.session_state["submitted_incident_id"] = incident.incident_id
        st.rerun()
    except ValidationError as error:
        st.error("Please correct the highlighted report details.")
        for item in error.errors():
            st.caption(item["msg"])
    except Exception:
        st.error("The incident could not be saved. No report was created; please try again.")
