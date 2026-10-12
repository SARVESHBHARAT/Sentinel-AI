import streamlit as st

from sentinel.config import Settings
from sentinel.database.repositories import IncidentRepository


def render(settings: Settings, repository: IncidentRepository) -> None:
    st.title("Settings")
    st.markdown('<p class="sentinel-subtitle">Configuration status and safe local maintenance controls.</p>', unsafe_allow_html=True)
    left, right = st.columns(2)
    left.subheader("AI configuration")
    left.write(f"Model: `{settings.openai_model}`")
    left.write("API key: configured" if settings.openai_api_key else "API key: not configured")
    if settings.effective_demo_mode:
        left.warning("Demo mode is active. Any future assessment must be labelled as demo output.")
    else:
        left.success("Live-model configuration is available. Human review remains required.")
    right.subheader("Storage")
    right.write(f"Database: `{settings.database_path}`")
    right.write("SQLite foreign-key constraints are enabled for each connection.")
    st.divider()
    st.subheader("Demo data maintenance")
    st.caption("Only records explicitly marked as demo data are removed. Real user reports are not affected.")
    confirmation = st.checkbox("I understand this removes only demo records.", key="confirm_demo_reset")
    if st.button("Reset demo records", disabled=not confirmation, key="reset_demo_records"):
        try:
            removed = repository.reset_demo_incidents()
            st.success(f"Removed {removed} demo incident record(s).")
        except Exception:
            st.error("Demo records could not be reset. No confirmation of deletion is available.")
