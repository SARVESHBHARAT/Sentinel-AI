import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """<style>
        .stApp { background: #f6f7fb; color: #18223a; }
        h1, h2, h3 { color: #102044; letter-spacing: -0.02em; }
        .sentinel-subtitle { color: #5b6578; margin-top: -0.6rem; }
        .sentinel-badge { display:inline-block; border-radius:999px; padding:0.16rem 0.55rem; font-size:0.78rem; font-weight:600; }
        .status-submitted { background:#e9eef7; color:#334155; }
        .status-under-review { background:#e7edff; color:#3344a3; }
        .status-action-required { background:#fff4db; color:#8a5900; }
        .status-resolved { background:#e5f5ed; color:#17613c; }
        .status-closed { background:#e9edf1; color:#4c596b; }
        .severity-low { background:#e5f5ed; color:#17613c; }
        .severity-medium { background:#fff4db; color:#8a5900; }
        .severity-high { background:#fee9e5; color:#9f2d1f; }
        .severity-critical { background:#f6dfe5; color:#82172d; }
        .severity-unassessed { background:#eef1f5; color:#536174; }
        </style>""",
        unsafe_allow_html=True,
    )
