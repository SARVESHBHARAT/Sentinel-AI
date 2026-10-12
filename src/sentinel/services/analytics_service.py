from collections import Counter
from dataclasses import dataclass
from datetime import date

from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentStatus, Severity
from sentinel.schemas.incident import Incident


@dataclass(frozen=True, slots=True)
class DashboardMetrics:
    total: int
    open_incidents: int
    high_critical: int
    awaiting_review: int


class AnalyticsService:
    def __init__(self, repository: IncidentRepository) -> None:
        self._repository = repository

    def filtered_incidents(
        self, *, category: str | None = None, date_from: date | None = None, date_to: date | None = None
    ) -> list[Incident]:
        return self._repository.all_matching_incidents(category=category, date_from=date_from, date_to=date_to)

    @staticmethod
    def metrics(incidents: list[Incident]) -> DashboardMetrics:
        open_statuses = {IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW, IncidentStatus.ACTION_REQUIRED}
        return DashboardMetrics(
            total=len(incidents),
            open_incidents=sum(item.status in open_statuses for item in incidents),
            high_critical=sum(item.severity in {Severity.HIGH, Severity.CRITICAL} for item in incidents),
            awaiting_review=sum(item.status == IncidentStatus.SUBMITTED for item in incidents),
        )

    @staticmethod
    def distribution(incidents: list[Incident], field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(getattr(item, field).value if getattr(item, field) else "Not assessed") for item in incidents).items()))

    @staticmethod
    def trend(incidents: list[Incident]) -> dict[str, int]:
        return dict(sorted(Counter(item.report_date.isoformat() for item in incidents).items()))
