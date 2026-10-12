from datetime import date

import pytest
from pydantic import ValidationError

from sentinel.domain.enums import IncidentCategory, Severity, SeveritySource
from sentinel.schemas.incident import CreateIncident


def test_incident_requires_complete_severity_source_pair() -> None:
    with pytest.raises(ValidationError, match="Severity and severity source"):
        CreateIncident(title="Unsafe response", description="A detailed description", category=IncidentCategory.HARMFUL_OUTPUT,
                       severity=Severity.HIGH)


def test_anonymous_report_cannot_include_reporter_details() -> None:
    with pytest.raises(ValidationError, match="Anonymous"):
        CreateIncident(title="Privacy issue", description="A detailed description", category=IncidentCategory.PRIVACY,
                       anonymous_report=True, reporter_name="Reporter")


def test_occurrence_must_not_follow_report_date() -> None:
    with pytest.raises(ValidationError, match="Occurrence"):
        CreateIncident(title="Reliability issue", description="A detailed description", category=IncidentCategory.RELIABILITY,
                       occurrence_date=date(2026, 2, 2), report_date=date(2026, 2, 1))


def test_valid_incident_model() -> None:
    incident = CreateIncident(title="Biased ranking", description="Ranking disadvantage observed", category=IncidentCategory.DISCRIMINATION,
                              severity=Severity.MEDIUM, severity_source=SeveritySource.HUMAN)
    assert incident.severity == Severity.MEDIUM
