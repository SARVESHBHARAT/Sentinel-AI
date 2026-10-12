import streamlit as st

from sentinel.database.repositories import IncidentNotFoundError, IncidentRepository
from sentinel.domain.enums import CategorySource, IncidentCategory, Severity, SeveritySource
from sentinel.schemas.incident import CorrectiveAction, IncidentUpdate, ReviewerNote
from sentinel.services.incident_service import IncidentService
from sentinel.ui.components import badge, escape_markdown, label, safe_error, status_options
from sentinel.time_utils import display_local


def render(repository: IncidentRepository, service: IncidentService) -> None:
    st.title("Incident Details")
    incident_id = st.session_state.get("selected_incident_id")
    if not incident_id:
        st.info("Select an incident from Overview or Incident Explorer to view its case details.")
        return
    try:
        incident = repository.get_incident(incident_id)
    except IncidentNotFoundError:
        st.error("This incident is no longer available.")
        return
    st.caption(f"{incident.incident_id} · Reported {incident.report_date.isoformat()} · Updated {display_local(incident.updated_at)}")
    columns = st.columns([3, 1, 1])
    # The title is reporter-supplied: escape it so Markdown constructs in the
    # text (links, images) render literally instead of loading remote content.
    columns[0].subheader(escape_markdown(incident.title))
    with columns[1]:
        st.caption("Status")
        badge(incident.status, "status")
    with columns[2]:
        st.caption("Severity")
        badge(incident.severity, "severity")
    if incident.is_demo:
        st.warning("This is an explicitly marked demo record.")
    overview, investigation, activity = st.tabs(["Case overview", "Investigation", "Activity"])
    with overview:
        st.subheader("Description")
        st.text(incident.description)
        left, right = st.columns(2)
        with left:
            st.caption("Category")
            st.write(label(incident.category))
            st.caption("Affected AI system")
            st.write(escape_markdown(incident.affected_system) or "Not provided")
            st.caption("Provider")
            st.write(escape_markdown(incident.provider) or "Not provided")
        with right:
            st.caption("Occurrence date")
            st.write(incident.occurrence_date.isoformat() if incident.occurrence_date else "Not provided")
            st.caption("Affected population")
            st.write(escape_markdown(incident.affected_population) or "Not provided")
            st.caption("Potential impact")
            st.write(escape_markdown(incident.potential_impact) or "Not provided")
            st.caption("Resolution summary")
            st.text(incident.resolution_summary or "Unknown / not applicable")
        references = repository.list_evidence_references(incident.incident_id)
        st.caption("Evidence references")
        st.text("\n".join(f"• {reference}" for reference in references) if references else "None provided")
    with investigation:
        _render_review_controls(incident, service)
        st.divider()
        _render_note_form(incident.incident_id, service)
        _render_action_form(incident.incident_id, service)
        notes = repository.list_reviewer_notes(incident.incident_id)
        if notes:
            st.subheader("Reviewer notes")
            for note in notes:
                # The author name is reviewer-supplied; escape the whole line.
                st.markdown(f"**{escape_markdown(note.author or 'Unattributed reviewer')}** · {display_local(note.created_at)}")
                st.text(note.body)
        actions = repository.list_corrective_actions(incident.incident_id)
        if actions:
            st.subheader("Corrective actions")
            st.dataframe([{"Action": action.title, "Type": action.action_kind.title(), "Owner": action.owner or "Unassigned", "Status": label(action.status), "Due": action.due_date.isoformat() if action.due_date else "—"} for action in actions], hide_index=True, use_container_width=True)
    with activity:
        events = repository.list_audit_events(incident.incident_id)
        st.dataframe([{"Time": display_local(event.created_at), "Event": label(event.event_type), "Actor": event.actor or "System", "Details": event.details or "—"} for event in events], hide_index=True, use_container_width=True)


def _render_review_controls(incident, service: IncidentService) -> None:
    st.subheader("Review controls")
    transitions = status_options(incident.status)
    if transitions:
        target = st.selectbox("Change status", transitions, format_func=label, key=f"status_target_{incident.incident_id}")
        if st.button("Update status", key=f"status_update_{incident.incident_id}"):
            try:
                service.transition(incident.incident_id, target, actor="Reviewer")
                st.success("Incident status updated.")
                st.rerun()
            except Exception as error:
                safe_error("update status", error)
    else:
        st.caption("This incident is closed. Reopen support can be added through a governance policy update.")
    with st.form(f"case_assignment_{incident.incident_id}"):
        reviewer = st.text_input("Assigned reviewer", value=incident.assigned_reviewer or "", max_chars=150)
        category = st.selectbox("Human-confirmed category", [item.value for item in IncidentCategory], index=[item.value for item in IncidentCategory].index(incident.category.value), format_func=label)
        severity = st.selectbox("Human severity", ["unchanged"] + [item.value for item in Severity], format_func=lambda value: "Unchanged" if value == "unchanged" else label(value))
        resolution = st.text_area("Resolution summary", value=incident.resolution_summary or "", max_chars=5_000, help="Required by governance policy before closing an incident.")
        if st.form_submit_button("Save review assignment"):
            fields = {"assigned_reviewer": reviewer or None, "category": IncidentCategory(category), "category_source": CategorySource.HUMAN, "resolution_summary": resolution or None}
            if severity != "unchanged":
                fields.update({"severity": Severity(severity), "severity_source": SeveritySource.HUMAN})
            try:
                service.update(incident.incident_id, IncidentUpdate(**fields), actor="Reviewer")
                st.success("Review assignment saved.")
                st.rerun()
            except Exception as error:
                safe_error("save the review assignment", error)


def _render_note_form(incident_id: str, service: IncidentService) -> None:
    with st.form(f"note_form_{incident_id}"):
        st.subheader("Add reviewer note")
        author = st.text_input("Reviewer name", max_chars=150)
        body = st.text_area("Note", max_chars=10_000, height=100)
        if st.form_submit_button("Add note"):
            try:
                service.add_note(ReviewerNote(incident_id=incident_id, author=author or None, body=body))
                st.rerun()
            except Exception as error:
                safe_error("add the note", error)


def _render_action_form(incident_id: str, service: IncidentService) -> None:
    with st.expander("Add corrective action"):
        with st.form(f"action_form_{incident_id}"):
            title = st.text_input("Action title", max_chars=300)
            action_kind = st.selectbox("Action type", ["corrective", "preventive"], format_func=str.title)
            owner = st.text_input("Owner", max_chars=150)
            due_date = st.date_input("Due date", value=None)
            if st.form_submit_button("Add action"):
                try:
                    service.add_corrective_action(CorrectiveAction(incident_id=incident_id, title=title, action_kind=action_kind, owner=owner or None, due_date=due_date))
                    st.rerun()
                except Exception as error:
                    safe_error("add the corrective action", error)
