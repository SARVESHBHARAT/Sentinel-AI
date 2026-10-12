# Sentinel AI — Development Status

_Last updated: Phase 5 (production-readiness audit & defect fixes)._

Sentinel AI (a.k.a. ERA IncidentGuard) is a Streamlit application for the ethical and
responsible reporting, triage, and governance of AI-system incidents. This document is a
handoff for the next developer/AI agent so the investigation is not repeated.

---

## 1. What the application is

- **Entry point:** `app.py` (run with Streamlit). It builds `Settings` from the
  environment, opens the SQLite repository, initialises services, and renders one of
  seven pages via the sidebar.
- **Architecture (layered, keep it this way):**
  - `src/sentinel/config.py` — env-driven `Settings` (frozen dataclass).
  - `src/sentinel/database/` — `connection.py` (SQLite context manager, WAL, FK on),
    `schema.py` (DDL), `repositories.py` (all SQL; the only place SQL lives).
  - `src/sentinel/domain/` — `enums.py` (categories, severities, statuses, sources) and
    `lifecycle.py` (`ALLOWED_TRANSITIONS`, `validate_transition`).
  - `src/sentinel/schemas/` — Pydantic models (`Incident`, `CreateIncident`,
    `IncidentUpdate`, `AIAssessment`, `AIModelAssessment`, `AuditEvent`, `ReviewerNote`,
    `CorrectiveAction`). Validation lives here, not in the UI.
  - `src/sentinel/services/` — `IncidentService` (business interface), `AnalyticsService`
    (dashboard metrics), `ReportService` (Markdown/PDF/CSV exports).
  - `src/sentinel/ai/` — `triage_service.py` (provider abstraction: demo + OpenAI) and
    `prompts.py` (system prompt + minimized payload builder).
  - `src/sentinel/ui/` — `styles.py`, `components.py`, and `pages/` (report_incident,
    explorer, details, triage, reports, overview, settings).
- **Storage:** SQLite via the Python stdlib `sqlite3`. Default path
  `data/sentinel.db`, overridable with `SENTINEL_DATABASE_PATH`. WAL mode + foreign keys
  are enabled on every connection.
- **AI triage:** an interface (`TriageProvider`) with two implementations —
  `DemoTriageProvider` (deterministic, offline, labelled as demo) and
  `OpenAITriageProvider` (structured `AIModelAssessment` output). Assessments are stored
  as **append-only history**; a reviewer can override the suggested category/severity,
  which requires a justification and is recorded as a reviewer note.

## 2. Features verified this phase

All confirmed by running code (tests + live scripted runs), not by reading source alone:

- [x] Startup with a clean database (schema auto-created) and with no API key
      (auto demo mode).
- [x] Demo-mode incident submission end to end.
- [x] Form validation: empty/oversized title & description, future `report_date`,
      occurrence-after-report date, anonymous-with-identity, severity/source pairing.
- [x] Persistence across repository reinstantiation and simulated restart.
- [x] Search, filter (category/severity/status/date range), sort, pagination, detail view.
- [x] AI triage (demo provider) and human override of AI category/severity with
      justification.
- [x] Status transitions validated against `ALLOWED_TRANSITIONS`.
- [x] Reviewer notes, reviewer assignment, corrective actions.
- [x] Audit-event trail matches real changes; reassessments preserve history.
- [x] Demo records are flagged (`is_demo`) and separable via `reset_demo_incidents`.
- [x] Dashboard metrics, Markdown report, PDF report (ReportLab), CSV register export.
- [x] Graceful AI-provider failure handling (safe messages, no raw exception leakage).
- [x] Duplicate creation after an error is prevented (read-back inside the same
      transaction; failures roll back).

## 3. Defects fixed this phase

Each was reproduced before fixing and has a regression test in
`tests/test_phase5_regressions.py`.

1. **`ALLOWED_UPDATE_COLUMNS` was defined but never enforced.** `update_incident`
   built its `SET` clause from whatever `IncidentUpdate` carried with no column
   whitelist. Now validated; disallowed fields raise `ValueError`.
   *(SQL-injection hardening of the update path.)*
2. **AI-assessment column mismatch.** The `rationale` column received
   `severity_explanation` instead of `observed_failure_or_concern`. Fixed the mapping
   in `add_ai_assessment`; verified at the raw-DB level.
3. **Over-long audit text could crash reads.** `details`/`actor` are now clipped to the
   `AuditEvent` schema limits on **both** write and read, so rows written before the cap
   still render instead of failing Pydantic validation.
4. **Unsafe/incorrect sort.** `search_incidents` ORDER BY is now restricted to a fixed
   `SORT_EXPRESSIONS` whitelist; an unknown `sort_by` raises `ValueError` before any SQL
   is built. *(No user text ever reaches the SQL string.)*
5. **False "not created/not updated" leading to duplicate submissions.** `create_incident`
   and `update_incident`/`transition_status` now read the row back **inside** the same
   transaction and only report success on a real row, so a failed write rolls back instead
   of inviting a duplicate.
6. **No-op saves bumped `updated_at` and emitted a misleading audit event.** Changes whose
   value already matches storage are dropped before the UPDATE; audit events now describe
   real changes only.
7. **Stale selection crashed whole pages.** Triage, Details, and Reports now handle
   `IncidentNotFoundError` (e.g. after the demo reset deletes the open incident) with a
   recoverable message instead of a traceback.
8. **CSV formula injection.** `ReportService.register_csv` neutralises cells starting with
   `= + - @` (tab/CR) by prefixing a single quote; the CSV download button is now exposed
   on the Reports page.
9. **`report_date` was not range-validated at the schema layer** (a year-2099 date was
   accepted). `CreateIncident`/`IncidentUpdate` now reject implausible future report dates.
10. **Markdown/HTML injection via untrusted report text.** Added `escape_markdown` and
    `html.escape`-based `badge` in `components.py`; titles, descriptions, AI-assessment
    output, and reviewer fields are rendered literally rather than as live Markdown/links.


## 4. Security posture and known limitations

**Hardened:** parameterised SQL throughout (whitelisted column/order identifiers);
untrusted text escaped before Markdown/HTML rendering; CSV formula injection
neutralised; AI prompt-injection mitigated (system prompt instructs the model to treat all
payload strings as untrusted; only a minimised payload — no reporter identity, audit
history, or other records — is transmitted); safe, non-revealing error messages (raw
provider/SQL exceptions are never shown to users); no secrets committed (`.env` is
git-ignored; `.env.example` holds only placeholders); demo data is explicitly flagged.

**Limitations — read before any real deployment:**

- **No authentication or authorization.** There is **no login, user accounts, roles, or
  session control.** Any person who can reach the running app can read every incident,
  submit reports, and change status/severity. **This application is NOT safe for
  unrestricted public use.** A reverse proxy or Streamlit auth layer must be added first.
- **State-changing endpoints are unprotected** (status transitions, overrides, demo reset,
  reviewer assignment) — they inherit the same "anyone can do anything" exposure.
- **Local SQLite on ephemeral hosting will lose data on redeploy.** Streamlit Community
  Cloud and most PaaS redraw the filesystem; `data/sentinel.db` will not persist. Use a
  managed database / external volume before hosting real data.
- **No automated database backups or retention policy** exist. Add both before
  production.
- **ReportLab PDF is an optional dependency**; PDF export degrades to an informational
  message when it is absent.

## 5. Tests

- **Command:** `python -m pytest -q`
- **Result:** `46 passed in ~5.4s` (verified by running, not assumed).
- **Coverage added:** `tests/test_phase5_regressions.py` (allowed-column enforcement,
  rationale mapping, sort whitelist/validation, CSV export + injection neutralisation,
  search/filter/sort, AI override justification, audit-event correspondence).
- **Lint:** `python -m ruff check --select E4,E7,E9,F,I,UP,B,SIM,C4 src tests`. The
  real bug classes (`F` unused/undefined names, errors) are clean. Remaining findings are
  stylistic import-ordering/`dict()` preferences in pre-existing modules and were left
  untouched to avoid rewriting working code.


## 6. Local execution

```bash
# 1. Create and activate a virtual environment (once)
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Configure (optional — safe defaults exist)
copy .env.example .env                 # then edit; .env is git-ignored

# 4. Run the app (demo mode by default; no API key required)
streamlit run app.py

# 5. Run the tests
python -m pytest -q
```

Key environment variables (all optional):

| Variable                 | Default              | Purpose                                            |
|--------------------------|----------------------|----------------------------------------------------|
| `SENTINEL_DATABASE_PATH` | `data/sentinel.db`   | SQLite file location (configurable).               |
| `SENTINEL_DEMO_MODE`     | `true`               | Force deterministic offline (demo) assessments.    |
| `SENTINEL_OPENAI_MODEL`  | `gpt-4.1-mini`       | Model used when live triage is enabled.            |
| `OPENAI_API_KEY`         | *(unset)*            | When set and demo mode off, enables live AI triage.|

If `OPENAI_API_KEY` is unset, `effective_demo_mode` is automatically `True`.

## 7. Deployment preparation status

- `requirements.txt` — present and consistent with imports (streamlit, openai, pydantic,
  plotly, python-dotenv, pytest, reportlab).
- `.env.example` — placeholders only; no secrets.
- `.gitignore` — ignores `.env`, `.venv`, caches, `.streamlit/secrets.toml`, and
  `data/*.db` (only `data/.gitkeep` tracked).
- `README.md` — startup + env docs (see "Local execution" above).
- **Not done (intentional):** no deployment was performed; no auth layer added; no
  external DB migration. See limitations in section 4.

## 8. Remaining work / next phase

1. **AI model incident intelligence (next phase).** The data model already supports it:
   `AIAssessment` stores `provider_mode`, `model_name`, `prompt_version`, and
   `created_at`, and assessments are append-only per incident. Keep storing the exact
   **provider, model name, and model version** on every assessment so incidents stay
   traceable to a specific model/version. Add a `model_version` field to `AIAssessment`
   when the new provider exposes it, without a destructive migration.
2. Add authentication/authorization before any non-local deployment.
3. Move persistence to a managed database for hosted deployments.
4. Add automated DB backup + retention.

## 9. Quick orientation for the next agent

- Start at `app.py` → `Settings.from_environment()` → `IncidentRepository.initialize()`.
- **All SQL lives in `repositories.py`.** Services orchestrate; the UI only renders.
- Validation lives in Pydantic schemas (`schemas/incident.py`), not the UI.
- When touching AI: keep assessments append-only and never mutate historical ones.
- Run `python -m pytest -q` after every change; the suite is the regression net.

