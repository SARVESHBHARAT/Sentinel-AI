# Sentinel AI — Development Status

_Last updated: Phase 10 (on-page incident selection fix — verified: 99 passed, ruff clean)._

## Phase 10 — implemented and verified

- **Root cause fixed**: Incident Details and AI Triage previously dead-ended on
  "Select an incident…" whenever `selected_incident_id` was unset (fresh session
  or browser refresh) — no on-page selector existed. Secondary cause: a leaked
  `SENTINEL_DATABASE_PATH` env var in the dev terminal pointed the running app at
  a temp DB instead of `data/sentinel.db`; the app now runs with a clean env and
  the dev DB was re-seeded (30 incidents: 1 genuine + 29 synthetic).
- **Fix**: new reusable `fetch_incident_options` / `incident_picker` in
  `ui/components.py`; both pages render a visible selector (ID — Title) backed by
  `search_incidents`, default to the current selection when valid, persist changes
  to `selected_incident_id` and rerun, recover from stale IDs, and show an empty
  state with a "Report an incident" navigation button. AI Triage shows incident
  status/severity and disables the triage action under `SENTINEL_READ_ONLY`.
- Tests: `tests/test_incident_selection.py` (9 AppTest-based tests). Verified:
  **99 passed**, `ruff check --select E4,E7,E9,F` clean, compileall clean.

---

_Last updated: Phase 9 (AI Model Observatory + synthetic demo dataset — verified: 90 passed, ruff clean)._

## Phase 9 — implemented and verified

- **AI Model Observatory** (`ui/pages/model_intelligence.py`): dataset selector
  (all / synthetic demo / genuine), global overview metrics (totals, distinct
  providers/models/versions, verified, disputed, high/critical, synthetic count),
  sortable exact-model leaderboard (rank only for count-based sorts; verification
  rate shown as "verified ÷ total"), model drill-down with per-version stats and
  reported-vs-verified charts, side-by-side comparison workspace. All metrics are
  report counts — no usage-adjusted rates, no safety scores, unknown versions
  never merged; below `SENTINEL_MODEL_INTEL_MIN_SAMPLE` the UI shows
  "Insufficient data for comparison".
- **Synthetic demo dataset** (`demo_seed.py`): 29 deterministic fictional
  `[DEMO]` incidents across 5 demo providers, 9 model identifiers, 10 version
  slots (incl. unknown version/provider slots), spread over 10 months, with demo
  triage assessments and audited verification-state chains. Idempotent via
  existing-title skip; seeded only with `is_demo=True`; exports labelled
  "SYNTHETIC DEMO DATA"; reset removes demo records only. Settings → "Seed
  synthetic demo dataset" button (disabled in read-only mode).
- Repository: `search_incidents` gained `is_demo` filter (parameterized).
- Report service: synthetic-demo label line in Markdown/PDF exports.
- Tests: `tests/test_observatory.py` (18 tests). Verified: **90 passed**,
  `ruff check --select E4,E7,E9,F` clean, compileall clean.

---

_Last updated: Phase 8 (CSS rendering regression fix)._

## Phase 7 — implemented and verified

- Report form collects provider, affected model name/version (optional, validated; unknown
  allowed); persists via `CreateIncident`; historical records without metadata still open.
- New Model Intelligence page (`ui/pages/model_intelligence.py`, in sidebar): live
  `ModelIntelligenceService` metrics, provider → model → version drill-down, severity/
  category/verification charts, period + provider/model/version/severity/category/
  verification filters, empty states, Unknown grouping, insufficient-data warning with
  formula `share_of_matching_reports = group_count / total_matching_reports`; no safety
  rankings, no usage rates; demo records labelled.
- Incident Details verification UI: current-status badge, allowed-next-states, required
  reviewer + reason, verify/dispute/mark-unverified via `IncidentService`, invalid
  transitions show errors, `verification_changed` history from audit events, stale
  selections handled, refresh on success. Typed reviewer names flagged as unauthenticated.
- Explorer adds verification + provider filters; reports include affected model/version,
  assessing-model version, verification status, and optional reporter-PII redaction
  (`[redacted]`, stored data unchanged); `Incident` now exposes reporter fields.
- Hardening: `SENTINEL_READ_ONLY` enforced at service + repository layers (tested for
  every write path); in-memory submission throttle
  (`SENTINEL_SUBMISSION_RATE_LIMIT/WINDOW`, documented limits); SQL/CSV/XSS/safe-error
  protections retained; no fake auth — external auth documented (Cloud ACL, oauth2-proxy,
  VPN).
- Deployment: `Dockerfile`, `docker-compose.yml` (persistent `sentinel-data` volume),
  `.env.example` placeholders, `scripts/backup_db.py` (SQLite online backup + rotation),
  restore/scheduling/retention docs, deployment-prerequisites section.
- Tests: `tests/test_phase7_integration.py` (8 tests: submit with/without metadata,
  filters, verification audit, redaction, read-only blocks, backup script, severity).
  Verified: `70 passed`, `ruff check --select E4,E7,E9,F` clean.
  Docker: CLI present (`29.7.2`) but daemon not running → `docker build` NOT validated
  (connection error to dockerDesktopLinuxEngine pipe).

## Phase 6 — implemented and verified (backend only, no dashboard UI)

- Additive migrations: `incidents.affected_model_name`, `incidents.affected_model_version`,
  `incidents.verification_status` (default `reported`), `ai_assessments.model_version`,
  `ai_assessments.system_fingerprint`; new indexes on provider, affected model, verification.
  Legacy databases open without data loss; historical rows read as `reported` (never verified).
- Verification lifecycle (`domain/lifecycle.py`, separate from `IncidentStatus`):
  `reported -> ai_assessed -> human_reviewed -> verified | disputed`, plus `unverified`
  for not-verifiable reports. AI triage moves `reported/unverified -> ai_assessed` only
  (inside the `add_ai_assessment` transaction, audited as `verification_changed`).
  `IncidentService.verify/dispute/mark_unverified` require reviewer + justification and
  write reviewer notes; invalid transitions raise `ValueError`.
- Assessment vs affected model are separate: `AIAssessment.model_name/model_version/`
  `system_fingerprint` describe the *assessing* provider; `Incident.affected_model_name/`
  `affected_model_version` describe the *reported* system. OpenAI captures the returned
  `completion.model` and `system_fingerprint` (fingerprint never presented as a version);
  `SENTINEL_OPENAI_MODEL_VERSION` override stored only when set; demo stays
  `sentinel-deterministic-demo-v1`. No version is ever invented.
- New `services/model_intelligence_service.py`: `summary/groups/compare` by provider,
  affected model/version, dates, category, verification status; unknown values grouped
  as `Unknown` without merging into known versions; `compare()` returns
  `sufficient_data=False` + explicit insufficient-data note below `min_sample`
  (default 5, via `SENTINEL_MODEL_INTEL_MIN_SAMPLE`). Formula documented:
  `share_of_matching_reports = group_count / total_matching_reports` — reported counts
  only, no usage denominators, no safety scores, AI output never treated as verification.
- Tests: `tests/test_model_intelligence.py` (16 tests) + 1 updated Phase 5 audit
  expectation. Verified: `62 passed`, `ruff check --select E4,E7,E9,F` clean.
- Not built (next phase): Model Intelligence dashboard UI, verification buttons in
  Details/Triage pages, report-form affected-model fields, comprehensive QA, security
  hardening, deployment preparation.

---

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
| `SENTINEL_OPENAI_MODEL_VERSION` | *(unset)* | Explicit assessing-model version override (stored only when set; never invented).|
| `SENTINEL_MODEL_INTEL_MIN_SAMPLE` | `5` | Minimum matching reports before a model comparison reports sufficient data. |

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

