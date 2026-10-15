from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from sentinel.domain.enums import IncidentCategory
from sentinel.services.analytics_service import AnalyticsService
from sentinel.ui.components import choose_incident, incident_rows, label
from sentinel.ui.styles import ACCENT, ACCENT_2, style_chart, page_header, section_label, severity_bar_colors


def _bar_chart(values: dict[str, int], title: str, color: str, semantic: bool = False) -> go.Figure:
    chart = go.Figure(go.Bar(
        x=list(values.keys()), y=list(values.values()),
        marker_color=severity_bar_colors(values) if semantic else color,
        marker_line=dict(width=0),
        hovertemplate="%{x}: %{y} incidents<extra></extra>",
    ))
    return style_chart(chart, title=title, y_title="Incidents")


def render(analytics: AnalyticsService, open_incident: callable) -> None:
    page_header("Overview", "Operations Dashboard",
                "Live operational view of recorded AI incidents and review activity, from the incident database.")
    with st.expander("Dashboard filters", expanded=False):
        first, second = st.columns(2)
        category = first.selectbox("Category", ["all"] + [item.value for item in IncidentCategory], format_func=lambda value: "All categories" if value == "all" else label(value), key="overview_category")
        period = second.selectbox("Reporting period", ["All time", "Last 30 days", "Last 90 days"], key="overview_period")
    date_from = None
    if period != "All time":
        date_from = date.today() - timedelta(days=int(period.split()[1]))
    incidents = analytics.filtered_incidents(category=None if category == "all" else category, date_from=date_from)
    metrics = analytics.metrics(incidents)
    cards = st.columns(4)
    cards[0].metric("Total incidents", metrics.total)
    cards[1].metric("Open incidents", metrics.open_incidents)
    cards[2].metric("High or critical", metrics.high_critical)
    cards[3].metric("Awaiting review", metrics.awaiting_review)
    if not incidents:
        st.info("No recorded incidents match these filters. Submit an incident to begin governance tracking.")
        return
    left, right = st.columns(2)
    left.plotly_chart(_bar_chart(analytics.distribution(incidents, "category"), "Incidents by category", ACCENT),
                      use_container_width=True)
    right.plotly_chart(_bar_chart(analytics.distribution(incidents, "severity"), "Severity distribution", ACCENT_2, semantic=True),
                       use_container_width=True)
    trend = analytics.trend(incidents)
    line = go.Figure(go.Scatter(
        x=list(trend), y=list(trend.values()), mode="lines+markers",
        line=dict(color=ACCENT, width=2.5, shape="spline"),
        fill="tozeroy", fillcolor="rgba(255,255,255,0.06)",
        hovertemplate="%{x}: %{y} reports<extra></extra>",
    ))
    st.plotly_chart(style_chart(line, title="Incident reporting trend", y_title="Reports"), use_container_width=True)
    section_label("Recent incidents")
    recent = sorted(incidents, key=lambda item: item.created_at, reverse=True)[:8]
    st.dataframe(incident_rows(recent), hide_index=True, use_container_width=True)
    choose_incident(recent, "overview_incident", open_incident)
