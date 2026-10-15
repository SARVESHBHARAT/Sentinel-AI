"""Sentinel AI design system — tokens, global CSS, and shared presentation helpers.

Palette: deep black app background (#050505), sleek dark charcoal sidebar (#090909),
dark cards (#101010), elevated surfaces (#151515), subtle borders (#262626), soft-white
text, crisp neutral / cyan accents, semantic severity colors. All page-level
styling references these tokens; individual pages should use the helpers here
(``page_header``, ``section_label``, ``style_chart``) instead of raw CSS.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens (single source of truth for Python-side rendering, e.g. Plotly)
# ---------------------------------------------------------------------------
BACKGROUND = "#050505"
SIDEBAR = "#090909"
CARD = "#101010"
ELEVATED = "#151515"
BORDER = "#262626"
GRID = "#1A1A1A"
TEXT = "#F5F5F5"
MUTED = "#8A8A8A"
ACCENT = "#F5F5F5"
ACCENT_2 = "#38BDF8"

SEVERITY_COLORS: dict[str, str] = {
    "low": "#34D399",
    "medium": "#FBBF24",
    "high": "#F87171",
    "critical": "#FB7185",
    "not assessed": "#6B7280",
}

_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

_CSS = f"""
/* ============================ base ============================ */
html, body, [class*="css"] {{ font-family: {_FONT}; }}
.stApp {{ background: {BACKGROUND}; color: {TEXT}; }}
section[data-testid="stSidebar"] > div {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
[data-testid="stHeader"] {{ background: {BACKGROUND}; }}
[data-testid="stToolbar"] {{ visibility: hidden; }}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
.block-container {{ max-width: 1280px !important; padding: 2.2rem 2.6rem 4rem; }}
hr {{ border-color: {BORDER}; opacity: 1; }}
a {{ color: #E5E5E5; }}
::selection {{ background: rgba(255,255,255,.2); }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: #262626; border-radius: 6px; border: 2px solid {BACKGROUND}; }}
::-webkit-scrollbar-track {{ background: transparent; }}

/* ========================= typography ========================= */
h1, h2, h3 {{ color: {TEXT}; letter-spacing: -0.015em; }}
h1 {{ font-size: 1.75rem !important; font-weight: 650 !important; }}
h2 {{ font-size: 1.25rem !important; font-weight: 600 !important; }}
h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; }}
p {{ color: {TEXT}; }}
[data-testid="stMarkdownContainer"] p {{ color: {TEXT}; font-size: 0.95rem; line-height: 1.55; }}
.sentinel-subtitle {{ color: {MUTED} !important; margin-top: -0.4rem; margin-bottom: 1.2rem; font-size: 0.95rem; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {MUTED} !important; font-size: 0.8rem !important; }}

/* ======================= page headers ========================= */
.sp-pagehead {{ margin-bottom: 1.6rem; }}
.sp-eyebrow {{ font-size: 0.7rem; font-weight: 700; letter-spacing: 0.18em; color: {MUTED};
    text-transform: uppercase; margin-bottom: 0.35rem; }}
.sp-title {{ font-size: 1.8rem; font-weight: 680; color: {TEXT}; letter-spacing: -0.02em; line-height: 1.2; margin: 0; }}
.sp-sub {{ color: {MUTED}; font-size: 0.95rem; margin: 0.45rem 0 0; max-width: 72ch; }}
.sp-section {{ font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
    color: {MUTED}; margin: 1.9rem 0 0.7rem; }}
.sp-case-title {{ font-size: 1.45rem; font-weight: 650; color: {TEXT}; letter-spacing: -0.01em;
    line-height: 1.3; margin: 0.2rem 0 0.8rem; }}
.sp-resultline {{ color: {MUTED}; font-size: 0.85rem; margin: 0.2rem 0 0.6rem; }}

/* =========================== badges =========================== */
.sentinel-badge {{ display: inline-flex; align-items: center; gap: 0.35rem; border-radius: 999px;
    padding: 0.2rem 0.62rem; font-size: 0.74rem; font-weight: 650; letter-spacing: 0.02em;
    border: 1px solid transparent; white-space: nowrap; }}
.sentinel-badge::before {{ content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.9; }}
.status-submitted {{ background: rgba(148,163,184,.12); color: #B4BCCB; border-color: rgba(148,163,184,.28); }}
.status-under-review {{ background: rgba(96,165,250,.12); color: #93BDFB; border-color: rgba(96,165,250,.3); }}
.status-action-required {{ background: rgba(251,191,36,.12); color: #F6C955; border-color: rgba(251,191,36,.3); }}
.status-resolved {{ background: rgba(52,211,153,.12); color: #6EE7B7; border-color: rgba(52,211,153,.3); }}
.status-closed {{ background: rgba(107,114,128,.16); color: #9CA3AF; border-color: rgba(107,114,128,.3); }}
.severity-low {{ background: rgba(52,211,153,.12); color: #6EE7B7; border-color: rgba(52,211,153,.3); }}
.severity-medium {{ background: rgba(251,191,36,.12); color: #F6C955; border-color: rgba(251,191,36,.3); }}
.severity-high {{ background: rgba(248,113,113,.13); color: #FCA5A1; border-color: rgba(248,113,113,.32); }}
.severity-critical {{ background: rgba(251,113,133,.15); color: #FDA4AF; border-color: rgba(251,113,133,.36); }}
.severity-unassessed {{ background: rgba(107,114,128,.16); color: #9CA3AF; border-color: rgba(107,114,128,.3); }}
.verification-reported {{ background: rgba(148,163,184,.12); color: #B4BCCB; border-color: rgba(148,163,184,.28); }}
.verification-ai-assessed {{ background: rgba(255,255,255,.08); color: #E4E4E7; border-color: rgba(255,255,255,.16); }}
.verification-human-reviewed {{ background: rgba(56,189,248,.12); color: #7DD3FC; border-color: rgba(56,189,248,.3); }}
.verification-verified {{ background: rgba(52,211,153,.12); color: #6EE7B7; border-color: rgba(52,211,153,.3); }}
.verification-disputed {{ background: rgba(251,146,60,.13); color: #FDBA74; border-color: rgba(251,146,60,.32); }}
.verification-unverified {{ background: rgba(107,114,128,.16); color: #9CA3AF; border-color: rgba(107,114,128,.3); }}
.sp-pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 0.22rem 0.65rem;
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
.sp-pill-demo {{ background: rgba(245,158,11,.12); color: #FBBF24; border: 1px solid rgba(245,158,11,.3); }}
.sp-pill-readonly {{ background: rgba(251,191,36,.13); color: #F6C955; border: 1px solid rgba(251,191,36,.34); }}

/* ========================= sidebar ============================ */
.sp-brand {{ display: flex; align-items: center; gap: 0.7rem; padding: 0.4rem 0.2rem 0.2rem; margin-bottom: 0.2rem; }}
.sp-brand-mark {{ width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
    background: #181818; border: 1px solid #333333; color: #FFFFFF; font-weight: 800; font-size: 1.05rem;
    box-shadow: 0 4px 16px rgba(0,0,0,.6); }}
.sp-brand-name {{ color: {TEXT}; font-size: 1.02rem; font-weight: 700; letter-spacing: 0.04em; line-height: 1.1; }}
.sp-brand-sub {{ color: {MUTED}; font-size: 0.72rem; letter-spacing: 0.04em; margin-top: 0.1rem; }}
.sp-side-note {{ color: {MUTED}; font-size: 0.72rem; line-height: 1.45; margin-top: 0.4rem; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    border-radius: 8px; padding: 0.32rem 0.6rem; margin-bottom: 2px;
    color: {MUTED}; font-weight: 500; transition: background .15s, color .15s; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{ background: rgba(255,255,255,.04); color: {TEXT}; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background: #1A1A1A;
    color: {TEXT}; box-shadow: inset 2px 0 0 #F5F5F5; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{ color: {TEXT} !important; font-weight: 600; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label p {{ color: {MUTED}; font-size: 0.9rem; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] {{ margin-bottom: 0.25rem; }}

/* ====================== buttons ============================== */
[data-testid="stButton"] button {{
    border-radius: 9px; border: 1px solid {BORDER}; background: {ELEVATED}; color: {TEXT};
    font-weight: 600; font-size: 0.88rem; transition: all .15s; }}
[data-testid="stButton"] button:hover {{ border-color: #383838; background: #1C1C1C; color: {TEXT}; }}
[data-testid="stButton"] button:focus-visible {{ outline: 2px solid #A1A1AA; outline-offset: 2px; }}
[data-testid="stButton"] button[kind="primary"] {{
    background: #F5F5F5; border-color: #F5F5F5; color: #0A0A0A; font-weight: 650;
    box-shadow: 0 2px 10px rgba(0,0,0,.5); }}
[data-testid="stButton"] button[kind="primary"]:hover {{ background: #E5E5E5; color: #000000; border-color: #E5E5E5; }}
[data-testid="stDownloadButton"] button {{
    border-radius: 9px; border: 1px solid {BORDER}; background: {ELEVATED}; color: {TEXT}; font-weight: 600; }}
[data-testid="stDownloadButton"] button:hover {{ border-color: #383838; background: #1C1C1C; }}

/* ==================== inputs & forms ========================= */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stDateInput"] input {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 9px; color: {TEXT}; }}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus,
[data-testid="stDateInput"] input:focus, [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
    border-color: #52525B; box-shadow: 0 0 0 3px rgba(255,255,255,.08); }}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div, [data-testid="stSelectbox"] [data-baseweb="input"] {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 9px; }}
[data-testid="stForm"] {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; padding: 1.6rem 1.8rem 1.4rem; }}
[data-testid="stExpander"] details {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ font-weight: 600; color: {TEXT}; }}
label {{ color: {TEXT} !important; font-size: 0.86rem !important; }}
[data-testid="stFormSubmitButton"] button {{ width: 100%; }}

/* ======================= tabs ================================ */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{ gap: 4px; background: transparent; border-bottom: 1px solid {BORDER}; }}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent; border-radius: 9px 9px 0 0; color: {MUTED}; font-weight: 600; font-size: 0.88rem;
    padding: 0.55rem 0.9rem; }}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {{ color: {TEXT}; }}
[data-testid="stTabs"] [aria-selected="true"] {{ background: #161616; color: {TEXT};
    box-shadow: inset 0 -2px 0 #F5F5F5; }}
[data-testid="stTabs"] [data-baseweb="tab-border"], [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ display: none; }}

/* ================ metrics, charts, tables ==================== */
[data-testid="stMetric"] {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 1rem 1.1rem; }}
[data-testid="stMetric"] label {{ color: {MUTED} !important; font-size: 0.72rem !important;
    text-transform: uppercase; letter-spacing: 0.08em; }}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: {TEXT}; font-weight: 680; font-size: 1.6rem; }}
[data-testid="stPlotlyChart"], [data-testid="stArrowVegaChart"] {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 0.6rem 0.4rem 0.2rem; }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
    border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}
[data-testid="stCode"], pre {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 9px; color: {TEXT}; }}

/* ======================= alerts ============================== */
[data-testid="stAlert"], .stAlert {{ border-radius: 10px; border: 1px solid {BORDER}; background: {CARD}; }}

/* ======================= misc ================================ */
[data-testid="stSpinner"] {{ color: {ACCENT}; }}
[data-testid="stImage"] img {{ border-radius: 10px; }}
"""


def apply_theme() -> None:
    """Inject the global design-system stylesheet (call once per run, before routing)."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, subtitle: str | None = None) -> None:
    """Premium page header: small uppercase eyebrow, strong title, muted subtitle."""
    sub_html = f'<p class="sp-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="sp-pagehead"><div class="sp-eyebrow">{eyebrow}</div>'
        f'<div class="sp-title">{title}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str, container=None) -> None:
    """Small uppercase section label used to group content within a page."""
    (container or st).markdown(f'<div class="sp-section">{text}</div>', unsafe_allow_html=True)


def result_line(text: str) -> None:
    """Muted supporting line (result counts, scope notes)."""
    st.markdown(f'<div class="sp-resultline">{text}</div>', unsafe_allow_html=True)


def style_chart(fig, *, title: str | None = None, y_title: str | None = None, height: int = 320):
    """Apply the shared dark Plotly layout so every chart matches the design system."""
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=54 if title else 24, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=12, color=MUTED),
        title=dict(text=title, font=dict(color=TEXT, size=15), x=0.01, xanchor="left", y=0.98),
        hoverlabel=dict(bgcolor=ELEVATED, font=dict(color=TEXT), bordercolor=BORDER),
        xaxis=dict(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED), title=y_title or ""),
    )
    return fig


def severity_bar_colors(values: dict[str, int]) -> list[str]:
    """Semantic per-bar colors for severity distributions (semantic use only)."""
    return [SEVERITY_COLORS.get(key.lower(), "#6B7280") for key in values]



