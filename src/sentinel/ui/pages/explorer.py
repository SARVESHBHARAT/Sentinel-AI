

import streamlit as st

from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory, IncidentStatus, Severity
from sentinel.ui.components import choose_incident, enum_label, incident_rows, label


PAGE_SIZE = 25


def render(repository: IncidentRepository, open_incident: callable) -> None:
    st.title("Incident Explorer")
    st.markdown('<p class="sentinel-subtitle">Search the incident register and open an active case record.</p>', unsafe_allow_html=True)
    with st.form("explorer_filters"):
        row1 = st.columns(4)
        query = row1[0].text_input("Search", placeholder="Incident ID or title")
        category = row1[1].selectbox("Category", ["all"] + [item.value for item in IncidentCategory], format_func=lambda value: "All" if value == "all" else enum_label(value))
        severity = row1[2].selectbox("Severity", ["all"] + [item.value for item in Severity], format_func=lambda value: "All" if value == "all" else label(value))
        status = row1[3].selectbox("Status", ["all"] + [item.value for item in IncidentStatus], format_func=lambda value: "All" if value == "all" else label(value))
        row2 = st.columns(4)
        date_from = row2[0].date_input("Reported from", value=None)
        date_to = row2[1].date_input("Reported to", value=None)
        sort_by = row2[2].selectbox("Sort by", ["created_at", "updated_at", "report_date", "title", "severity", "status"], format_func=lambda value: label(value))
        descending = row2[3].checkbox("Newest / highest first", value=True)
        applied = st.form_submit_button("Apply filters", type="primary")
    if applied:
        st.session_state["explorer_page"] = 0
    page = st.session_state.get("explorer_page", 0)
    incidents, total = repository.search_incidents(query=query or None, category=None if category == "all" else category,
        severity=None if severity == "all" else severity, status=None if status == "all" else status,
        date_from=date_from, date_to=date_to, sort_by=sort_by, descending=descending, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    st.caption(f"{total} incident{'s' if total != 1 else ''} found")
    if not incidents:
        st.info("No incidents match these filters. Try broadening the search or submit a new incident.")
        return
    st.dataframe(incident_rows(incidents), hide_index=True, use_container_width=True)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    left, middle, right = st.columns([1, 2, 1])
    if left.button("Previous", disabled=page == 0, key="explorer_previous"):
        st.session_state["explorer_page"] = page - 1
        st.rerun()
    middle.markdown(f"<div style='text-align:center'>Page {page + 1} of {pages}</div>", unsafe_allow_html=True)
    if right.button("Next", disabled=page + 1 >= pages, key="explorer_next"):
        st.session_state["explorer_page"] = page + 1
        st.rerun()
    choose_incident(incidents, "explorer_incident", open_incident)
