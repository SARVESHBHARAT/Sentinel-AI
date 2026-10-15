import html
import re
from collections.abc import Callable

import streamlit as st

from sentinel.database.repositories import IncidentRepository
from sentinel.domain.enums import IncidentCategory, IncidentStatus
from sentinel.schemas.incident import Incident
from sentinel.time_utils import display_local

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<])")


def _sanitize_for_selectbox(text: str) -> str:
    """Replace Markdown-special characters with safe Unicode lookalikes.

    Streamlit's selectbox renders options as Markdown, so characters like
    ``[``, ``]``, ``--``, ``*``, etc. would be interpreted as Markdown syntax.
    This function replaces them with visually similar Unicode characters that
    render as plain text, avoiding both Markdown interpretation and visible
    escape backslashes.
    """
    replacements = {
        "[": "\uFF3B",   # FULLWIDTH LEFT SQUARE BRACKET ［
        "]": "\uFF3D",   # FULLWIDTH RIGHT SQUARE BRACKET ］
        "--": "\u2014",  # EM DASH —
        "`": "\uFF40",   # FULLWIDTH GRAVE ACCENT ｀
        "*": "\uFF0A",   # FULLWIDTH ASTERISK ＊
        "_": "\uFF3F",   # FULLWIDTH LOW LINE ＿
        "{": "\uFF5B",   # FULLWIDTH LEFT CURLY BRACKET ｛
        "}": "\uFF5D",   # FULLWIDTH RIGHT CURLY BRACKET ｝
        "(": "\uFF08",   # FULLWIDTH LEFT PARENTHESIS （
        ")": "\uFF09",   # FULLWIDTH RIGHT PARENTHESIS ）
        "#": "\uFF03",   # FULLWIDTH NUMBER SIGN ＃
        "+": "\uFF0B",   # FULLWIDTH PLUS SIGN ＋
        ".": "\uFF0E",   # FULLWIDTH FULL STOP ．
        "!": "\uFF01",   # FULLWIDTH EXCLAMATION MARK ！
        "|": "\uFF5C",   # FULLWIDTH VERTICAL LINE ｜
        ">": "\uFF1E",   # FULLWIDTH GREATER-THAN SIGN 〉
        "<": "\uFF1C",   # FULLWIDTH LESS-THAN SIGN 〈
        "~": "\uFF5E",   # FULLWIDTH TILDE ～
        "\\": "\uFF3C",  # FULLWIDTH REVERSE SOLIDUS ＼
    }
    result = text
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    return result


#: Characters with structural meaning in GitHub-flavored Markdown. Escaping
#: them renders untrusted text literally instead of letting reporter-supplied
#: content become headings, links, images, or inline HTML.
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<])")


def escape_markdown(value: object | None) -> str:
    """Neutralise Markdown control characters in untrusted text.

    Streamlit renders ``st.write``/``st.markdown``/``st.subheader`` input as
    Markdown, so a report title, note author, or AI suggestion containing e.g.
    ``![x](https://example.invalid/track.png)`` would otherwise load remote
    content in the reviewer's browser. Escaping keeps the text legible while
    removing that channel.
    """
    if value is None:
        return ""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", str(value))


def escape_html(value: object | None) -> str:
    """Escape untrusted text for raw-HTML contexts (``unsafe_allow_html=True``).

    Unlike :func:`escape_markdown`, this preserves visible punctuation such as
    ``[DEMO]`` and ``--``: Markdown escapes would otherwise render as literal
    backslashes inside an HTML block, because the block is passed through as
    HTML rather than parsed as Markdown. ``html.escape`` keeps ``<``/``>``/``&``
    safe while leaving legitimate backslashes, brackets, and hyphens intact.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def label(value: object | None) -> str:
    if value is None:
        return "Not assessed"
    raw = getattr(value, "value", str(value))
    return raw.replace("_", " ").title()


def badge(value: object | None, kind: str) -> None:
    raw = getattr(value, "value", "unassessed") if value else "unassessed"
    safe_kind = html.escape(str(kind))
    safe_raw = html.escape(str(raw).replace("_", "-"))
    safe_label = html.escape(label(value))
    st.markdown(f'<span class="sentinel-badge {safe_kind}-{safe_raw}">{safe_label}</span>', unsafe_allow_html=True)


def incident_rows(incidents: list[Incident]) -> list[dict[str, str]]:
    return [
        {
            "Incident ID": item.incident_id,
            "Title": item.title,
            "Category": label(item.category),
            "Severity": label(item.severity),
            "Status": label(item.status),
            "Reported": item.report_date.isoformat(),
            "Updated": display_local(item.updated_at),
            "Source": "Demo" if item.is_demo else "Reported",
        }
        for item in incidents
    ]


def choose_incident(incidents: list[Incident], key: str, on_select: Callable[[str], None]) -> None:
    if not incidents:
        return
    selected = st.selectbox("Open incident", incidents, format_func=lambda item: f"{item.incident_id} — {item.title}", key=key)
    st.button("View incident", key=f"{key}_open", type="secondary", on_click=on_select, args=(selected.incident_id,))


def category_options(include_unknown: bool = False) -> list[str]:
    values = [item.value for item in IncidentCategory]
    return (["unknown"] if include_unknown else []) + values


def enum_label(value: str) -> str:
    return "I don't know" if value == "unknown" else label(value)


def safe_error(action: str, error: Exception) -> None:
    st.error(f"Unable to {action}. Your information was not changed. Please review the form and try again.")


def status_options(status: IncidentStatus) -> list[IncidentStatus]:
    from sentinel.domain.lifecycle import ALLOWED_TRANSITIONS
    return sorted(ALLOWED_TRANSITIONS[status], key=lambda item: item.value)


def fetch_incident_options(repository: IncidentRepository, limit: int = 500) -> list[tuple[str, str]]:
    """Return (label, incident_id) pairs of persisted incidents for on-page pickers.

    Labels are sanitized so that Markdown-special characters in titles do not
    trigger Markdown rendering inside Streamlit's selectbox.
    """
    incidents, _ = repository.search_incidents(limit=limit)
    return [
        (f"{item.incident_id} \u2014 {_sanitize_for_selectbox(item.title)}", item.incident_id)
        for item in incidents
    ]


def incident_picker(repository: IncidentRepository, *, key: str, label: str = "Selected incident") -> str | None:
    """On-page incident selector backed by persisted records.

    Keeps ``selected_incident_id`` as the single source of truth: defaults to
    the current session selection when it is still in the list, otherwise to
    the first incident. Returns the chosen incident id (the caller persists it
    and reruns when it changed). Returns None when no incidents exist.
    """
    options = fetch_incident_options(repository)
    if not options:
        return None
    labels = [item[0] for item in options]
    mapping = dict(options)
    current = st.session_state.get("selected_incident_id")
    default = next((item for item in labels if mapping[item] == current), labels[0])
    choice = st.selectbox(label, labels, index=labels.index(default), key=key)
    return mapping[choice]
