"""Model-intelligence aggregation over real incident records.

Reports describe *reported* events; this service never claims a model is
objectively less safe because it has more reports, never computes
usage-adjusted failure rates (no usage denominators exist), and never treats
an AI assessment as independent verification. Comparisons below the
minimum-data threshold return an explicit insufficient-data state.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import Severity
from sentinel.schemas.incident import Incident


UNKNOWN = "Unknown"

COMPARISON_FORMULA = (
    "share_of_matching_reports = group_count / total_matching_reports; "
    "reported only, no usage denominator, no safety score."
)


def _provider_key(incident: Incident) -> str:
    return (incident.provider or "").strip() or UNKNOWN


def _model_key(incident: Incident) -> str:
    return (incident.affected_model_name or "").strip() or UNKNOWN


def _version_key(incident: Incident) -> str:
    return (incident.affected_model_version or "").strip() or UNKNOWN


@dataclass(frozen=True, slots=True)
class ModelGroup:
    provider: str
    affected_model_name: str
    affected_model_version: str
    total: int
    severity: dict[str, int] = field(default_factory=dict)
    category: dict[str, int] = field(default_factory=dict)
    verification_status: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelComparison:
    groups: tuple[ModelGroup, ...]
    total_matching_reports: int
    min_sample: int
    sufficient_data: bool
    note: str
    formula: str = COMPARISON_FORMULA


@dataclass(frozen=True, slots=True)
class LeaderboardRow:
    """One exact-model row. Counts are reported incidents only — never safety scores."""

    provider: str
    affected_model_name: str
    version_label: str
    total: int
    verified: int
    disputed: int
    high_critical: int
    verification_rate: float | None
    most_common_category: str
    most_recent_report: str
    sufficient: bool


@dataclass(frozen=True, slots=True)
class VersionRow:
    """Per-version (or per-comparison-target) statistics block."""

    affected_model_version: str
    total: int
    verified: int
    high_critical: int
    severity: dict[str, int] = field(default_factory=dict)
    category: dict[str, int] = field(default_factory=dict)
    verification_status: dict[str, int] = field(default_factory=dict)
    trend: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelDetail:
    provider: str
    affected_model_name: str
    versions: tuple[VersionRow, ...]
    recent_incidents: tuple[Incident, ...]
    total: int
    sufficient: bool


@dataclass(frozen=True, slots=True)
class ComparisonWorkspace:
    selected: tuple[VersionRow, ...]
    sufficient: bool


class ModelIntelligenceService:
    """Aggregate incidents by provider / affected model / affected version."""

    def __init__(self, repository: IncidentRepository, min_sample: int = 5) -> None:
        self._repository = repository
        self._min_sample = max(1, min_sample)

    def _filtered(self, *, date_from: date | None = None, date_to: date | None = None,
                  category: str | None = None, verification_status: str | None = None,
                  severity: str | None = None, dataset: str | None = None) -> list[Incident]:
        is_demo = {"demo": True, "genuine": False}.get(dataset or "all")
        _, total = self._repository.search_incidents(
            category=category, verification_status=verification_status, severity=severity,
            date_from=date_from, date_to=date_to, is_demo=is_demo, limit=1)
        results: list[Incident] = []
        for offset in range(0, total, 500):
            batch, _ = self._repository.search_incidents(
                category=category, verification_status=verification_status, severity=severity,
                date_from=date_from, date_to=date_to, is_demo=is_demo, limit=500, offset=offset)
            results.extend(batch)
        return results

    @staticmethod
    def _distributions(incidents: list[Incident]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
        severity = dict(sorted(Counter(item.severity.value if item.severity else "Not assessed" for item in incidents).items()))
        category = dict(sorted(Counter(item.category.value for item in incidents).items()))
        verification = dict(sorted(Counter(item.verification_status.value for item in incidents).items()))
        return severity, category, verification

    def summary(self, *, date_from: date | None = None, date_to: date | None = None,
                category: str | None = None, verification_status: str | None = None,
                severity: str | None = None, dataset: str | None = None) -> dict[str, object]:
        incidents = self._filtered(date_from=date_from, date_to=date_to, category=category,
                                   verification_status=verification_status, severity=severity, dataset=dataset)
        severity, categories, verification = self._distributions(incidents)
        return {"total": len(incidents), "severity": severity, "category": categories,
                "verification_status": verification}

    def groups(self, *, date_from: date | None = None, date_to: date | None = None,
               category: str | None = None, verification_status: str | None = None,
               severity: str | None = None, dataset: str | None = None) -> list[ModelGroup]:
        incidents = self._filtered(date_from=date_from, date_to=date_to, category=category,
                                   verification_status=verification_status, severity=severity, dataset=dataset)
        buckets: dict[tuple[str, str, str], list[Incident]] = {}
        for incident in incidents:
            buckets.setdefault((_provider_key(incident), _model_key(incident), _version_key(incident)), []).append(incident)
        ordered: list[ModelGroup] = []
        for (provider, model, version) in sorted(buckets):
            members = buckets[(provider, model, version)]
            severity, categories, verification = self._distributions(members)
            ordered.append(ModelGroup(provider=provider, affected_model_name=model, affected_model_version=version,
                                      total=len(members), severity=severity, category=categories,
                                      verification_status=verification))
        return ordered

    def compare(self, *, date_from: date | None = None, date_to: date | None = None,
                category: str | None = None, verification_status: str | None = None,
                severity: str | None = None, dataset: str | None = None) -> ModelComparison:
        matching = self._filtered(date_from=date_from, date_to=date_to, category=category,
                                  verification_status=verification_status, severity=severity, dataset=dataset)
        grouped = self.groups(date_from=date_from, date_to=date_to, category=category,
                              verification_status=verification_status, severity=severity, dataset=dataset)
        sufficient = len(matching) >= self._min_sample and len(grouped) > 0
        if not sufficient:
            note = (f"Insufficient data for comparison: {len(matching)} matching report(s), "
                    f"minimum required is {self._min_sample}. Counts are reported without ranking.")
        else:
            note = ("Transparent share of matching reports per provider/model/version. "
                    "More reports do not prove a model is less safe; usage is unknown and "
                    "verification status must be checked per incident.")
        return ModelComparison(groups=tuple(grouped), total_matching_reports=len(matching),
                               min_sample=self._min_sample, sufficient_data=sufficient, note=note)

    # ------------------------------------------------------------------
    # Observatory: overview, leaderboard, model detail, comparison
    # ------------------------------------------------------------------
    def overview_metrics(self, **filters) -> dict[str, object]:
        """Dataset-level metrics for the selected filters and dataset scope."""
        incidents = self._filtered(**filters)
        demo_count = sum(1 for item in incidents if item.is_demo)
        genuine_count = len(incidents) - demo_count
        return {
            "total": len(incidents),
            "distinct_providers": len({_provider_key(item) for item in incidents}),
            "distinct_models": len({(_provider_key(item), _model_key(item)) for item in incidents}),
            "distinct_versions": len({(_provider_key(item), _model_key(item), _version_key(item)) for item in incidents}),
            "verified": sum(item.verification_status.value == "verified" for item in incidents),
            "disputed": sum(item.verification_status.value == "disputed" for item in incidents),
            "high_critical": sum(item.severity in (Severity.HIGH, Severity.CRITICAL) for item in incidents),
            "demo_records": demo_count,
            "genuine_records": genuine_count,
        }

    def leaderboard(self, *, sort_by: str = "most_reported", **filters) -> list["LeaderboardRow"]:
        """Rank exact model identifiers by a clearly named report metric.

        Rankings measure counts of *reported* incidents only; they never imply
        relative safety (see module docstring for interpretation rules).
        """
        incidents = self._filtered(**filters)
        buckets: dict[tuple[str, str], list[Incident]] = {}
        for incident in incidents:
            buckets.setdefault((_provider_key(incident), _model_key(incident)), []).append(incident)
        rows: list[LeaderboardRow] = []
        for (provider, model), members in buckets.items():
            severity, category, verification = self._distributions(members)
            verified = sum(item.verification_status.value == "verified" for item in members)
            disputed = sum(item.verification_status.value == "disputed" for item in members)
            high_critical = sum(item.severity in (Severity.HIGH, Severity.CRITICAL) for item in members)
            known_versions = sorted({item.affected_model_version.strip() for item in members
                                     if item.affected_model_version and item.affected_model_version.strip()})
            version_label = ", ".join(known_versions) if known_versions else "Unknown"
            top_category = max(category.items(), key=lambda kv: kv[1])[0] if category else "No data"
            most_recent = max(item.report_date for item in members).isoformat()
            total = len(members)
            rate = round(verified / total, 4) if total else None
            rows.append(LeaderboardRow(
                provider=provider, affected_model_name=model, version_label=version_label,
                total=total, verified=verified, disputed=disputed, high_critical=high_critical,
                verification_rate=rate, most_common_category=top_category,
                most_recent_report=most_recent,
                sufficient=total >= self._min_sample,
            ))
        sorters = {
            "most_reported": lambda row: (-row.total, row.provider, row.affected_model_name),
            "fewest_reported": lambda row: (row.total, row.provider, row.affected_model_name),
            "most_verified": lambda row: (-row.verified, row.provider, row.affected_model_name),
            "most_high_critical": lambda row: (-row.high_critical, row.provider, row.affected_model_name),
            "model": lambda row: (row.affected_model_name.lower(), row.provider),
            "provider": lambda row: (row.provider.lower(), row.affected_model_name),
        }
        return sorted(rows, key=sorters.get(sort_by, sorters["most_reported"]))

    def model_detail(self, provider: str, model: str, **filters) -> "ModelDetail":
        """Per-version breakdown for one exact model identifier (versions never merged)."""
        incidents = self._filtered(**filters)
        members = [item for item in incidents if _provider_key(item) == provider and _model_key(item) == model]
        by_version: dict[str, list[Incident]] = {}
        for incident in members:
            by_version.setdefault(_version_key(incident), []).append(incident)
        versions: list[VersionRow] = []
        for version in sorted(by_version):
            group = by_version[version]
            severity, category, verification = self._distributions(group)
            verified = sum(item.verification_status.value == "verified" for item in group)
            versions.append(VersionRow(
                affected_model_version=version, total=len(group), verified=verified,
                high_critical=sum(item.severity in (Severity.HIGH, Severity.CRITICAL) for item in group),
                severity=severity, category=category, verification_status=verification,
                trend=dict(sorted(Counter(item.report_date.isoformat() for item in group).items())),
            ))
        recent = sorted(members, key=lambda item: item.report_date, reverse=True)[:10]
        return ModelDetail(provider=provider, affected_model_name=model,
                           versions=tuple(versions), recent_incidents=tuple(recent),
                           total=len(members), sufficient=len(members) >= self._min_sample)

    def compare_models(self, targets: list[tuple[str, str, str | None]], **filters) -> "ComparisonWorkspace":
        """Side-by-side statistics for two or more exact model/version targets.

        ``targets`` items are (provider, model, version); ``version=None`` means
        all versions of that model.
        """
        selected: list[VersionRow] = []
        for provider, model, version in targets:
            incidents = [item for item in self._filtered(**filters)
                         if _provider_key(item) == provider and _model_key(item) == model
                         and (version is None or _version_key(item) == version)]
            severity, category, verification = self._distributions(incidents)
            verified = sum(item.verification_status.value == "verified" for item in incidents)
            selected.append(VersionRow(
                affected_model_version=f"{model} · {version or 'all versions'}",
                total=len(incidents), verified=verified,
                high_critical=sum(item.severity in (Severity.HIGH, Severity.CRITICAL) for item in incidents),
                severity=severity, category=category, verification_status=verification,
                trend=dict(sorted(Counter(item.report_date.isoformat() for item in incidents).items())),
            ))
        return ComparisonWorkspace(selected=tuple(selected),
                                   sufficient=len(selected) >= 1 and all(item.total >= self._min_sample
                                                                          for item in selected))



