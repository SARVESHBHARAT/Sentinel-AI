import streamlit as st

from sentinel.config import Settings
from sentinel.database.repositories import IncidentRepository
from sentinel.ui.styles import page_header, section_label


def render(settings: Settings, repository: IncidentRepository) -> None:
    page_header("System", "Settings",
                "Configuration status and safe local maintenance controls. Secrets are never displayed.")
    left, right = st.columns(2)
    section_label("AI configuration", left)
    left.write(f"Model: `{settings.openai_model}`")
    left.write("API key: configured" if settings.openai_api_key else "API key: not configured")
    if settings.effective_demo_mode:
        left.warning("Demo mode is active. Any future assessment must be labelled as demo output.")
    else:
        left.success("Live-model configuration is available. Human review remains required.")
    section_label("Storage", right)
    right.write(f"Database: `{settings.database_path}`")
    right.write("SQLite foreign-key constraints are enabled for each connection.")
    st.divider()
    section_label("Demo data maintenance")
    st.caption("Only records explicitly marked as demo data are removed. Real user reports are not affected.")
    confirmation = st.checkbox("I understand this removes only demo records.", key="confirm_demo_reset")
    if st.button("Reset demo records", disabled=not confirmation, key="reset_demo_records"):
        try:
            removed = repository.reset_demo_incidents()
            st.success(f"Removed {removed} demo incident record(s).")
        except Exception:
            st.error("Demo records could not be reset. No confirmation of deletion is available.")
    st.divider()
    section_label("Synthetic demo dataset")
    st.caption("Populate fictional demo incidents across several providers, models, and versions so the AI Model "
               "Observatory has data. All records are marked SYNTHETIC DEMO DATA. Seeding is idempotent: "
               "re-running adds nothing new.")
    if settings.read_only:
        st.caption("Demo seeding is disabled in read-only mode.")
    elif st.button("Seed synthetic demo dataset", key="seed_demo_dataset"):
        try:
            from sentinel.demo_seed import seed_demo_dataset
            result = seed_demo_dataset(repository)
            if result.created:
                st.success(f"Seeded {result.created} synthetic demo incident(s) "
                           f"({result.skipped} already present). Open Model Intelligence to explore.")
            else:
                st.info(f"Demo dataset already present ({result.skipped} records). Nothing new was created.")
        except Exception:
            st.error("Demo seeding failed. No confirmation is available; existing data was not modified.")
