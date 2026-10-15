"""AI Model Observatory tests: leaderboard, drill-down, comparison, synthetic data."""
from datetime import date

import pytest

from sentinel.demo_seed import seed_demo_dataset
from sentinel.domain.enums import IncidentCategory, IncidentStatus, VerificationStatus
from sentinel.schemas.incident import CreateIncident
from sentinel.services.incident_service import IncidentService
from sentinel.services.model_intelligence_service import ModelIntelligenceService
from sentinel.services.report_service import ReportService
from sentinel.ui.pages.model_intelligence import (
    _comparison_counts_chart,
    _comparison_grouped_chart,
    comparison_category_matrix,
    comparison_counts,
    comparison_severity_matrix,
    comparison_verification_matrix,
)


def _payload(title, **overrides):
    base = dict(title=title, description="Detailed description for observatory tests.",
                category=IncidentCategory.HARMFUL_OUTPUT)
    base.update(overrides)
    return CreateIncident(**base)


@pytest.fixture()
def seeded(repository):
    result = seed_demo_dataset(repository)
    return repository, result


def test_seed_is_reproducible_and_idempotent(repository):
    first = seed_demo_dataset(repository)
    assert first.created == 160
    assert first.skipped == 0
    assert first.migrated == 0
    second = seed_demo_dataset(repository)
    assert second.created == 0
    assert second.skipped == 160
    assert second.migrated == 0
    _, total = repository.search_incidents(limit=1)
    assert total == 160


def test_seed_marks_all_records_synthetic(repository):
    seed_demo_dataset(repository)
    _, total = repository.search_incidents(is_demo=True, limit=1)
    assert total == 160
    for offset in range(0, total, 100):
        incidents, _ = repository.search_incidents(is_demo=True, limit=100, offset=offset)
        assert all(item.is_demo for item in incidents)
        assert all(item.title.startswith("[DEMO]") for item in incidents)
        assert all("SYNTHETIC DEMO RECORD" in item.description for item in incidents)


def test_seed_reset_preserves_genuine_records(repository):
    genuine = repository.create_incident(_payload("Genuine report", provider="RealCo"))
    seed_demo_dataset(repository)
    removed = repository.reset_demo_incidents()
    assert removed == 160
    assert repository.get_incident(genuine.incident_id).title == "Genuine report"
    assert len(repository.list_incidents()) == 1


def test_overview_metrics_from_seeded_data(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    metrics = service.overview_metrics()
    assert metrics["total"] == 160
    assert metrics["demo_records"] == 160
    assert metrics["genuine_records"] == 0
    assert metrics["distinct_models"] == 15  # 14 named models + Unknown (leaderboard groups versions)
    assert metrics["distinct_providers"] == 8  # 7 named providers + Unknown
    assert metrics["distinct_versions"] == 19  # 18 known versions + Unknown
    assert metrics["verified"] > 0
    assert metrics["high_critical"] > 0


def test_dataset_separation_demo_vs_genuine(repository):
    repository.create_incident(_payload("Genuine", provider="RealCo", affected_model_name="real-1"))
    seed_demo_dataset(repository)
    service = ModelIntelligenceService(repository)
    assert service.overview_metrics(dataset="demo")["total"] == 160
    assert service.overview_metrics(dataset="genuine")["total"] == 1
    assert service.overview_metrics(dataset="all")["total"] == 161
    assert service.overview_metrics(dataset="genuine")["distinct_providers"] == 1


def test_leaderboard_aggregation_and_sorting(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    most = service.leaderboard(sort_by="most_reported")
    fewest = service.leaderboard(sort_by="fewest_reported")
    assert most[0].total >= most[-1].total
    assert fewest[0].total <= fewest[-1].total
    by_verified = service.leaderboard(sort_by="most_verified")
    assert by_verified[0].verified >= by_verified[-1].verified
    by_severity = service.leaderboard(sort_by="most_high_critical")
    assert by_severity[0].high_critical >= by_severity[-1].high_critical
    by_model = service.leaderboard(sort_by="model")
    names = [row.affected_model_name.lower() for row in by_model]
    assert names == sorted(names)
    assert sum(row.total for row in most) == 160
    gpt4o = next(row for row in most if row.affected_model_name == "gpt-4o")
    assert gpt4o.verification_rate == pytest.approx(round(gpt4o.verified / gpt4o.total, 4))


def test_no_fabricated_usage_fields(seeded):
    repository, _ = seeded
    row = ModelIntelligenceService(repository).leaderboard()[0]
    forbidden = {"usage", "failure_rate", "safety_score", "confidence_interval"}
    assert not forbidden & set(row.__dataclass_fields__)


def test_exact_model_version_grouping_not_merged(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    detail = service.model_detail("OpenAI", "gpt-4o")
    version_names = {version.affected_model_version for version in detail.versions}
    assert version_names == {"2024-05-13", "2024-08-06"}
    assert sum(version.total for version in detail.versions) == detail.total == 22
    llama = service.model_detail("Meta", "llama-3.1-70b-instruct")
    assert [version.affected_model_version for version in llama.versions] == ["Unknown"]


def test_unknown_provider_and_model_grouping(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    rows = service.leaderboard()
    unknown = next(row for row in rows if row.provider == "Unknown")
    assert unknown.affected_model_name == "Unknown"
    assert unknown.version_label == "Unknown"
    assert unknown.total == 7


def test_comparison_between_models(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    workspace = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ])
    assert len(workspace.selected) == 2
    gpt = next(item for item in workspace.selected if item.affected_model_version.startswith("gpt-4o"))
    claude = next(item for item in workspace.selected if item.affected_model_version.startswith("claude"))
    assert gpt.total == 22
    assert claude.total == 18
    assert workspace.sufficient is True


def test_filters_and_reporting_periods(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    assert service.overview_metrics()["total"] == 160
    assert service.overview_metrics(date_from=date(2026, 11, 1))["total"] == 0
    assert service.overview_metrics(date_from=date(2026, 8, 15), date_to=date(2026, 10, 15))["total"] == 160
    assert service.overview_metrics(date_from=date(2026, 9, 1), date_to=date(2026, 9, 30))["total"] > 0
    verified = service.overview_metrics(verification_status="verified")
    assert verified["total"] == service.overview_metrics()["verified"]
    disputed = service.summary(verification_status="disputed")
    assert disputed["verification_status"] == {"disputed": service.overview_metrics()["disputed"]}
    by_severity = service.summary(severity="critical")
    assert sum(by_severity["severity"].values()) == by_severity["total"]


def test_insufficient_data_below_threshold(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository, min_sample=500)
    comparison = service.compare()
    assert comparison.sufficient_data is False
    assert "Insufficient data" in comparison.note
    assert all(not row.sufficient for row in service.leaderboard())
    assert service.overview_metrics()["total"] == 160
    # A threshold the dataset satisfies still reports sufficient data.
    assert ModelIntelligenceService(repository, min_sample=5).compare().sufficient_data is True


def test_empty_dataset(repository):
    service = ModelIntelligenceService(repository)
    metrics = service.overview_metrics()
    assert metrics["total"] == 0
    assert metrics["distinct_providers"] == 0
    assert service.leaderboard() == []
    assert service.compare().sufficient_data is False


def test_verified_disputed_unverified_breakdowns(seeded):
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    verification = service.summary()["verification_status"]
    assert set(verification) <= {"reported", "ai_assessed", "human_reviewed", "verified", "disputed", "unverified"}
    assert sum(verification.values()) == 160
    assert len(verification) == 6  # all lifecycle states represented
    rows = service.leaderboard()
    assert sum(row.verified for row in rows) == verification.get("verified", 0)
    assert sum(row.disputed for row in rows) == verification.get("disputed", 0)


def test_seeded_records_have_audit_and_assessment_history(seeded):
    repository, _ = seeded
    first = repository.search_incidents(is_demo=True, limit=1)[0][0]
    events = repository.list_audit_events(first.incident_id)
    assert events[0].event_type == "incident_created"
    assessed = next(item for item in repository.search_incidents(is_demo=True, limit=200)[0]
                    if item.verification_status != VerificationStatus.REPORTED)
    assessments = repository.list_ai_assessments(assessed.incident_id)
    assert assessments and assessments[0].provider_mode == "demo"
    assert assessments[0].model_name == "sentinel-deterministic-demo-v1"


def test_export_labels_synthetic_records(seeded):
    repository, _ = seeded
    service = ReportService(repository)
    incident = repository.search_incidents(is_demo=True, limit=1)[0][0]
    assert "SYNTHETIC DEMO DATA" in service.markdown(incident.incident_id)
    genuine = repository.create_incident(_payload("Genuine for export"))
    assert "SYNTHETIC DEMO DATA" not in service.markdown(genuine.incident_id)


def test_incident_workflows_still_work_after_seeding(seeded):
    repository, _ = seeded
    service = IncidentService(repository)
    incident = repository.create_incident(_payload("Workflow check"))
    service.transition(incident.incident_id, IncidentStatus.UNDER_REVIEW)
    updated = repository.get_incident(incident.incident_id)
    assert updated.status.value == "under_review"
    assert updated.verification_status == VerificationStatus.REPORTED
    with pytest.raises(ValueError, match="Cannot transition verification"):
        repository.transition_verification(incident.incident_id, VerificationStatus.VERIFIED)


def test_dataset_separation_after_seeding_genuine_first(repository):
    genuine = repository.create_incident(_payload("Real one", provider="RealCo"))
    seed_demo_dataset(repository)
    service = ModelIntelligenceService(repository)
    genuine_rows = service.leaderboard(dataset="genuine")
    assert len(genuine_rows) == 1
    assert genuine_rows[0].provider == "RealCo"
    assert len(service.leaderboard(dataset="all")) == len(genuine_rows) + 15
    assert repository.get_incident(genuine.incident_id).is_demo is False


def test_synthetic_dataset_range_diversity_and_lifecycle(seeded):
    repository, _ = seeded
    incidents, total = repository.search_incidents(is_demo=True, limit=500)
    assert total == 160
    dates = [item.report_date for item in incidents]
    assert min(dates) >= date(2026, 8, 15)
    assert max(dates) <= date(2026, 10, 15)
    assert len({item.category for item in incidents}) >= 7
    assert len({item.severity for item in incidents}) == 4
    assert {item.verification_status for item in incidents} == set(VerificationStatus)
    assert {item.status for item in incidents} == set(IncidentStatus)
    providers = {(item.provider or "Unknown") for item in incidents}
    assert len(providers) >= 7
    models = {(item.provider or "Unknown", item.affected_model_name or "Unknown",
               item.affected_model_version or "Unknown") for item in incidents}
    assert len(models) >= 15
    # Search, pagination, sorting still work over the large demo set.
    page1, total1 = repository.search_incidents(is_demo=True, limit=25, offset=0, sort_by="report_date")
    page2, _ = repository.search_incidents(is_demo=True, limit=25, offset=25, sort_by="report_date")
    assert total1 == 160
    assert {item.incident_id for item in page1}.isdisjoint({item.incident_id for item in page2})
    found, _ = repository.search_incidents(query="SYN-042", limit=10)
    assert found and all("SYN-042" in item.title for item in found)


def test_seed_migrates_legacy_demo_records(repository):
    legacy = repository.create_incident(_payload("Legacy demo row", provider="OldCo"))
    from sentinel.database.connection import database_connection
    with database_connection(repository.database_path) as connection:
        connection.execute("UPDATE incidents SET is_demo = 1, title = '[DEMO] legacy row', "
                           "report_date = '2026-01-05', occurrence_date = '2026-01-04' "
                           "WHERE incident_id = ?", (legacy.incident_id,))
    genuine = repository.create_incident(_payload("Genuine stays"))
    result = seed_demo_dataset(repository)
    assert result.migrated >= 1
    assert result.created + result.migrated == 160
    second = seed_demo_dataset(repository)
    assert (second.created, second.migrated) == (0, 0)
    assert second.skipped == 160
    assert repository.get_incident(genuine.incident_id).title == "Genuine stays"
    _, total = repository.search_incidents(is_demo=True, limit=1)
    assert total == 160
    demo, _ = repository.search_incidents(is_demo=True, limit=500)
    assert all(date(2026, 8, 15) <= item.report_date <= date(2026, 10, 15) for item in demo)


def test_comparison_counts_chart_from_service_data(seeded):
    """Chart data matches service comparison counts."""
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    workspace = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ])
    counts = comparison_counts(workspace)
    assert counts["gpt-4o · all versions"] == 22
    assert counts["claude-3-5-sonnet · all versions"] == 18
    fig = _comparison_counts_chart(workspace)
    assert fig.data[0].type == "bar"
    assert list(fig.data[0].x) == list(counts.keys())
    assert list(fig.data[0].y) == list(counts.values())


def test_comparison_severity_matrix_chart(seeded):
    """Severity chart reflects actual severity distribution per model."""
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    workspace = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ])
    matrix = comparison_severity_matrix(workspace)
    for model in matrix:
        assert set(matrix[model].keys()) == {"low", "medium", "high", "critical"}
        assert all(isinstance(v, int) for v in matrix[model].values())
    fig = _comparison_grouped_chart(matrix, ("low", "medium", "high", "critical"),
                                    {"low": "#34D399", "medium": "#FBBF24", "high": "#F87171", "critical": "#FB7185"},
                                    "Severity distribution by model")
    assert fig.data[0].type == "bar"
    assert len(fig.data) == 4  # four severity levels
    assert fig.layout.barmode == "group"


def test_comparison_verification_matrix_chart(seeded):
    """Verification chart reflects actual verification distribution per model."""
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    workspace = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ])
    matrix = comparison_verification_matrix(workspace)
    expected_states = ("reported", "ai_assessed", "human_reviewed", "verified", "disputed", "unverified")
    for model in matrix:
        assert set(matrix[model].keys()) == set(expected_states)
        assert all(isinstance(v, int) for v in matrix[model].values())
    fig = _comparison_grouped_chart(matrix, expected_states, None, "Verification distribution by model")
    assert len(fig.data) == 6  # six verification states
    assert fig.layout.barmode == "group"


def test_comparison_category_matrix_chart(seeded):
    """Category chart reflects actual category distribution per model."""
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    workspace = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ])
    matrix = comparison_category_matrix(workspace)
    categories = sorted({name for row in matrix.values() for name in row})
    assert len(categories) >= 2
    for model in matrix:
        assert all(isinstance(v, int) for v in matrix[model].values())
    fig = _comparison_grouped_chart(matrix, tuple(categories), None, "Category breakdown by model")
    assert len(fig.data) == len(categories)
    assert fig.layout.barmode == "group"


def test_comparison_charts_respect_filters(seeded):
    """Charts update when filters change (verified status filter)."""
    repository, _ = seeded
    service = ModelIntelligenceService(repository)
    # All data
    workspace_all = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ])
    counts_all = comparison_counts(workspace_all)
    # Only verified
    workspace_verified = service.compare_models([
        ("OpenAI", "gpt-4o", None),
        ("Anthropic", "claude-3-5-sonnet", None),
    ], verification_status="verified")
    counts_verified = comparison_counts(workspace_verified)
    # Verified counts should be <= all counts
    for model in counts_verified:
        assert counts_verified[model] <= counts_all.get(model, 0)
    # Chart data reflects filtered counts
    fig = _comparison_counts_chart(workspace_verified)
    assert list(fig.data[0].y) == list(counts_verified.values())


def test_comparison_charts_handle_insufficient_data(seeded):
    """Charts render correctly even when one model has insufficient data."""
    repository, _ = seeded
    service = ModelIntelligenceService(repository, min_sample=50)
    workspace = service.compare_models([
        ("OpenAI", "gpt-4o", None),  # 22 reports < 50
        ("Anthropic", "claude-3-5-sonnet", None),  # 18 reports < 50
    ])
    assert workspace.sufficient is False
    # Charts should still render with actual counts
    counts = comparison_counts(workspace)
    assert counts["gpt-4o · all versions"] == 22
    assert counts["claude-3-5-sonnet · all versions"] == 18
    fig = _comparison_counts_chart(workspace)
    assert list(fig.data[0].y) == [22, 18]


def test_comparison_charts_empty_results(repository):
    """Charts handle empty comparison gracefully."""
    service = ModelIntelligenceService(repository)
    workspace = service.compare_models([
        ("NonExistent", "model", None),
    ])
    counts = comparison_counts(workspace)
    assert counts == {"model · all versions": 0}
    fig = _comparison_counts_chart(workspace)
    assert list(fig.data[0].y) == [0]


