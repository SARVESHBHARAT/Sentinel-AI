import streamlit as st

from sentinel.database.repositories import IncidentNotFoundError, IncidentRepository
from sentinel.domain.enums import CategorySource, IncidentCategory, Severity, SeveritySource, VerificationStatus
from sentinel.domain.lifecycle import ALLOWED_VERIFICATION_TRANSITIONS
from sentinel.schemas.incident import CorrectiveAction, IncidentUpdate, ReviewerNote
from sentinel.services.incident_service import IncidentService
from sentinel.ui.components import badge, escape_html, escape_markdown, fetch_incident_options, incident_picker, label, safe_error, status_options
from sentinel.time_utils import display_local
from sentinel.ui.styles import page_header, section_label


def _go_to_report() -> None:
    st.session_state["active_page"] = "Report an Incident"


def render(repository: IncidentRepository, service: IncidentService) -> None:
    page_header("Case File", "Incident Details")
    if not fetch_incident_options(repository):
        st.info("No incidents are recorded yet. Report an incident to begin governance tracking.")
        st.button("Report an incident", key="details_report_incident", on_click=_go_to_report)
        return
    selected = incident_picker(repository, key="details_incident_picker")
    if selected != st.session_state.get("selected_incident_id"):
        st.session_state["selected_incident_id"] = selected
        st.rerun()
        return
    try:
        incident = repository.get_incident(selected)
    except IncidentNotFoundError:
        # Stale selection (e.g. incident deleted by demo reset): recover and
        # let the reviewer pick another incident on the next render.
        st.session_state.pop("selected_incident_id", None)
        st.warning("The previously selected incident is no longer available. Select another incident below.")
        st.rerun()
        return
    # The title is reporter-supplied: HTML-escape it for the raw-HTML heading so
    # Markdown constructs (links, images) render literally instead of loading
    # remote content, without showing Markdown-escape backslashes.
    st.markdown(f'<div class="sp-case-title">{escape_html(incident.title)}</div>', unsafe_allow_html=True)
    meta = st.columns([1.2, 1, 1, 1.6])
    meta[0].caption(f"{incident.incident_id} · Reported {incident.report_date.isoformat()}")
    with meta[1]:
        st.caption("Incident status")
        badge(incident.status, "status")
    with meta[2]:
        st.caption("Severity")
        badge(incident.severity, "severity")
    with meta[3]:
        st.caption("Verification")
        badge(incident.verification_status, "verification")
    st.caption(f"Last updated {display_local(incident.updated_at)}")
    if incident.is_demo:
        st.warning("This is an explicitly marked demo record.")
    overview, investigation, activity = st.tabs(["Case overview", "Investigation", "Activity"])
    with overview:
        section_label("Incident description")
        st.text(incident.description)
        left, right = st.columns(2)
        with left:
            st.caption("Category")
            st.write(label(incident.category))
            st.caption("Affected AI system")
            st.write(escape_markdown(incident.affected_system) or "Not provided")
            st.caption("Provider")
            st.write(escape_markdown(incident.provider) or "Not provided")
            st.caption("Affected model")
            st.write(escape_markdown(incident.affected_model_name) or "Unknown")
            st.caption("Affected model version")
            st.write(escape_markdown(incident.affected_model_version) or "Unknown")
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
        _render_verification_controls(incident, service, repository)
        st.divider()
        _render_note_form(incident.incident_id, service)
        _render_action_form(incident.incident_id, service)
        notes = repository.list_reviewer_notes(incident.incident_id)
        if notes:
            section_label("Reviewer notes")
            for note in notes:
                # The author name is reviewer-supplied; escape the whole line.
                st.markdown(f"**{escape_markdown(note.author or 'Unattributed reviewer')}** · {display_local(note.created_at)}")
                st.text(note.body)
        actions = repository.list_corrective_actions(incident.incident_id)
        if actions:
            section_label("Corrective actions")
            st.dataframe([{"Action": action.title, "Type": action.action_kind.title(), "Owner": action.owner or "Unassigned", "Status": label(action.status), "Due": action.due_date.isoformat() if action.due_date else "—"} for action in actions], hide_index=True, use_container_width=True)
    with activity:
        events = repository.list_audit_events(incident.incident_id)
        if not events:
            st.info("No investigation events recorded yet.")
        else:
            st.dataframe([{"Time": display_local(event.created_at), "Event": label(event.event_type), "Actor": event.actor or "System", "Details": event.details or "—"} for event in events], hide_index=True, use_container_width=True)


def _render_review_controls(incident, service: IncidentService) -> None:
    section_label("Status and assignment")
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


def _render_verification_controls(incident, service: IncidentService, repository: IncidentRepository) -> None:
    section_label("Verification of the reported event")
    st.caption("Verification is separate from the incident status lifecycle. AI triage never verifies an incident.")
    st.write(f"**Current:** {label(incident.verification_status)}")
    allowed = sorted(ALLOWED_VERIFICATION_TRANSITIONS[incident.verification_status], key=lambda item: item.value)
    if not allowed:
        st.caption("No further verification transitions are available.")
    else:
        st.caption(f"Allowed next states: {', '.join(label(item) for item in allowed)}")
        with st.form(f"verification_form_{incident.incident_id}"):
            target = st.selectbox("Change verification to", allowed, format_func=label)
            reviewer = st.text_input("Reviewer name *", max_chars=150)
            reason = st.text_area("Reason *", max_chars=2_000,
                                  help="Required: why this verification change is warranted.")
            if st.form_submit_button("Record verification change"):
                try:
                    if not reviewer.strip():
                        st.error("A reviewer name is required.")
                    elif not reason.strip():
                        st.error("A reason is required for verification changes.")
                    elif target == VerificationStatus.VERIFIED:
                        service.verify(incident.incident_id, reviewer=reviewer, justification=reason)
                        st.success("Incident verified.")
                        st.rerun()
                    elif target == VerificationStatus.DISPUTED:
                        service.dispute(incident.incident_id, reviewer=reviewer, justification=reason)
                        st.success("Incident disputed.")
                        st.rerun()
                    elif target == VerificationStatus.UNVERIFIED:
                        service.mark_unverified(incident.incident_id, reviewer=reviewer, justification=reason)
                        st.success("Incident marked unverified.")
                        st.rerun()
                    else:
                        repository.transition_verification(incident.incident_id, target, actor=reviewer)
                        repository.add_reviewer_note(ReviewerNote(
                            incident_id=incident.incident_id, author=reviewer,
                            body=f"Verification note: {reason.strip()}"))
                        st.success("Verification status updated.")
                        st.rerun()
                except ValueError as error:
                    st.error(str(error))
                except Exception as error:
                    safe_error("record the verification change", error)
    st.caption("Verification history (audit trail)")
    events = [event for event in repository.list_audit_events(incident.incident_id)
              if event.event_type == "verification_changed"]
    if not events:
        st.caption("No verification changes recorded.")
    for event in events:
        st.text(f"• {display_local(event.created_at)} | {event.actor or 'System'} | {event.details or 'No details'}")
    st.caption("Reviewer identity here is a typed name, not authenticated access. Keep this app in a local or trusted environment.")


def _render_note_form(incident_id: str, service: IncidentService) -> None:
    with st.form(f"note_form_{incident_id}"):
        section_label("Add reviewer note")
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
