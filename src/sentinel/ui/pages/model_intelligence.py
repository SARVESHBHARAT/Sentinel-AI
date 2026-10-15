"""AI Model Observatory: exact-model leaderboards, drill-down, and comparisons.

All numbers are counts of *reported* incidents from the live database. They are
never usage-adjusted, never presented as safety scores, and synthetic demo
records are always separable and labelled.
"""

from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from sentinel.config import Settings
from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory, Severity, VerificationStatus
from sentinel.services.model_intelligence_service import COMPARISON_FORMULA, ComparisonWorkspace, ModelIntelligenceService
from sentinel.ui.components import escape_html, escape_markdown, label
from sentinel.ui.styles import ACCENT, ACCENT_2, MUTED, SEVERITY_COLORS, page_header, result_line, section_label, severity_bar_colors, style_chart

_DATASET_LABELS = {
    "all": "All records",
    "demo": "Synthetic demo only",
    "genuine": "Genuine reports only",
}
_RANK_LABELS = {
    "most_reported": "Most reported incidents",
    "fewest_reported": "Fewest reported incidents",
    "most_verified": "Most verified incidents",
    "most_high_critical": "Most high/critical incidents",
    "model": "Model identifier (A–Z)",
    "provider": "Provider (A–Z)",
}


def _bar(values: dict[str, int], title: str, color: str, semantic: bool = False) -> go.Figure:
    chart = go.Figure(go.Bar(
        x=list(values.keys()), y=list(values.values()),
        marker_color=severity_bar_colors(values) if semantic else color,
        marker_line=dict(width=0),
        hovertemplate="%{x}: %{y} reports<extra></extra>",
    ))
    return style_chart(chart, title=title, y_title="Reports")


def _trend_chart(values: dict[str, int], title: str) -> go.Figure:
    chart = go.Figure(go.Scatter(x=list(values.keys()), y=list(values.values()),
                                 mode="lines+markers", line=dict(color=ACCENT, width=2.5, shape="spline"),
                                 fill="tozeroy", fillcolor="rgba(255,255,255,0.06)",
                                 hovertemplate="%{x}: %{y} reports<extra></extra>"))
    return style_chart(chart, title=title, y_title="Reports")


#: Fixed display orders so severity/verification comparisons are stable even
#: when a selected model has zero rows for a level.
_SEVERITY_ORDER = ("low", "medium", "high", "critical")
_VERIFICATION_ORDER = ("reported", "ai_assessed", "human_reviewed", "verified", "disputed", "unverified")
_COMPARISON_PALETTE = (ACCENT, ACCENT_2, "#34D399", "#FBBF24", "#F87171", "#94A3B8", "#22D3EE", "#E2E8F0")


def comparison_counts(workspace: ComparisonWorkspace) -> dict[str, int]:
    """Incident-report counts per compared model, straight from the service."""
    return {item.affected_model_version: item.total for item in workspace.selected}


def comparison_severity_matrix(workspace: ComparisonWorkspace) -> dict[str, dict[str, int]]:
    """Severity breakdown per compared model (missing levels read as zero)."""
    matrix: dict[str, dict[str, int]] = {}
    for item in workspace.selected:
        matrix[item.affected_model_version] = {
            level: int(item.severity.get(level, 0)) for level in _SEVERITY_ORDER
        }
    return matrix


def comparison_verification_matrix(workspace: ComparisonWorkspace) -> dict[str, dict[str, int]]:
    """Verification breakdown per compared model (missing states read as zero)."""
    matrix: dict[str, dict[str, int]] = {}
    for item in workspace.selected:
        matrix[item.affected_model_version] = {
            state: int(item.verification_status.get(state, 0)) for state in _VERIFICATION_ORDER
        }
    return matrix


def comparison_category_matrix(workspace: ComparisonWorkspace) -> dict[str, dict[str, int]]:
    """Category breakdown per compared model, union of observed categories."""
    categories: list[str] = sorted({key for item in workspace.selected for key in item.category})
    return {
        item.affected_model_version: {name: int(item.category.get(name, 0)) for name in categories}
        for item in workspace.selected
    }


def _comparison_counts_chart(workspace: ComparisonWorkspace) -> go.Figure:
    counts = comparison_counts(workspace)
    chart = go.Figure(go.Bar(
        x=list(counts.keys()), y=list(counts.values()),
        marker_color=[_COMPARISON_PALETTE[index % len(_COMPARISON_PALETTE)] for index in range(len(counts))],
        marker_line=dict(width=0),
        hovertemplate="%{x}: %{y} reported incidents<extra></extra>",
    ))
    chart.update_xaxes(tickangle=-18, automargin=True)
    return style_chart(chart, title="Reported incidents by model (matching filters)", y_title="Reports")


def _comparison_grouped_chart(matrix: dict[str, dict[str, int]], levels: tuple[str, ...],
                              colors: dict[str, str] | None, title: str) -> go.Figure:
    chart = go.Figure()
    for position, level in enumerate(levels):
        chart.add_bar(
            name=level.replace("_", " "),
            x=list(matrix.keys()), y=[matrix[model].get(level, 0) for model in matrix],
            marker_color=(colors or {}).get(level, _COMPARISON_PALETTE[position % len(_COMPARISON_PALETTE)]),
            marker_line=dict(width=0),
            hovertemplate="%{x} · %{fullData.name}: %{y} reports<extra></extra>",
        )
    chart.update_layout(barmode="group", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                                                    font=dict(color=MUTED)))
    chart.update_xaxes(tickangle=-18, automargin=True)
    return style_chart(chart, title=title, y_title="Reports")



def render(repository: IncidentRepository, settings: Settings, open_incident: callable) -> None:
    page_header("Analytics", "AI Model Observatory",
                "Exact-model comparisons built from reported incidents, verified findings, and severity — transparent counts, never safety scores.")
    service = ModelIntelligenceService(repository, min_sample=settings.model_intelligence_min_sample)
    dataset = st.radio("Dataset", list(_DATASET_LABELS), format_func=lambda value: _DATASET_LABELS[value],
                       horizontal=True, key="observatory_dataset")
    if dataset == "demo":
        st.warning("Showing SYNTHETIC DEMO DATA only — fictional records, not evidence of real model performance.")
    elif dataset == "genuine":
        st.info("Showing genuine user reports only. Synthetic demo records are excluded.")
    else:
        st.caption("Showing all records (synthetic demo + genuine). Charts and counts mark which records are included.")
    with st.form("observatory_filters"):
        row1 = st.columns(4)
        provider = row1[0].text_input("Provider contains", placeholder="Optional")
        model = row1[1].text_input("Model contains", placeholder="Optional")
        version = row1[2].text_input("Version contains", placeholder="Optional")
        period = row1[3].selectbox("Reporting period", ["All time", "Last 30 days", "Last 90 days", "Last 365 days"])
        row2 = st.columns(4)
        category = row2[0].selectbox("Category", ["all"] + [item.value for item in IncidentCategory],
                                     format_func=lambda value: "All" if value == "all" else label(value))
        severity = row2[1].selectbox("Severity", ["all"] + [item.value for item in Severity],
                                     format_func=lambda value: "All" if value == "all" else label(value))
        verification = row2[2].selectbox("Verification", ["all"] + [item.value for item in VerificationStatus],
                                         format_func=lambda value: "All" if value == "all" else label(value))
        st.form_submit_button("Apply filters", type="primary")
    days = {"Last 30 days": 30, "Last 90 days": 90, "Last 365 days": 365}.get(period)
    date_from = date.today() - timedelta(days=days) if days else None
    filters = dict(category=None if category == "all" else category,
                   severity=None if severity == "all" else severity,
                   verification_status=None if verification == "all" else verification,
                   date_from=date_from, dataset=dataset)

    # ---------------------------- A. Global overview ----------------------------
    section_label("A · Global overview")
    metrics = service.overview_metrics(**filters)
    row_a = st.columns(4)
    row_a[0].metric("Incidents in dataset", metrics["total"])
    row_a[1].metric("Distinct providers", metrics["distinct_providers"])
    row_a[2].metric("Distinct model identifiers", metrics["distinct_models"])
    row_a[3].metric("Distinct model versions", metrics["distinct_versions"])
    row_b = st.columns(4)
    row_b[0].metric("Verified incidents", metrics["verified"])
    row_b[1].metric("Disputed incidents", metrics["disputed"])
    row_b[2].metric("High/critical severity", metrics["high_critical"])
    row_b[3].metric("Synthetic demo records", metrics["demo_records"])
    result_line(f"Dataset: {_DATASET_LABELS[dataset]} · {metrics['demo_records']} synthetic, "
                f"{metrics['genuine_records']} genuine · counts describe reported incidents only.")
    if metrics["total"] == 0:
        st.info("No matching records. Broaden the filters, change the dataset, or seed the synthetic demo dataset from Settings.")
        return

    # ------------------------- B. Exact-model leaderboard -------------------------
    section_label("B · Exact-model leaderboard")
    sort_key = st.selectbox("Rank by", list(_RANK_LABELS), format_func=lambda value: _RANK_LABELS[value],
                            key="observatory_sort")
    rows = service.leaderboard(sort_by=sort_key, **filters)
    needle_p = (provider or "").strip().lower()
    needle_m = (model or "").strip().lower()
    needle_v = (version or "").strip().lower()
    rows = [row for row in rows
            if needle_p in row.provider.lower() and needle_m in row.affected_model_name.lower()
            and needle_v in row.version_label.lower()]
    if not rows:
        st.info("No models match these filters. Broaden the filters or submit an incident with provider/model details.")
        return
    st.caption(f"Ranked by: **{_RANK_LABELS[sort_key]}** — a count of reported incidents in the selected dataset. "
               "It is not a safety score. Verification rate = verified ÷ total reported (per row).")
    rank_count = sort_key in ("most_reported", "fewest_reported", "most_verified", "most_high_critical")
    table = []
    for index, row in enumerate(rows, start=1):
        table.append({
            "Rank": str(index) if rank_count else "—",
            "Provider": escape_markdown(row.provider),
            "Model": escape_markdown(row.affected_model_name),
            "Version(s)": escape_markdown(row.version_label),
            "Reports": row.total,
            "Verified": row.verified,
            "Disputed": row.disputed,
            "High/critical": row.high_critical,
            "Verification rate": f"{row.verification_rate:.0%} (verified ÷ {row.total})" if row.verification_rate is not None else "—",
            "Top category": row.most_common_category,
            "Most recent": row.most_recent_report,
            "Evidence": "Sufficient" if row.sufficient else f"Insufficient (min {settings.model_intelligence_min_sample})",
        })
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.caption("Unknown versions remain “Unknown”; they are never merged into a known version. "
               "Higher report counts can reflect popularity, exposure, or reporting coverage — not proven risk.")

    # ------------------- C. Model detail and version comparison -------------------
    section_label("C · Model detail and version comparison")
    model_options = {f"{row.provider} · {row.affected_model_name}": (row.provider, row.affected_model_name)
                     for row in rows}
    choice = st.selectbox("Select exact model to inspect", list(model_options),
                          format_func=lambda value: escape_markdown(value), key="observatory_detail_choice")
    if choice:
        detail = service.model_detail(*model_options[choice], **filters)
        if detail.total == 0:
            st.info("No records for this model under the current filters.")
        else:
            sufficiency = ("Sufficient sample" if detail.sufficient
                           else f"Insufficient data for comparison (min {settings.model_intelligence_min_sample})")
            result_line(f"{detail.provider} · {detail.affected_model_name} — {detail.total} reported incident(s) · {sufficiency}")
            version_table = [{
                "Version": escape_markdown(version.affected_model_version),
                "Reports": version.total,
                "Verified": version.verified,
                "High/critical": version.high_critical,
                "Severity": version.severity or "No data",
                "Categories": version.category or "No data",
                "Verification": version.verification_status or "No data",
            } for version in detail.versions]
            st.dataframe(version_table, hide_index=True, use_container_width=True)
            left, right = st.columns(2)
            reported_vs_verified = {f"{version.affected_model_version}": version.verified for version in detail.versions}
            reported_counts = {version.affected_model_version: version.total for version in detail.versions}
            left.plotly_chart(_bar(reported_counts, "Reported incidents by version (versions never merged)", ACCENT),
                              use_container_width=True)
            right.plotly_chart(_bar(reported_vs_verified, "Verified incidents by version", ACCENT_2),
                               use_container_width=True)
            if detail.versions:
                st.plotly_chart(_trend_chart(detail.versions[-1].trend,
                                             f"Reporting trend · {detail.versions[-1].affected_model_version}"),
                                use_container_width=True)
            recent_table = [{
                "Incident": escape_markdown(item.incident_id),
                "Title": escape_markdown(item.title),
                "Version": escape_markdown(item.affected_model_version or "Unknown"),
                "Severity": label(item.severity),
                "Verification": label(item.verification_status),
                "Reported": item.report_date.isoformat(),
                "Source": "Synthetic demo" if item.is_demo else "Reported",
            } for item in detail.recent_incidents]
            st.dataframe(recent_table, hide_index=True, use_container_width=True)
            st.caption("Assessing model used by Sentinel AI is tracked separately from the affected model shown here.")

    # ---------------------------- D. Comparison workspace ----------------------------
    section_label("D · Comparison workspace")
    comparison_targets = st.multiselect(
        "Select exact models/versions to compare",
        [f"{row.provider} · {row.affected_model_name}" for row in rows],
        default=[f"{rows[0].provider} · {rows[0].affected_model_name}"] if rows else [],
        format_func=lambda value: escape_markdown(value), key="observatory_compare")
    if len(comparison_targets) >= 1:
        targets = [model_options[label] for label in comparison_targets]
        workspace = service.compare_models([(p, m, None) for p, m in targets], **filters)
        st.caption(f"Formula: `{COMPARISON_FORMULA}` Minimum sample: {settings.model_intelligence_min_sample} per target.")
        if not workspace.sufficient:
            st.warning("Insufficient data for comparison — at least one selected model has fewer than "
                       f"{settings.model_intelligence_min_sample} matching reports. Counts are shown without ranking.")
        else:
            st.info("Transparent share of matching reports per model. More reports do not prove a model is "
                    "less safe; usage is unknown and verification status must be checked per incident.")
        st.caption(f"Dataset compared: {_DATASET_LABELS[dataset]}."
                   + (" SYNTHETIC DEMO DATA included — fictional records, not real model performance."
                      if dataset in ("all", "demo") else ""))
        if sum(item.total for item in workspace.selected) == 0:
            st.info("No matching incidents for the selected models under the current filters. "
                    "Broaden the date range or filters, or select different models.")
        else:
            view = st.radio("Comparison view", ["Incident counts", "Severity", "Verification", "Categories"],
                            horizontal=True, key="observatory_compare_view")
            if view == "Incident counts":
                st.plotly_chart(_comparison_counts_chart(workspace), use_container_width=True)
            elif view == "Severity":
                st.plotly_chart(_comparison_grouped_chart(
                    comparison_severity_matrix(workspace), _SEVERITY_ORDER, SEVERITY_COLORS,
                    "Severity distribution by model (matching filters)"), use_container_width=True)
            elif view == "Verification":
                st.plotly_chart(_comparison_grouped_chart(
                    comparison_verification_matrix(workspace), _VERIFICATION_ORDER, None,
                    "Verification distribution by model (matching filters)"), use_container_width=True)
            else:
                matrix = comparison_category_matrix(workspace)
                categories = sorted({name for row in matrix.values() for name in row})
                if not categories:
                    st.info("No category data for the selected models under the current filters.")
                else:
                    st.plotly_chart(_comparison_grouped_chart(
                        matrix, tuple(categories), None,
                        "Category breakdown by model (matching filters)"), use_container_width=True)
            st.caption("Charts show counts of reported incidents matching the current filters and dataset. "
                       "They are not failure rates: model usage and exposure are unknown.")
        comparison_table = [{
            "Model": escape_html(item.affected_model_version),
            "Reports": item.total,
            "Verified": item.verified,
            "Disputed": item.verification_status.get("disputed", 0),
            "High/critical": item.high_critical,
            "Severity": item.severity or "No data",
            "Categories": item.category or "No data",
            "Verification": item.verification_status or "No data",
            "Evidence": "Sufficient" if item.total >= settings.model_intelligence_min_sample else "Insufficient",
        } for item in workspace.selected]
        st.dataframe(comparison_table, hide_index=True, use_container_width=True)
        st.caption(f"Dataset compared: {_DATASET_LABELS[dataset]}. Synthetic and genuine records are never "
                   "silently merged into an unlabelled ranking.")
    else:
        st.info("Select one or more models to compare.")



