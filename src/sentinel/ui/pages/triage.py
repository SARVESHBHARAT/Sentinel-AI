import streamlit as st

from sentinel.ai.triage_service import AITriageService, TriageError
from sentinel.config import Settings
from sentinel.database.repositories import IncidentNotFoundError, IncidentRepository
from sentinel.domain.enums import IncidentCategory, Severity
from sentinel.services.incident_service import IncidentService
from sentinel.time_utils import display_local
from sentinel.ui.components import badge, escape_html, escape_markdown, fetch_incident_options, incident_picker, label, safe_error
from sentinel.ui.styles import page_header, section_label


def _go_to_report() -> None:
    st.session_state["active_page"] = "Report an Incident"


def render(repository: IncidentRepository, service: IncidentService, triage_service: AITriageService, settings: Settings) -> None:
    page_header("AI Workflow", "AI Triage")
    if not fetch_incident_options(repository):
        st.info("No incidents are recorded yet. Report an incident, then run triage here.")
        st.button("Report an incident", key="triage_report_incident", on_click=_go_to_report)
        return
    selected = incident_picker(repository, key="triage_incident_picker")
    if selected != st.session_state.get("selected_incident_id"):
        st.session_state["selected_incident_id"] = selected
        st.rerun()
        return
    try:
        incident = repository.get_incident(selected)
    except IncidentNotFoundError:
        # The selected incident may have been deleted (for example by the
        # demo-record reset) since it was last opened.
        st.session_state.pop("selected_incident_id", None)
        st.warning("This incident is no longer available. Select another incident below.")
        st.rerun()
        return
    st.markdown(f'<div class="sp-case-title">{escape_html(incident.title)}</div>', unsafe_allow_html=True)
    meta = st.columns([1.6, 1, 1])
    meta[0].caption(f"{incident.incident_id} · {label(incident.category)}")
    with meta[1]:
        st.caption("Incident status")
        badge(incident.status, "status")
    with meta[2]:
        st.caption("Severity")
        badge(incident.severity, "severity")
    if incident.is_demo:
        st.warning("This is an explicitly marked demo record.")
    if st.button("Request reassessment" if repository.list_ai_assessments(selected) else "Run AI triage",
                 type="primary", key=f"assess_{selected}", disabled=settings.read_only):
        try:
            with st.spinner("Generating an advisory assessment…"):
                triage_service.assess_incident(selected)
            st.success("Assessment saved. Previous assessments remain available below.")
            st.rerun()
        except TriageError as error:
            st.error(str(error))
    if settings.read_only:
        st.caption("Read-only mode is enabled: AI triage cannot generate or persist assessments.")
    assessments = repository.list_ai_assessments(selected)
    if not assessments:
        if settings.effective_demo_mode:
            st.info("Demo mode is active. No demo assessment has been generated for this incident. Demo outputs are never represented as live model assessments.")
        else:
            st.info("No AI assessment is available yet. Model assessment generation will be added in the AI workflow phase.")
    else:
        section_label("AI assessment history · most recent first")
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
                provenance = f"Assessed by `{assessment.model_name}`"
                if assessment.model_version:
                    provenance += f" · version `{assessment.model_version}`"
                provenance += f" · mode `{assessment.provider_mode}` · prompt `{assessment.prompt_version}`"
                st.caption(provenance)
                # Assessment text is model output derived from the untrusted report,
                # so render it literally rather than letting it become links.
                st.markdown(f"**Summary:** {escape_markdown(assessment.concise_summary)}")
                st.write(escape_markdown(assessment.observed_failure_or_concern))
                st.markdown("**Severity rationale**")
                st.write(escape_markdown(assessment.severity_explanation))
                st.markdown("**Recommended actions**")
                for recommendation in assessment.recommended_corrective_actions:
                    st.write(f"• {escape_markdown(recommendation)}")
    st.divider()
    section_label("Human review decision")
    st.caption("A reviewer remains responsible for the final severity determination. AI output is advisory only.")
    if not assessments:
        return
    latest = assessments[-1]
    with st.form(f"triage_review_{selected}"):
        category = st.selectbox("Confirmed category", [item.value for item in IncidentCategory], index=[item.value for item in IncidentCategory].index(latest.suggested_category.value), format_func=label)
        severity = st.selectbox("Confirmed severity", [item.value for item in Severity], index=[item.value for item in Severity].index(latest.suggested_severity.value), format_func=label)
        reviewer = st.text_input("Reviewer", value=incident.assigned_reviewer or "", max_chars=150)
        justification = st.text_area("Override justification", max_chars=2_000, help="Required if you change the suggested category or severity.")
        if st.form_submit_button("Record human determination"):
            try:
                service.review_ai_suggestion(selected, latest, category=IncidentCategory(category), severity=Severity(severity), reviewer=reviewer or None, justification=justification or None)
                st.success("Human triage decision recorded.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception as error:
                safe_error("record the human determination", error)
