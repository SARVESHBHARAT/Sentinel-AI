import streamlit as st

from sentinel.config import Settings
from sentinel.ai.triage_service import AITriageService, TriageError
from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory, Severity
from sentinel.services.incident_service import IncidentService
from sentinel.ui.components import badge, label, safe_error
from sentinel.time_utils import display_local


def render(repository: IncidentRepository, service: IncidentService, triage_service: AITriageService, settings: Settings) -> None:
    st.title("AI Triage")
    incident_id = st.session_state.get("selected_incident_id")
    if not incident_id:
        st.info("Select an incident in the Explorer or Overview before reviewing AI triage.")
        return
    incident = repository.get_incident(incident_id)
    st.subheader(f"{incident.incident_id} — {incident.title}")
    if st.button("Request reassessment" if repository.list_ai_assessments(incident_id) else "Run AI triage", type="primary", key=f"assess_{incident_id}"):
        try:
            with st.spinner("Generating an advisory assessment…"):
                triage_service.assess_incident(incident_id)
            st.success("Assessment saved. Previous assessments remain available below.")
            st.rerun()
        except TriageError as error:
            st.error(str(error))
    assessments = repository.list_ai_assessments(incident_id)
    if not assessments:
        if settings.effective_demo_mode:
            st.info("Demo mode is active. No demo assessment has been generated for this incident. Demo outputs are never represented as live model assessments.")
        else:
            st.info("No AI assessment is available yet. Model assessment generation will be added in the AI workflow phase.")
    else:
        for assessment in reversed(assessments):
            heading = "Demo assessment — not a live model result" if assessment.provider_mode == "demo" else f"OpenAI assessment · {assessment.model_name}"
            with st.expander(heading, expanded=True):
                first, second, third = st.columns(3)
                first.metric("Risk score", f"{assessment.risk_score}/100")
                second.metric("Confidence", f"{assessment.confidence:.0%}")
                with third:
                    st.caption("Suggested severity")
                    badge(assessment.suggested_severity, "severity")
                st.caption(f"Suggested category: {label(assessment.suggested_category)} · Generated {display_local(assessment.created_at)}")
                st.markdown(f"**Summary:** {assessment.concise_summary}")
                st.write(assessment.observed_failure_or_concern)
                st.markdown("**Severity rationale**")
                st.write(assessment.severity_explanation)
                st.markdown("**Recommended actions**")
                for recommendation in assessment.recommended_corrective_actions:
                    st.write(f"• {recommendation}")
    st.divider()
    st.subheader("Human review decision")
    st.caption("A reviewer remains responsible for the final severity determination.")
    if not assessments:
        return
    latest = assessments[-1]
    with st.form(f"triage_review_{incident_id}"):
        category = st.selectbox("Confirmed category", [item.value for item in IncidentCategory], index=[item.value for item in IncidentCategory].index(latest.suggested_category.value), format_func=label)
        severity = st.selectbox("Confirmed severity", [item.value for item in Severity], index=[item.value for item in Severity].index(latest.suggested_severity.value), format_func=label)
        reviewer = st.text_input("Reviewer", value=incident.assigned_reviewer or "", max_chars=150)
        justification = st.text_area("Override justification", max_chars=2_000, help="Required if you change the suggested category or severity.")
        if st.form_submit_button("Record human determination"):
            try:
                service.review_ai_suggestion(incident_id, latest, category=IncidentCategory(category), severity=Severity(severity), reviewer=reviewer or None, justification=justification or None)
                st.success("Human triage decision recorded.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception as error:
                safe_error("record the human determination", error)
