from datetime import date

from sentinel.domain.enums import IncidentCategory, IncidentStatus, Severity, SeveritySource
from sentinel.schemas.incident import CreateIncident
from sentinel.services import AnalyticsService, IncidentService


def test_submit_search_and_dashboard_metrics_share_persisted_records(repository) -> None:
    service = IncidentService(repository)
    first = service.submit(CreateIncident(
        title="Unsafe generated output", description="A user received an unsafe response.",
        category=IncidentCategory.HARMFUL_OUTPUT, severity=Severity.HIGH,
        severity_source=SeveritySource.HUMAN, report_date=date(2026, 1, 2),
    ))
    service.submit(CreateIncident(
        title="Model service outage", description="The service became unavailable for users.",
        category=IncidentCategory.RELIABILITY, report_date=date(2026, 1, 3),
    ))
    service.transition(first.incident_id, IncidentStatus.UNDER_REVIEW)

    matches, total = repository.search_incidents(query="unsafe")
    assert total == 1
    assert matches[0].incident_id == first.incident_id

    analytics = AnalyticsService(repository)
    incidents = analytics.filtered_incidents()
    metrics = analytics.metrics(incidents)
    assert metrics.total == 2
    assert metrics.open_incidents == 2
    assert metrics.high_critical == 1
    assert metrics.awaiting_review == 1
    assert analytics.distribution(incidents, "category") == {"harmful_unsafe_output": 1, "reliability_system_failure": 1}
