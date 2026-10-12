from collections.abc import Callable
import html

import streamlit as st

from sentinel.domain.enums import IncidentCategory, IncidentStatus
from sentinel.schemas.incident import Incident
from sentinel.time_utils import display_local


def label(value: object | None) -> str:
    if value is None:
        return "Not assessed"
    raw = getattr(value, "value", str(value))
    return raw.replace("_", " ").title()


def badge(value: object | None, kind: str) -> None:
    raw = getattr(value, "value", "unassessed") if value else "unassessed"
    safe_kind = html.escape(str(kind))
    safe_raw = html.escape(str(raw).replace("_", "-"))
    safe_label = html.escape(label(value))
    st.markdown(f'<span class="sentinel-badge {safe_kind}-{safe_raw}">{safe_label}</span>', unsafe_allow_html=True)


def incident_rows(incidents: list[Incident]) -> list[dict[str, str]]:
    return [
        {
            "Incident ID": item.incident_id,
            "Title": item.title,
            "Category": label(item.category),
            "Severity": label(item.severity),
            "Status": label(item.status),
            "Reported": item.report_date.isoformat(),
            "Updated": display_local(item.updated_at),
            "Source": "Demo" if item.is_demo else "Reported",
        }
        for item in incidents
    ]


def choose_incident(incidents: list[Incident], key: str, on_select: Callable[[str], None]) -> None:
    if not incidents:
        return
    selected = st.selectbox("Open incident", incidents, format_func=lambda item: f"{item.incident_id} — {item.title}", key=key)
    st.button("View incident", key=f"{key}_open", type="secondary", on_click=on_select, args=(selected.incident_id,))


def category_options(include_unknown: bool = False) -> list[str]:
    values = [item.value for item in IncidentCategory]
    return (["unknown"] if include_unknown else []) + values


def enum_label(value: str) -> str:
    return "I don't know" if value == "unknown" else label(value)


def safe_error(action: str, error: Exception) -> None:
    st.error(f"Unable to {action}. Your information was not changed. Please review the form and try again.")


def status_options(status: IncidentStatus) -> list[IncidentStatus]:
    from sentinel.domain.lifecycle import ALLOWED_TRANSITIONS
    return sorted(ALLOWED_TRANSITIONS[status], key=lambda item: item.value)
