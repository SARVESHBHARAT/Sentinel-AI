"""Regression tests for the UI design-system injection (Phase 8 CSS-rendering fix)."""

import html

from sentinel.demo_seed import seed_demo_dataset
from sentinel.domain.enums import IncidentCategory
from sentinel.schemas.incident import CreateIncident
from sentinel.services.model_intelligence_service import ModelIntelligenceService
from sentinel.ui import styles
from sentinel.ui.components import escape_html, escape_markdown
from sentinel.ui.pages import model_intelligence as mi_page


def test_apply_theme_wraps_css_in_style_tag(monkeypatch):
    """The stylesheet must be injected inside a single <style> block.

    Regression: _CSS previously lacked the opening <style> tag (and carried a
    stray </style>), so Streamlit rendered the entire stylesheet as visible text
    on every page.
    """
    captured = {}

    def fake_markdown(body, unsafe_allow_html=False, **kwargs):
        captured["body"] = body
        captured["unsafe"] = unsafe_allow_html

    monkeypatch.setattr(styles.st, "markdown", fake_markdown)
    styles.apply_theme()
    body = captured["body"]
    assert body.startswith("<style>")
    assert body.endswith("</style>")
    assert body.count("<style>") == 1
    assert body.count("</style>") == 1
    assert captured["unsafe"] is True
    # Design-system content is present inside the style block.
    assert ".sp-pagehead" in body
    assert ".sentinel-badge" in body


def test_css_payload_has_no_stray_style_tags():
    """The raw _CSS payload must be bare CSS — tags are added by apply_theme only."""
    assert "<style>" not in styles._CSS
    assert "</style>" not in styles._CSS
    assert "============================ base" in styles._CSS


_DEMO_TITLE = ("[DEMO] Fictional incorrect classification and prediction -- spam filter quarantines "
               "legitimate invoices from a new vendor [gpt-4o-mini SYN-159]")


def test_escape_html_preserves_brackets_and_hyphens_for_raw_html_headings():
    rendered = escape_html(_DEMO_TITLE)
    assert rendered == html.escape(_DEMO_TITLE, quote=True)
    assert "\\[" not in rendered and "\\-" not in rendered
    assert "[DEMO]" in rendered and "--" in rendered and "[gpt-4o-mini SYN-159]" in rendered
    assert escape_html('<img src=x onerror=alert(1)>') == '&lt;img src=x onerror=alert(1)&gt;'
    assert escape_html(None) == ""


def test_escape_html_preserves_legitimate_backslashes():
    assert escape_html("C:\\model\\weights\\final.bin") == "C:\\model\\weights\\final.bin"
    assert escape_html("pattern ^\\d+$ matches digits") == "pattern ^\\d+$ matches digits"


def test_comparison_chart_data_comes_from_service_results(repository):
    service = ModelIntelligenceService(repository)
    seed_demo_dataset(repository)
    workspace = service.compare_models([("OpenAI", "gpt-4o", None), ("Anthropic", "claude-3-5-sonnet", None)])
    counts = mi_page.comparison_counts(workspace)
    assert counts == {item.affected_model_version: item.total for item in workspace.selected}
    assert counts["gpt-4o · all versions"] == 22
    assert counts["claude-3-5-sonnet · all versions"] == 18


def test_comparison_changing_models_updates_chart_data(repository):
    service = ModelIntelligenceService(repository)
    seed_demo_dataset(repository)
    first = mi_page.comparison_counts(service.compare_models([("OpenAI", "gpt-4o", None)]))
    second = mi_page.comparison_counts(service.compare_models(
        [("OpenAI", "gpt-4o", None), ("Google", "gemini-1.5-pro", None)]))
    assert set(second) == {"gpt-4o · all versions", "gemini-1.5-pro · all versions"}
    assert second["gpt-4o · all versions"] == first["gpt-4o · all versions"] == 22
    assert second["gemini-1.5-pro · all versions"] == 18


def test_comparison_severity_matches_service_and_filters_respected(repository):
    from datetime import date
    service = ModelIntelligenceService(repository)
    seed_demo_dataset(repository)
    workspace = service.compare_models([("OpenAI", "gpt-4o", None), ("Anthropic", "claude-3-5-sonnet", None)])
    matrix = mi_page.comparison_severity_matrix(workspace)
    for item in workspace.selected:
        for level in ("low", "medium", "high", "critical"):
            assert matrix[item.affected_model_version][level] == item.severity.get(level, 0)
        assert sum(matrix[item.affected_model_version].values()) == item.total
    filtered = service.compare_models(
        [("OpenAI", "gpt-4o", None), ("Anthropic", "claude-3-5-sonnet", None)], severity="critical")
    assert sum(mi_page.comparison_counts(filtered).values()) <= sum(mi_page.comparison_counts(workspace).values())
    dated = service.compare_models([("OpenAI", "gpt-4o", None)],
                                    date_from=date(2026, 9, 1), date_to=date(2026, 9, 30))
    assert 0 < dated.selected[0].total < workspace.selected[0].total


def test_comparison_empty_results_handled(repository):
    from datetime import date
    service = ModelIntelligenceService(repository)
    seed_demo_dataset(repository)
    workspace = service.compare_models([("Nobody", "no-such-model", None)], date_from=date(2026, 9, 1))
    assert mi_page.comparison_counts(workspace) == {"no-such-model · all versions": 0}
    assert all(value == 0 for row in mi_page.comparison_severity_matrix(workspace).values()
               for value in row.values())


def test_escape_markdown_still_neutralises_links_for_markdown_contexts():
    assert "\\[" in escape_markdown("[DEMO] title")
    assert "![x]" not in escape_markdown("see ![x](https://example.invalid/track.png)")


def test_comparison_charts_render_counts_and_distributions(repository):
    service = ModelIntelligenceService(repository)
    seed_demo_dataset(repository)
    workspace = service.compare_models([("OpenAI", "gpt-4o", None), ("Anthropic", "claude-3-5-sonnet", None)])
    counts_fig = mi_page._comparison_counts_chart(workspace)
    assert list(counts_fig.data[0].x) == list(mi_page.comparison_counts(workspace).keys())
    assert list(counts_fig.data[0].y) == list(mi_page.comparison_counts(workspace).values())
    severity_fig = mi_page._comparison_grouped_chart(
        mi_page.comparison_severity_matrix(workspace), mi_page._SEVERITY_ORDER, None, "t")
    assert {trace.name for trace in severity_fig.data} == {"low", "medium", "high", "critical"}
    verification_fig = mi_page._comparison_grouped_chart(
        mi_page.comparison_verification_matrix(workspace), mi_page._VERIFICATION_ORDER, None, "t")
    assert len(verification_fig.data) == 6


def test_triage_title_rendering_and_reassessment_still_work(repository):
    from sentinel.ai.triage_service import AITriageService, DemoTriageProvider
    incident = repository.create_incident(CreateIncident(
        title=_DEMO_TITLE, description="Readable-title triage check.",
        category=IncidentCategory.HALLUCINATION_MISINFORMATION))
    assert "\\[" not in escape_html(incident.title)
    triage = AITriageService(repository, DemoTriageProvider())
    triage.assess_incident(incident.incident_id)
    triage.assess_incident(incident.incident_id)
    assert len(repository.list_ai_assessments(incident.incident_id)) == 2
    assert repository.get_incident(incident.incident_id).title == _DEMO_TITLE

