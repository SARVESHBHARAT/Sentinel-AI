import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS incident_sequences (
    year INTEGER PRIMARY KEY,
    last_value INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    reference TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviewer_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    author TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS corrective_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    action_kind TEXT NOT NULL DEFAULT 'corrective',
    owner TEXT,
    status TEXT NOT NULL,
    due_date TEXT,
    evidence TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_events_incident ON audit_events(incident_id, created_at);
"""

#: Fresh-install shape for incidents (CREATE TABLE only; never ALTER path).
INCIDENTS_FRESH_DDL = """
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    category_source TEXT NOT NULL DEFAULT 'reporter',
    affected_system TEXT,
    provider TEXT,
    occurrence_date TEXT,
    report_date TEXT NOT NULL,
    severity TEXT,
    severity_source TEXT,
    potential_impact TEXT,
    affected_population TEXT,
    reporter_name TEXT,
    reporter_contact TEXT,
    anonymous_report INTEGER NOT NULL CHECK (anonymous_report IN (0, 1)),
    assigned_reviewer TEXT,
    resolution_summary TEXT,
    status TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    affected_model_name TEXT,
    affected_model_version TEXT,
    verification_status TEXT NOT NULL DEFAULT 'reported',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_category ON incidents(category);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
"""

#: Fresh-install shape for ai_assessments (CREATE TABLE only).
ASSESSMENTS_FRESH_DDL = """
CREATE TABLE IF NOT EXISTS ai_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    provider_mode TEXT NOT NULL,
    model_name TEXT NOT NULL,
    suggested_category TEXT NOT NULL,
    suggested_severity TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    confidence REAL NOT NULL,
    rationale TEXT NOT NULL,
    recommendations_json TEXT NOT NULL,
    concise_summary TEXT NOT NULL DEFAULT '',
    observed_failure_or_concern TEXT NOT NULL DEFAULT '',
    potential_harms_json TEXT NOT NULL DEFAULT '[]',
    affected_stakeholders_json TEXT NOT NULL DEFAULT '[]',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    missing_information_json TEXT NOT NULL DEFAULT '[]',
    immediate_containment_steps_json TEXT NOT NULL DEFAULT '[]',
    corrective_actions_json TEXT NOT NULL DEFAULT '[]',
    urgent_human_review_recommended INTEGER NOT NULL DEFAULT 0,
    severity_explanation TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT 'legacy',
    model_version TEXT,
    system_fingerprint TEXT,
    created_at TEXT NOT NULL
);
"""


def initialize_schema(connection: sqlite3.Connection) -> None:
    # NOTE: CREATE TABLE statements run individually (not one executescript)
    # because sqlite3 aborts the whole script when a legacy table already
    # exists without the newest columns (e.g. no affected_model_name index).
    # Missing-table creation first, then additive ALTER migrations below.
    connection.executescript(SCHEMA)
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "incidents" not in tables:
        connection.executescript(INCIDENTS_FRESH_DDL)
    if "ai_assessments" not in tables:
        connection.executescript(ASSESSMENTS_FRESH_DDL)
    # Small additive migration for databases created during early Phase 1 builds.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(incidents)")}
    if "is_demo" not in columns:
        connection.execute(
            "ALTER TABLE incidents ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1))"
        )
    if "category_source" not in columns:
        connection.execute("ALTER TABLE incidents ADD COLUMN category_source TEXT NOT NULL DEFAULT 'reporter'")
    if "resolution_summary" not in columns:
        connection.execute("ALTER TABLE incidents ADD COLUMN resolution_summary TEXT")
    action_columns = {row[1] for row in connection.execute("PRAGMA table_info(corrective_actions)")}
    if "action_kind" not in action_columns:
        connection.execute("ALTER TABLE corrective_actions ADD COLUMN action_kind TEXT NOT NULL DEFAULT 'corrective'")
    incident_additions = {
        "affected_model_name": "TEXT",
        "affected_model_version": "TEXT",
        "verification_status": "TEXT NOT NULL DEFAULT 'reported'",
    }
    for name, definition in incident_additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE incidents ADD COLUMN {name} {definition}")
    # Historical rows predate verification tracking; 'reported' is the safe
    # mapping (never implies verification). NULL can only occur for rows
    # written by a concurrent older process between ADD COLUMN and backfill.
    connection.execute("UPDATE incidents SET verification_status = 'reported' WHERE verification_status IS NULL OR verification_status = ''")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_provider ON incidents(provider)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_affected_model ON incidents(affected_model_name, affected_model_version)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_incidents_verification ON incidents(verification_status)")
    assessment_columns = {row[1] for row in connection.execute("PRAGMA table_info(ai_assessments)")}
    additions = {
        "concise_summary": "TEXT NOT NULL DEFAULT ''",
        "observed_failure_or_concern": "TEXT NOT NULL DEFAULT ''",
        "potential_harms_json": "TEXT NOT NULL DEFAULT '[]'",
        "affected_stakeholders_json": "TEXT NOT NULL DEFAULT '[]'",
        "evidence_json": "TEXT NOT NULL DEFAULT '[]'",
        "missing_information_json": "TEXT NOT NULL DEFAULT '[]'",
        "immediate_containment_steps_json": "TEXT NOT NULL DEFAULT '[]'",
        "corrective_actions_json": "TEXT NOT NULL DEFAULT '[]'",
        "urgent_human_review_recommended": "INTEGER NOT NULL DEFAULT 0",
        "severity_explanation": "TEXT NOT NULL DEFAULT ''",
        "prompt_version": "TEXT NOT NULL DEFAULT 'legacy'",
        "model_version": "TEXT",
        "system_fingerprint": "TEXT",
    }
    for name, definition in additions.items():
        if name not in assessment_columns:
            connection.execute(f"ALTER TABLE ai_assessments ADD COLUMN {name} {definition}")
    connection.execute("UPDATE ai_assessments SET concise_summary = 'Not recorded' WHERE concise_summary = ''")
    connection.execute("UPDATE ai_assessments SET observed_failure_or_concern = 'Not recorded' WHERE observed_failure_or_concern = ''")
    connection.execute("UPDATE ai_assessments SET severity_explanation = 'Not recorded' WHERE severity_explanation = ''")
