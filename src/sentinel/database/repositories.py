from datetime import date, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from sentinel.database.connection import database_connection
from sentinel.database.schema import initialize_schema
from sentinel.domain.enums import CategorySource, IncidentCategory, IncidentStatus
from sentinel.domain.lifecycle import validate_transition
from sentinel.schemas.incident import (
    AIAssessment,
    AuditEvent,
    CorrectiveAction,
    CreateIncident,
    Incident,
    IncidentUpdate,
    ReviewerNote,
)
from sentinel.time_utils import utc_iso


ALLOWED_UPDATE_COLUMNS: frozenset[str] = frozenset({
    "title",
    "description",
    "category",
    "category_source",
    "affected_system",
    "provider",
    "occurrence_date",
    "report_date",
    "severity",
    "severity_source",
    "potential_impact",
    "affected_population",
    "assigned_reviewer",
    "resolution_summary",
})


class IncidentNotFoundError(LookupError):
    pass


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _incident_from_row(row: sqlite3.Row) -> Incident:
    return Incident(
        incident_id=row["incident_id"], title=row["title"], description=row["description"],
        category=_category(row["category"]), category_source=row["category_source"], affected_system=row["affected_system"], provider=row["provider"],
        occurrence_date=_date(row["occurrence_date"]), report_date=date.fromisoformat(row["report_date"]),
        severity=row["severity"], severity_source=row["severity_source"],
        potential_impact=row["potential_impact"], affected_population=row["affected_population"],
        anonymous_report=bool(row["anonymous_report"]), assigned_reviewer=row["assigned_reviewer"], resolution_summary=row["resolution_summary"],
        status=row["status"], is_demo=bool(row["is_demo"]), created_at=_dt(row["created_at"]), updated_at=_dt(row["updated_at"]),
    )


def _category(value: str) -> IncidentCategory:
    legacy = {"harmful_output": "harmful_unsafe_output", "privacy": "privacy_data_leakage", "discrimination": "bias_discrimination", "security": "security_vulnerability_abuse", "reliability": "reliability_system_failure", "governance": "other_unclassified", "other": "other_unclassified"}
    return IncidentCategory(legacy.get(value, value))


class IncidentRepository:
    """SQLite persistence boundary for the Sentinel application."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        with database_connection(self.database_path) as connection:
            initialize_schema(connection)

    @staticmethod
    def _next_id(connection: sqlite3.Connection, year: int) -> str:
        row = connection.execute(
            "SELECT last_value FROM incident_sequences WHERE year = ?", (year,)
        ).fetchone()
        if row is None:
            value = 1
            connection.execute(
                "INSERT INTO incident_sequences(year, last_value) VALUES (?, ?)", (year, value)
            )
        else:
            value = int(row["last_value"]) + 1
            connection.execute(
                "UPDATE incident_sequences SET last_value = ? WHERE year = ?", (value, year)
            )
        return f"INC-{year}-{value:04d}"

    @staticmethod
    def _add_event(
        connection: sqlite3.Connection, incident_id: str, event_type: str, actor: str | None,
        details: str | None, now: str,
    ) -> None:
        connection.execute(
            "INSERT INTO audit_events(incident_id, event_type, actor, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (incident_id, event_type, actor, details, now),
        )

    def create_incident(
        self, payload: CreateIncident, actor: str | None = None, *, is_demo: bool = False
    ) -> Incident:
        now = utc_iso()
        with database_connection(self.database_path) as connection:
            # IMMEDIATE makes sequence allocation safe between concurrent SQLite writers.
            connection.execute("BEGIN IMMEDIATE")
            incident_id = self._next_id(connection, datetime.fromisoformat(now).year)
            connection.execute(
                """INSERT INTO incidents (
                    incident_id, title, description, category, category_source, affected_system, provider, occurrence_date,
                    report_date, severity, severity_source, potential_impact, affected_population,
                    reporter_name, reporter_contact, anonymous_report, assigned_reviewer, resolution_summary, status, is_demo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (incident_id, payload.title, payload.description, payload.category.value, CategorySource.REPORTER.value, payload.affected_system,
                 payload.provider, payload.occurrence_date.isoformat() if payload.occurrence_date else None,
                 payload.report_date.isoformat(), payload.severity.value if payload.severity else None,
                 payload.severity_source.value if payload.severity_source else None, payload.potential_impact,
                 payload.affected_population, payload.reporter_name, payload.reporter_contact,
                 int(payload.anonymous_report), payload.assigned_reviewer, None, IncidentStatus.SUBMITTED.value, int(is_demo), now, now),
            )
            connection.executemany(
                "INSERT INTO evidence_references(incident_id, reference) VALUES (?, ?)",
                [(incident_id, reference) for reference in payload.evidence_references],
            )
            self._add_event(connection, incident_id, "incident_created", actor, "Incident submitted", now)
        return self.get_incident(incident_id)

    def get_incident(self, incident_id: str) -> Incident:
        with database_connection(self.database_path) as connection:
            row = connection.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
        if row is None:
            raise IncidentNotFoundError(f"Incident {incident_id} was not found")
        return _incident_from_row(row)

    def list_incidents(
        self, *, status: IncidentStatus | None = None, category: str | None = None,
        assigned_reviewer: str | None = None, limit: int = 100, offset: int = 0,
    ) -> list[Incident]:
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("limit must be between 1 and 500 and offset cannot be negative")
        clauses: list[str] = []
        values: list[Any] = []
        if status:
            clauses.append("status = ?")
            values.append(status.value)
        if category:
            clauses.append("category = ?")
            values.append(category)
        if assigned_reviewer:
            clauses.append("assigned_reviewer = ?")
            values.append(assigned_reviewer)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM incidents{where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        with database_connection(self.database_path) as connection:
            rows = connection.execute(query, (*values, limit, offset)).fetchall()
        return [_incident_from_row(row) for row in rows]

    def search_incidents(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str = "created_at",
        descending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Incident], int]:
        """Search safely using a fixed set of sortable database columns."""
        if sort_by not in {"created_at", "updated_at", "report_date", "title", "severity", "status"}:
            raise ValueError("Unsupported incident sort field")
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("limit must be between 1 and 500 and offset cannot be negative")
        clauses: list[str] = []
        values: list[Any] = []
        if query:
            clauses.append("(incident_id LIKE ? OR title LIKE ?)")
            term = f"%{query.strip()}%"
            values.extend((term, term))
        for column, value in (("category", category), ("severity", severity), ("status", status)):
            if value:
                clauses.append(f"{column} = ?")
                values.append(value)
        if date_from:
            clauses.append("report_date >= ?")
            values.append(date_from.isoformat())
        if date_to:
            clauses.append("report_date <= ?")
            values.append(date_to.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        direction = "DESC" if descending else "ASC"
        with database_connection(self.database_path) as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM incidents{where}", values).fetchone()[0])
            rows = connection.execute(
                f"SELECT * FROM incidents{where} ORDER BY {sort_by} {direction} LIMIT ? OFFSET ?",
                (*values, limit, offset),
            ).fetchall()
        return [_incident_from_row(row) for row in rows], total

    def all_matching_incidents(
        self, *, category: str | None = None, date_from: date | None = None, date_to: date | None = None
    ) -> list[Incident]:
        """Return the complete filtered set for aggregate analytics, in safe batches."""
        _, total = self.search_incidents(category=category, date_from=date_from, date_to=date_to, limit=1)
        results: list[Incident] = []
        for offset in range(0, total, 500):
            batch, _ = self.search_incidents(
                category=category, date_from=date_from, date_to=date_to, limit=500, offset=offset
            )
            results.extend(batch)
        return results

    def update_incident(self, incident_id: str, update: IncidentUpdate, actor: str | None = None) -> Incident:
        changes = update.model_dump(exclude_unset=True)
        if not changes:
            return self.get_incident(incident_id)
        current = self.get_incident(incident_id)
        if "severity" in changes or "severity_source" in changes:
            severity = changes.get("severity", current.severity)
            source = changes.get("severity_source", current.severity_source)
            if (severity is None) != (source is None):
                raise ValueError("Severity and severity source must be supplied together")
        occurrence = changes.get("occurrence_date", current.occurrence_date)
        report = changes.get("report_date", current.report_date)
        if occurrence and report and occurrence > report:
            raise ValueError("Occurrence date cannot be later than report date")
        serialized = {
            key: (value.value if hasattr(value, "value") else value.isoformat() if isinstance(value, date) else value)
            for key, value in changes.items()
        }
        disallowed = set(serialized) - ALLOWED_UPDATE_COLUMNS
        if disallowed:
            raise ValueError(f"Disallowed update fields: {disallowed}")
        serialized["updated_at"] = utc_iso()
        assignments = ", ".join(f"{key} = ?" for key in serialized)
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                f"UPDATE incidents SET {assignments} WHERE incident_id = ?",
                (*serialized.values(), incident_id),
            )
            if cursor.rowcount != 1:
                raise IncidentNotFoundError(f"Incident {incident_id} was not found")
            safe_fields = {"category", "category_source", "severity", "severity_source", "assigned_reviewer", "resolution_summary"}
            audit_values = []
            for field in changes:
                if field in safe_fields:
                    before = getattr(current, field)
                    before_value = getattr(before, "value", before) or "not set"
                    after_value = serialized[field] or "not set"
                    audit_values.append(f"{field}: {before_value} -> {after_value}")
                else:
                    audit_values.append(field)
            self._add_event(connection, incident_id, "incident_updated", actor,
                            f"Updated: {'; '.join(audit_values)}", serialized["updated_at"])
        return self.get_incident(incident_id)

    def transition_status(self, incident_id: str, target: IncidentStatus, actor: str | None = None) -> Incident:
        current = self.get_incident(incident_id)
        validate_transition(current.status, target)
        now = utc_iso()
        with database_connection(self.database_path) as connection:
            cursor = connection.execute("UPDATE incidents SET status = ?, updated_at = ? WHERE incident_id = ?",
                                        (target.value, now, incident_id))
            if cursor.rowcount != 1:
                raise IncidentNotFoundError(f"Incident {incident_id} was not found")
            self._add_event(connection, incident_id, "status_changed", actor,
                            f"{current.status.value} -> {target.value}", now)
        return self.get_incident(incident_id)

    def list_evidence_references(self, incident_id: str) -> list[str]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute("SELECT reference FROM evidence_references WHERE incident_id = ?", (incident_id,)).fetchall()
        return [str(row["reference"]) for row in rows]

    def reset_demo_incidents(self) -> int:
        """Remove explicitly marked demo records without touching user reports."""
        with database_connection(self.database_path) as connection:
            cursor = connection.execute("DELETE FROM incidents WHERE is_demo = 1")
        return cursor.rowcount

    def add_ai_assessment(self, assessment: AIAssessment) -> AIAssessment:
        now = utc_iso()
        with database_connection(self.database_path) as connection:
            connection.execute("""INSERT INTO ai_assessments(incident_id, provider_mode, model_name, suggested_category,
                suggested_severity, risk_score, confidence, rationale, recommendations_json, concise_summary, observed_failure_or_concern,
                potential_harms_json, affected_stakeholders_json, evidence_json, missing_information_json, immediate_containment_steps_json,
                corrective_actions_json, urgent_human_review_recommended, severity_explanation, prompt_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (assessment.incident_id, assessment.provider_mode, assessment.model_name, assessment.suggested_category.value,
                 assessment.suggested_severity.value, assessment.risk_score, assessment.confidence, assessment.observed_failure_or_concern,
                 json.dumps(assessment.recommended_corrective_actions), assessment.concise_summary, assessment.observed_failure_or_concern,
                 json.dumps(assessment.potential_harms), json.dumps(assessment.affected_stakeholders), json.dumps([item.model_dump() for item in assessment.evidence]),
                 json.dumps(assessment.missing_information), json.dumps(assessment.immediate_containment_steps), json.dumps(assessment.recommended_corrective_actions),
                 int(assessment.urgent_human_review_recommended), assessment.severity_explanation, assessment.prompt_version, now))
            self._add_event(connection, assessment.incident_id, "ai_assessment_added", None,
                            f"Assessment source: {assessment.provider_mode}", now)
        return assessment.model_copy(update={"created_at": datetime.fromisoformat(now)})

    def add_reviewer_note(self, note: ReviewerNote) -> ReviewerNote:
        now = utc_iso()
        with database_connection(self.database_path) as connection:
            connection.execute("INSERT INTO reviewer_notes(incident_id, body, author, created_at) VALUES (?, ?, ?, ?)",
                               (note.incident_id, note.body, note.author, now))
            self._add_event(connection, note.incident_id, "reviewer_note_added", note.author, "Reviewer note added", now)
        return note.model_copy(update={"created_at": datetime.fromisoformat(now)})

    def add_corrective_action(self, action: CorrectiveAction) -> CorrectiveAction:
        now = utc_iso()
        with database_connection(self.database_path) as connection:
            connection.execute("""INSERT INTO corrective_actions(incident_id, title, action_kind, owner, status, due_date, evidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (action.incident_id, action.title, action.action_kind, action.owner, action.status,
                 action.due_date.isoformat() if action.due_date else None, action.evidence, now))
            self._add_event(connection, action.incident_id, "corrective_action_added", action.owner,
                            "Corrective action added", now)
        return action.model_copy(update={"created_at": datetime.fromisoformat(now)})

    def list_audit_events(self, incident_id: str) -> list[AuditEvent]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM audit_events WHERE incident_id = ? ORDER BY created_at, id", (incident_id,)).fetchall()
        return [AuditEvent(incident_id=row["incident_id"], event_type=row["event_type"], actor=row["actor"],
                           details=row["details"], created_at=_dt(row["created_at"])) for row in rows]

    def list_ai_assessments(self, incident_id: str) -> list[AIAssessment]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM ai_assessments WHERE incident_id = ? ORDER BY created_at", (incident_id,)).fetchall()
        return [AIAssessment(incident_id=row["incident_id"], provider_mode=row["provider_mode"], model_name=row["model_name"], prompt_version=row["prompt_version"],
                             suggested_category=row["suggested_category"], suggested_severity=row["suggested_severity"],
                             risk_score=row["risk_score"], confidence=row["confidence"], concise_summary=row["concise_summary"], observed_failure_or_concern=row["observed_failure_or_concern"],
                             potential_harms=json.loads(row["potential_harms_json"]), affected_stakeholders=json.loads(row["affected_stakeholders_json"]), evidence=json.loads(row["evidence_json"]),
                             missing_information=json.loads(row["missing_information_json"]), immediate_containment_steps=json.loads(row["immediate_containment_steps_json"]),
                             recommended_corrective_actions=json.loads(row["corrective_actions_json"]), urgent_human_review_recommended=bool(row["urgent_human_review_recommended"]), severity_explanation=row["severity_explanation"], created_at=_dt(row["created_at"])) for row in rows]

    def list_reviewer_notes(self, incident_id: str) -> list[ReviewerNote]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM reviewer_notes WHERE incident_id = ? ORDER BY created_at", (incident_id,)).fetchall()
        return [ReviewerNote(incident_id=row["incident_id"], body=row["body"], author=row["author"],
                             created_at=_dt(row["created_at"])) for row in rows]

    def list_corrective_actions(self, incident_id: str) -> list[CorrectiveAction]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM corrective_actions WHERE incident_id = ? ORDER BY created_at", (incident_id,)).fetchall()
        return [CorrectiveAction(incident_id=row["incident_id"], title=row["title"], action_kind=row["action_kind"], owner=row["owner"], status=row["status"],
                                 due_date=_date(row["due_date"]), evidence=row["evidence"], created_at=_dt(row["created_at"])) for row in rows]
