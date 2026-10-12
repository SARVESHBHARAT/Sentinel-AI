# Sentinel AI

Sentinel AI is an incident reporting and governance portal for AI-system failures, harmful outputs, privacy concerns, discriminatory decisions, security issues, and reliability problems.

## Requirements

- Python 3.10 or later
- An isolated Python environment is recommended

## Quick start

```bash
python3 -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
cp .env.example .env
```

The default configuration stores the SQLite database at `data/sentinel.db` and enables demo mode. **Do not commit `.env`** — it may contain `OPENAI_API_KEY`.

## Run the application

```bash
python -m streamlit run app.py
```

## Run tests

```bash
python -m pytest
```

## Run linter

```bash
python -m ruff check src tests
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `SENTINEL_DATABASE_PATH` | `data/sentinel.db` | SQLite file path |
| `SENTINEL_DEMO_MODE` | `true` | Deterministic demo behavior; no API calls |
| `SENTINEL_OPENAI_MODEL` | `gpt-4.1-mini` | Model for OpenAI triage |
| `OPENAI_API_KEY` | unset | OpenAI credential; never persisted in DB or logged |

When no API key is present, `effective_demo_mode` is always `true`, preventing any UI from implying a live model assessment occurred.

## AI triage

Set `SENTINEL_DEMO_MODE=false` and configure `OPENAI_API_KEY` to enable live triage. In demo mode (or whenever the key is absent), the application uses a deterministic keyword-based provider named `sentinel-deterministic-demo-v1`. Its assessments are visibly labelled **Demo** and are never represented as OpenAI results.

**Data minimization:** Live requests send only assessment-relevant fields: title, description, reported category, affected system/provider, dates, impact, affected population, and evidence references. Reporter identity, audit history, unrelated incidents, and uploaded files are never sent.

**Prompt injection defence:** The triage prompt instructs the model to treat all incident text as untrusted evidence and never follow embedded instructions. Each assessment records prompt version, provider mode, model identifier, and UTC timestamp.

**Human oversight:** AI recommendations are advisory. A reviewer can accept, override (with mandatory justification), or request reassessment. Overrides are recorded as reviewer notes and audit events.

## Application pages

- **Overview** — Incident metrics, category/severity distributions, and reporting trend from the database.
- **Report an Incident** — Guided form with Pydantic validation; review-before-submit.
- **Incident Explorer** — Search by ID/title, filter by category/severity/status/dates, sort, paginate.
- **Incident Details** — Case record, review controls, status transitions, reviewer notes, corrective actions, audit trail.
- **AI Triage** — Persisted assessments with provenance; human determination form.
- **Reports** — Markdown and PDF export from stored case data.
- **Settings** — Configuration display; safe demo-data reset (only records with `is_demo=True`).

## Architecture

- **Incident IDs:** `INC-YYYY-NNNN`, allocated via per-year SQLite sequence inside `BEGIN IMMEDIATE` transactions.
- **Timestamps:** UTC-aware ISO 8601. `display_local` converts to host timezone for UI.
- **Lifecycle:** Submitted → Under Review → Action Required or Resolved → Closed. Resolution may return to Action Required; Action Required may return to Under Review.
- **Audit trail:** Every creation, update, status change, note, corrective action, and assessment writes an audit event.
- **Demo isolation:** Demo records carry `is_demo=True` and can be selectively purged via `reset_demo_incidents()`.

## Security and authorization limitations

> **⚠️ This application does not implement authentication or authorization.**
>
> There is no login system, user management, role-based access control, or session management. Any user with network access to the application can view, create, and modify all incidents. **Do not deploy this application on the public internet without adding an authentication layer** (e.g., Streamlit Community Cloud auth, an OAuth proxy, or VPN restriction).

### Security measures in place

- **No hardcoded credentials.** API keys are loaded from environment variables via `.env` (which is in `.gitignore`).
- **No SQL injection.** All database queries use parameterized statements. Dynamic column names in `update_incident` are validated against `ALLOWED_UPDATE_COLUMNS`.
- **No unsafe HTML rendering.** User-supplied text is rendered via `st.text()` (preformatted, no HTML interpretation). Badge values are HTML-escaped. PDF exports escape all content via `html.escape()`.
- **Prompt injection mitigation.** The system prompt instructs the model to treat incident text as evidence, not instructions. Reporter identity is excluded from AI payloads.
- **Error message safety.** AI provider errors are mapped to safe user-facing messages; raw provider details are not exposed.
- **No sensitive data in logs.** API keys are not logged or stored in the database.
- **Temporary file safety.** PDF generation uses in-memory `BytesIO` buffers, not temporary files.

### Known limitations

- **No authentication / authorization** — see warning above.
- **No CSRF protection** — Streamlit forms do not implement CSRF tokens; acceptable for internal-network use.
- **No rate limiting** — any user can submit unlimited incidents.
- **No encryption at rest** — SQLite database is not encrypted. Use filesystem-level encryption for sensitive deployments.

## Data integrity and privacy

- Incident IDs are unique per year via a SQLite sequence counter inside write transactions.
- Database writes use `BEGIN IMMEDIATE` for sequence allocation and the `database_connection` context manager for atomic commits with rollback on error.
- Audit events are written in the same transaction as the change they record.
- AI reassessments create new rows; historical assessments are never overwritten.
- Demo data is explicitly marked with `is_demo=True` and cannot be confused with real reports.
- Reporter identity is excluded from AI payloads.
- The database path is configurable via `SENTINEL_DATABASE_PATH`.

## Deployment

### Local development

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python -m streamlit run app.py
```

### Streamlit Community Cloud

1. Push the repository to GitHub.
2. Connect the repository in [share.streamlit.io](https://share.streamlit.io).
3. Set `OPENAI_API_KEY` and other variables in the Streamlit Secrets panel.
4. **Important:** Streamlit Community Cloud has an **ephemeral filesystem**. The SQLite database at `data/sentinel.db` will be lost on every redeployment or container restart. For persistent data, either:
   - Use an external database (PostgreSQL via `SENTINEL_DATABASE_PATH` — requires code changes to swap the SQLite driver).
   - Accept that demo/dev data is ephemeral and back up via the Reports page.

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Persistent storage:** Mount a volume for the database directory:

```bash
docker run -v sentinel-data:/app/data -p 8501:8501 sentinel-ai
```

### Filesystem persistence warning

SQLite stores data in a local file. The following platforms have ephemeral filesystems where data **will be lost** on redeployment:

| Platform | Persistence | Workaround |
| --- | --- | --- |
| Streamlit Cloud | ❌ Ephemeral | Use external DB or accept data loss |
| Heroku | ❌ Ephemeral | Use Heroku Postgres (requires driver change) |
| Railway | ✅ With volume | Attach a persistent volume |
| Fly.io | ✅ With volume | Attach a Fly Volume |
| Docker | ✅ With volume | Use `-v` mount |
| VM / bare metal | ✅ Native | Ensure backup strategy |

## Troubleshooting

### Application won't start

1. Verify Python 3.10+ is installed: `python --version`
2. Verify dependencies: `pip install -r requirements.txt`
3. Check port availability: the default port is 8501
4. Ensure `data/` directory exists (created automatically, but check permissions)

### API key errors

- **"AI triage is unavailable because its credentials are not configured correctly"**: The `OPENAI_API_KEY` in `.env` is invalid or expired. Regenerate at [platform.openai.com](https://platform.openai.com).
- **"AI triage is temporarily unavailable"**: OpenAI rate limit or timeout. The service retries twice automatically. Wait and try again.
- **Demo mode active when you expected live mode**: Ensure `SENTINEL_DEMO_MODE=false` and `OPENAI_API_KEY` is set in `.env`.

### Database issues

- **"Database operation failed"**: The SQLite file may be locked by another process, or the `data/` directory is read-only. Check filesystem permissions.
- **Database corruption**: Stop the application, back up the `.db` file, delete it, and restart. The schema will be recreated (data will be lost).
- **Migration**: The application automatically runs additive schema migrations on startup for backward compatibility.

### PDF export

- **"PDF export is unavailable because ReportLab is not installed"**: Run `pip install reportlab`.

## Backups and data retention

- **Backups:** SQLite databases can be backed up by copying the `.db` file while the application is stopped, or by using `sqlite3 .backup` while running (WAL mode supports concurrent reads).
- **Retention:** There is no automatic data retention or purging policy. All incidents are retained indefinitely. Implement organizational data retention policies as needed.
- **Demo data cleanup:** Use Settings → "Reset demo records" to remove only `is_demo=True` records.
