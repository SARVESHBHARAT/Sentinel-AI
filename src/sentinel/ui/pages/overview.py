from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from sentinel.domain.enums import IncidentCategory
from sentinel.services.analytics_service import AnalyticsService
from sentinel.ui.components import choose_incident, incident_rows, label


def _bar_chart(values: dict[str, int], title: str, color: str) -> go.Figure:
    chart = go.Figure(go.Bar(x=list(values.keys()), y=list(values.values()), marker_color=color,
                              hovertemplate="%{x}: %{y} incidents<extra></extra>"))
    chart.update_layout(title=title, height=300, margin=dict(l=15, r=15, t=45, b=35),
                        paper_bgcolor="white", plot_bgcolor="white", yaxis_title="Incidents")
    return chart


def render(analytics: AnalyticsService, open_incident: callable) -> None:
    st.title("Overview")
    st.markdown('<p class="sentinel-subtitle">Operational view of recorded AI incidents and review activity.</p>', unsafe_allow_html=True)
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
    left.plotly_chart(_bar_chart(analytics.distribution(incidents, "category"), "Incidents by category", "#4f46e5"), use_container_width=True)
    right.plotly_chart(_bar_chart(analytics.distribution(incidents, "severity"), "Severity distribution", "#2563eb"), use_container_width=True)
    trend = analytics.trend(incidents)
    line = go.Figure(go.Scatter(x=list(trend), y=list(trend.values()), mode="lines+markers", line=dict(color="#4f46e5"), hovertemplate="%{x}: %{y} reports<extra></extra>"))
    line.update_layout(title="Incident reporting trend", height=300, margin=dict(l=15, r=15, t=45, b=35), paper_bgcolor="white", plot_bgcolor="white", yaxis_title="Reports")
    st.plotly_chart(line, use_container_width=True)
    st.subheader("Recent incidents")
    recent = sorted(incidents, key=lambda item: item.created_at, reverse=True)[:8]
    st.dataframe(incident_rows(recent), hide_index=True, use_container_width=True)
    choose_incident(recent, "overview_incident", open_incident)
