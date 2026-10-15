"""On-page incident selection for Details/Triage (regression tests).

Uses Streamlit's AppTest harness to execute the real app against isolated
temporary databases.
"""
from pathlib import Path

from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory
from sentinel.schemas.incident import CreateIncident


def _open_app(monkeypatch, tmp_path, page, *, read_only=False, count=3):
    monkeypatch.setenv("SENTINEL_DATABASE_PATH", str(tmp_path / "sentinel.db"))
    if read_only:
        monkeypatch.setenv("SENTINEL_READ_ONLY", "true")
    repository = IncidentRepository(tmp_path / "sentinel.db")
    repository.initialize()
    for index in range(count):
        repository.create_incident(CreateIncident(
            title=f"Case {index}", description=f"Persisted description {index}.",
            category=IncidentCategory.HARMFUL_OUTPUT))
    from streamlit.testing.v1 import AppTest
    app_path = Path(__file__).resolve().parent.parent / "app.py"
    at = AppTest.from_file(app_path, default_timeout=60)
    at.session_state["active_page"] = page
    at.run()
    return at


def _page_text(at) -> str:
    parts = [str(item.value) for item in at.markdown]
    parts += [str(item.value) for item in at.get("text")]
    parts += [str(item.value) for item in at.caption]
    return "\n".join(parts)


def test_details_selector_lists_persisted_incidents(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "Incident Details")
    assert len(at.exception) == 0
    picker = at.selectbox(key="details_incident_picker")
    assert len(picker.options) == 3
    # Newest-first ordering: first render auto-selects and persists the key.
    assert at.session_state["selected_incident_id"] == "INC-2026-0003"
    text = _page_text(at)
    assert "Case 2" in text
    assert "Persisted description 2" in text


def test_details_changing_selection_refreshes_page(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "Incident Details")
    at.selectbox(key="details_incident_picker").select("INC-2026-0001 — Case 0").run()
    assert len(at.exception) == 0
    assert at.session_state["selected_incident_id"] == "INC-2026-0001"
    text = _page_text(at)
    assert "Case 0" in text
    assert "Persisted description 0" in text


def test_triage_selector_and_summary(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "AI Triage")
    assert len(at.exception) == 0
    picker = at.selectbox(key="triage_incident_picker")
    assert len(picker.options) == 3
    text = _page_text(at)
    assert "Case 2" in text
    assert "Incident status" in text


def test_triage_changing_selection_refreshes_page(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "AI Triage")
    at.selectbox(key="triage_incident_picker").select("INC-2026-0001 — Case 0").run()
    assert len(at.exception) == 0
    assert at.session_state["selected_incident_id"] == "INC-2026-0001"
    assert "Case 0" in _page_text(at)


def test_details_empty_state_offers_report_navigation(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "Incident Details", count=0)
    assert len(at.exception) == 0
    assert len(at.get("selectbox")) == 0
    buttons = at.get("button")
    report_buttons = [item for item in buttons if "Report an incident" in str(item.proto.label)]
    assert report_buttons
    report_buttons[0].click().run()
    assert at.session_state["active_page"] == "Report an Incident"


def test_triage_empty_state_offers_report_navigation(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "AI Triage", count=0)
    assert len(at.exception) == 0
    assert len(at.get("selectbox")) == 0
    buttons = [item for item in at.get("button") if "Report an incident" in str(item.proto.label)]
    assert buttons


def test_navigation_preserves_valid_selection(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "Incident Details")
    at.selectbox(key="details_incident_picker").select("INC-2026-0002 — Case 1").run()
    selected = at.session_state["selected_incident_id"]
    at.session_state["active_page"] = "Overview"
    at.run()
    at.session_state["active_page"] = "Incident Details"
    at.run()
    assert len(at.exception) == 0
    assert at.session_state["selected_incident_id"] == selected
    assert "Case 1" in _page_text(at)


def test_stale_selection_recovers(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "Incident Details")
    at.session_state["selected_incident_id"] = "INC-2026-9999"
    at.run()
    assert len(at.exception) == 0
    # Stale id cleared; picker still available for recovery.
    assert at.session_state.get("selected_incident_id") in (None, "INC-2026-0003")
    assert at.selectbox(key="details_incident_picker")


def test_read_only_disables_triage_action(monkeypatch, tmp_path):
    at = _open_app(monkeypatch, tmp_path, "AI Triage", read_only=True)
    assert len(at.exception) == 0
    triage_buttons = [item for item in at.get("button") if "triage" in str(item.proto.label).lower()]
    assert triage_buttons
    assert triage_buttons[0].proto.disabled is True
