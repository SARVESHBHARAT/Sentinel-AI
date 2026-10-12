from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape
from io import BytesIO, StringIO
from typing import Iterable

from sentinel.database.repositories import IncidentRepository
from sentinel.schemas.incident import Incident
from sentinel.time_utils import display_local


def _label(value: object | None) -> str:
    if value is None:
        return "Unknown / not assessed"
    return getattr(value, "value", str(value)).replace("_", " ").title()


def _value(value: str | None) -> str:
    return value.strip() if value else "Unknown / not applicable"


class ReportService:
    """Point-in-time report renderers. User data is escaped before PDF rendering."""

    def __init__(self, repository: IncidentRepository) -> None:
        self._repository = repository

    def markdown(self, incident_id: str) -> str:
        incident = self._repository.get_incident(incident_id)
        assessments = self._repository.list_ai_assessments(incident_id)
        notes = self._repository.list_reviewer_notes(incident_id)
        actions = self._repository.list_corrective_actions(incident_id)
        evidence = self._repository.list_evidence_references(incident_id)
        events = self._repository.list_audit_events(incident_id)
        latest = assessments[-1] if assessments else None
        ai_category = _label(latest.suggested_category) if latest else "No assessment available"
        ai_severity = _label(latest.suggested_severity) if latest else "No assessment available"
        lines = [
            "# Sentinel AI Incident Report", "", f"**Incident ID:** {incident.incident_id}", f"**Title:** {incident.title}",
            f"**Generated (UTC):** {datetime.now(timezone.utc).isoformat()}", "**Snapshot notice:** This export is a point-in-time snapshot.", "",
            "## Executive summary", _value(latest.concise_summary if latest else None), "",
            "## Original report", f"**Description:** {_value(incident.description)}", f"**Reported:** {incident.report_date.isoformat()}",
            f"**Occurrence date:** {incident.occurrence_date.isoformat() if incident.occurrence_date else 'Unknown / not applicable'}", "",
            "## Affected AI system", f"**System:** {_value(incident.affected_system)}", f"**Provider:** {_value(incident.provider)}", "",
            "## Classification and severity", f"**AI suggestion:** Category — {ai_category}; Severity — {ai_severity}",
            f"**Human/current determination:** Category — {_label(incident.category)} ({_label(incident.category_source)}); Severity — {_label(incident.severity)} ({_label(incident.severity_source)})", "",
            "## Potential impact and stakeholders", _value(incident.potential_impact), f"**Affected stakeholders/population:** {_value(incident.affected_population)}", "",
            "## Supporting evidence", *([f"- {item}" for item in evidence] or ["- Unknown / not applicable"]), "",
            "## AI assessment and limitations",
        ]
        if latest:
            lines.extend([
                f"**Model:** {latest.model_name}; **Timestamp:** {latest.created_at.isoformat() if latest.created_at else 'Unknown'}; **Mode:** {latest.provider_mode}",
                f"**Observed concern:** {latest.observed_failure_or_concern}", f"**Severity explanation:** {latest.severity_explanation}",
                "**Missing information / limitations:**", *([f"- {item}" for item in latest.missing_information] or ["- Unknown / not applicable"]),
            ])
        else:
            lines.append("No assessment is available. Any reported findings remain unverified.")
        lines.extend(["", "## Investigation history"])
        lines.extend([f"- {display_local(event.created_at)} | {event.event_type} | {event.actor or 'System'} | {event.details or 'No details'}" for event in events] or ["- No investigation events recorded"])
        lines.extend(["", "## Reviewer notes"])
        lines.extend([f"- {note.author or 'Reviewer'}: {note.body}" for note in notes] or ["- No notes recorded"])
        lines.extend(["", "## Corrective and preventive actions"])
        lines.extend([f"- [{action.action_kind}] [{action.status}] {action.title} — {action.owner or 'Unassigned'}" for action in actions] or ["- No actions recorded"])
        lines.extend(["", "## Status and resolution", f"**Current status:** {_label(incident.status)}", f"**Resolution summary:** {_value(incident.resolution_summary)}"])
        return "\n".join(lines)

    def pdf(self, incident_id: str) -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        except ImportError as error:
            raise RuntimeError("PDF export is unavailable because ReportLab is not installed.") from error
        markdown = self.markdown(incident_id)
        buffer = BytesIO()
        styles = getSampleStyleSheet()
        body = ParagraphStyle("SentinelBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, spaceAfter=5)
        heading = ParagraphStyle("SentinelHeading", parent=styles["Heading2"], textColor=colors.HexColor("#102044"), spaceBefore=10, spaceAfter=5)
        story = []
        for line in markdown.splitlines():
            safe = escape(line).replace("\n", "<br/>")
            if line.startswith("# "):
                story.append(Paragraph(safe[2:], styles["Title"]))
            elif line.startswith("## "):
                story.append(Paragraph(safe[3:], heading))
            elif not line:
                story.append(Spacer(1, 4))
            else:
                story.append(Paragraph(safe, body))

        def page_number(canvas, document):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#5b6578"))
            canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Sentinel AI · Page {document.page}")
            canvas.restoreState()

        document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=f"Sentinel AI {incident_id}")
        document.build(story, onFirstPage=page_number, onLaterPages=page_number)
        return buffer.getvalue()

    @staticmethod
    def register_csv(incidents: Iterable[Incident]) -> str:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Incident ID", "Title", "Category", "Severity", "Status", "Report date", "Assigned reviewer"])
        for incident in incidents:
            writer.writerow([incident.incident_id, incident.title, _label(incident.category), _label(incident.severity), _label(incident.status), incident.report_date.isoformat(), incident.assigned_reviewer or ""])
        return output.getvalue()
