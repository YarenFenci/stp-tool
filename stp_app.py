"""
STP Manual Analyzer — BiP QA priority assignment.
Scenario input with Actual/Expected Result → priority with reasoning.
"""

import sys
import re
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from stp_engine import (
    decide_priority,
    detect_device_os_scope,
    PRIORITY_ORDER,
    REASON_MAP,
    GATING_TERMS, HIGH_TERMS, MEDIUM_TERMS,
    LOW_COSMETIC_TERMS, HARD_CRASH_TERMS, FREEZE_TERMS,
    FREQ_OPTIONS,
)

# ─────────────────────────────────────────────
# Priority metadata
# ─────────────────────────────────────────────
PRIORITY_META = {
    "Gating": {
        "color":  "#E53935",
        "bg":     "#FFF0F0",
        "border": "#FFCDD2",
        "icon":   "🔴",
        "label":  "GATING",
        "desc":   "Blocks release — core function broken or reproducible crash. Must fix before shipping.",
    },
    "High": {
        "color":  "#FB8C00",
        "bg":     "#FFF8F0",
        "border": "#FFE0B2",
        "icon":   "🟠",
        "label":  "HIGH",
        "desc":   "Important feature affected — fix within 2 weeks. PO/QA Lead decision required to ship.",
    },
    "Medium": {
        "color":  "#1E88E5",
        "bg":     "#F0F6FF",
        "border": "#BBDEFB",
        "icon":   "🔵",
        "label":  "MEDIUM",
        "desc":   "Secondary UX issue — workaround exists, fix within 6 weeks.",
    },
    "Low": {
        "color":  "#43A047",
        "bg":     "#F0FFF0",
        "border": "#C8E6C9",
        "icon":   "🟢",
        "label":  "LOW",
        "desc":   "Cosmetic / minor edge case — no functional impact.",
    },
}

SCOPE_META = {
    "device":              {"label": "Device Specific",       "color": "#FF6F00"},
    "os_version":          {"label": "OS Version Specific",   "color": "#7B1FA2"},
    "chipset":             {"label": "Chipset Specific",      "color": "#C62828"},
    "single_device_repro": {"label": "Single Device Repro",   "color": "#AD1457"},
    "manual":              {"label": "Device / OS Scope",     "color": "#E65100"},
}

FREQ_META = {
    "always":       {"icon": "🔁", "color": "#E53935", "label": "Always"},
    "frequently":   {"icon": "🔄", "color": "#FB8C00", "label": "Frequently"},
    "occasionally": {"icon": "🔃", "color": "#1E88E5", "label": "Occasionally"},
    "rarely":       {"icon": "🔀", "color": "#43A047", "label": "Rarely"},
    "once":         {"icon": "1️⃣",  "color": "#78909C", "label": "Once"},
}

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []


# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: #0A0E1A; }

    .stp-header { padding: 2.5rem 0 1.5rem 0; margin-bottom: 0.5rem; }
    .stp-title {
        font-family: 'Syne', sans-serif; font-size: 2.4rem; font-weight: 800;
        color: #F0F4FF; letter-spacing: -0.03em; line-height: 1.1; margin: 0;
    }
    .stp-title span { color: #4FC3F7; }
    .stp-subtitle { font-size: 0.88rem; color: #6B7A99; margin-top: 0.4rem; letter-spacing: 0.02em; }
    .stp-divider {
        height: 1px;
        background: linear-gradient(90deg, #4FC3F7 0%, #1E2761 60%, transparent 100%);
        margin: 1rem 0 1.5rem 0;
    }

    .form-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #4FC3F7; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.4rem;
    }
    .section-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 600;
        color: #3A6080; letter-spacing: 0.1em; text-transform: uppercase;
        margin: 0.8rem 0 0.3rem 0;
    }

    .stTextInput input, .stTextArea textarea {
        background: #0D1321 !important; border: 1px solid #1E2761 !important;
        border-radius: 8px !important; color: #E8EEFF !important;
        font-family: 'DM Sans', sans-serif !important; font-size: 0.88rem !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #4FC3F7 !important; box-shadow: 0 0 0 2px rgba(79,195,247,0.12) !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #3A4A6B !important; }

    /* Selectbox styling */
    .stSelectbox > div > div {
        background: #0D1321 !important;
        border: 1px solid #1E2761 !important;
        border-radius: 8px !important;
        color: #E8EEFF !important;
    }

    /* Adjustment note box */
    .adjust-box {
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-top: 0.8rem;
        border: 1px solid;
        font-size: 0.82rem;
        line-height: 1.6;
    }
    .adjust-box-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
        font-weight: 600;
    }

    /* Freq badge */
    .freq-badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 3px 10px; border-radius: 12px; margin-top: 0.6rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 600;
    }

    .stButton > button {
        background: linear-gradient(135deg, #1565C0, #0D47A1) !important;
        color: #E8F5FF !important; border: none !important; border-radius: 8px !important;
        font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
        font-size: 0.9rem !important; letter-spacing: 0.04em !important;
        padding: 0.6rem 1.5rem !important; width: 100% !important; transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1976D2, #1565C0) !important;
        transform: translateY(-1px) !important; box-shadow: 0 4px 20px rgba(21,101,192,0.4) !important;
    }

    .result-card { border-radius: 12px; padding: 1.6rem; margin-bottom: 1rem; border: 1px solid; }
    .result-priority-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 600;
        letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 0.3rem;
    }
    .result-priority-value {
        font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800;
        letter-spacing: -0.02em; line-height: 1; margin-bottom: 0.5rem;
    }
    .result-desc { font-size: 0.82rem; opacity: 0.75; line-height: 1.4; }

    .device-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 600;
        letter-spacing: 0.06em; margin-top: 0.8rem;
    }

    /* Actual/Expected result display */
    .result-comparison {
        display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 1rem;
    }
    .result-box {
        background: #0D1321; border: 1px solid #1E2761; border-radius: 8px; padding: 0.8rem 1rem;
    }
    .result-box-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; letter-spacing: 0.1em;
        text-transform: uppercase; margin-bottom: 0.3rem;
    }
    .result-box-text { font-size: 0.82rem; color: #C8D4F0; line-height: 1.5; }

    .reason-box {
        background: #0D1321; border: 1px solid #1E2761; border-left: 3px solid #4FC3F7;
        border-radius: 8px; padding: 1rem 1.2rem; margin-top: 1rem;
    }
    .reason-title {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #4FC3F7;
        letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.5rem;
    }
    .reason-text { font-size: 0.85rem; color: #C8D4F0; line-height: 1.6; }

    .keyword-box {
        background: #0D1321; border: 1px solid #1E2761; border-radius: 8px;
        padding: 0.8rem 1.1rem; margin-top: 0.8rem;
    }
    .kw-chip {
        display: inline-block; background: #1A2340; border: 1px solid #2A3560;
        border-radius: 4px; padding: 2px 8px; font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem; color: #8BA7D9; margin: 2px 3px;
    }

    .hist-row {
        display: flex; align-items: center; gap: 10px; padding: 0.6rem 0.8rem;
        border-radius: 6px; background: #111827; border: 1px solid #1A2340;
        margin-bottom: 6px; font-size: 0.82rem;
    }
    .hist-key { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #4FC3F7; min-width: 36px; }
    .hist-summary { flex: 1; color: #A0B0CC; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .hist-badge {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700;
        padding: 2px 9px; border-radius: 4px; color: #fff; white-space: nowrap;
    }
    .hist-device { font-size: 0.68rem; color: #FF6F00; font-family: 'JetBrains Mono', monospace; }

    section[data-testid="stSidebar"] { background: #0D1321 !important; border-right: 1px solid #1E2761 !important; }
    section[data-testid="stSidebar"] * { color: #8BA7D9 !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Keyword hit detection
# ─────────────────────────────────────────────
def find_hit_keywords(text: str, priority: str) -> List[str]:
    t = text.lower()
    if priority == "Gating":
        pool = GATING_TERMS + HARD_CRASH_TERMS
    elif priority == "High":
        pool = HIGH_TERMS
    elif priority == "Medium":
        pool = MEDIUM_TERMS
    else:
        pool = LOW_COSMETIC_TERMS
    return [kw for kw in pool if kw and kw in t][:8]


# ─────────────────────────────────────────────
# Render result
# ─────────────────────────────────────────────
def render_result(summary: str, steps: str, actual: str, expected: str,
                  freq: str, device_scope: str):
    priority, is_scoped, scope_type, scope_detail, reason, adjusted_note = decide_priority(
        "",
        expected_result=expected,
        summary=summary,
        steps=steps,
        reproduce_frequency=freq,
        device_scope=device_scope,
    )
    meta  = PRIORITY_META[priority]
    fmeta = FREQ_META.get(freq, FREQ_META["always"])
    hits  = find_hit_keywords(
        (summary + " " + steps + " " + actual + " " + expected).lower(), priority
    )

    # ── Result card ──────────────────────────────────────────
    scope_html = ""
    if is_scoped:
        sc = SCOPE_META.get(scope_type, SCOPE_META["manual"])
        scope_html = f"""
        <div class="device-badge" style="
            background:{sc['color']}22;
            border:1px solid {sc['color']}66;
            color:{sc['color']};
        ">
            ⚠ {sc['label']}: {scope_detail}
        </div>"""

    freq_html = f"""
    <div class="freq-badge" style="
        background:{fmeta['color']}22;
        border:1px solid {fmeta['color']}55;
        color:{fmeta['color']};
    ">
        {fmeta['icon']} {fmeta['label']}
    </div>"""

    st.markdown(f"""
    <div class="result-card" style="background:{meta['bg']};border-color:{meta['border']};">
        <div class="result-priority-label" style="color:{meta['color']}">STP PRIORITY</div>
        <div class="result-priority-value" style="color:{meta['color']}">{meta['icon']} {meta['label']}</div>
        <div class="result-desc" style="color:{meta['color']}">{meta['desc']}</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:0.5rem">
            {freq_html}
            {scope_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Adjustment note ──────────────────────────────────────
    if adjusted_note.strip():
        st.markdown(f"""
        <div class="adjust-box" style="
            background:#0D1B2A; border-color:#1E3A5F;
        ">
            <div class="adjust-box-label" style="color:#4FC3F7">Priority Adjustments Applied</div>
            <div style="color:#A8C8E8">{adjusted_note}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Actual vs Expected ───────────────────────────────────
    if actual.strip() or expected.strip():
        actual_html   = actual.strip()   or "<em style='opacity:0.4'>Not specified</em>"
        expected_html = expected.strip() or "<em style='opacity:0.4'>Not specified</em>"
        st.markdown(f"""
        <div class="result-comparison">
            <div class="result-box">
                <div class="result-box-label" style="color:#E53935">🔴 Actual Result</div>
                <div class="result-box-text">{actual_html}</div>
            </div>
            <div class="result-box">
                <div class="result-box-label" style="color:#43A047">🟢 Expected Result</div>
                <div class="result-box-text">{expected_html}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Reason ───────────────────────────────────────────────
    st.markdown(f"""
    <div class="reason-box">
        <div class="reason-title">Why this priority?</div>
        <div class="reason-text">{reason}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Matched signals ──────────────────────────────────────
    if hits:
        chips = "".join(f'<span class="kw-chip">{kw}</span>' for kw in hits)
        st.markdown(f"""
        <div class="keyword-box">
            <div class="reason-title" style="margin-bottom:0.4rem">Matched signals</div>
            {chips}
        </div>
        """, unsafe_allow_html=True)

    return priority, is_scoped, scope_type, scope_detail, reason, adjusted_note


# ─────────────────────────────────────────────
# History
# ─────────────────────────────────────────────
def render_history():
    if not st.session_state.history:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="form-label" style="color:#6B7A99;margin-bottom:0.6rem">'
        f'SESSION HISTORY &nbsp;·&nbsp; {len(st.session_state.history)} scenarios</div>',
        unsafe_allow_html=True,
    )

    for i, entry in enumerate(reversed(st.session_state.history)):
        meta     = PRIORITY_META[entry["priority"]]
        fm       = FREQ_META.get(entry.get("freq", "always"), FREQ_META["always"])
        dev_html = (
            f'<span class="hist-device">📱 {entry["scope_detail"]}</span>'
            if entry["is_scoped"] else ""
        )
        freq_html = (
            f'<span style="font-size:0.68rem;color:{fm["color"]};'
            f'font-family:\'JetBrains Mono\',monospace">'
            f'{fm["icon"]} {fm["label"]}</span>'
        )
        st.markdown(f"""
        <div class="hist-row">
            <span class="hist-key">#{len(st.session_state.history)-i}</span>
            <span class="hist-summary">{entry['summary'][:60]}{'…' if len(entry['summary'])>60 else ''}</span>
            {freq_html}
            {dev_html}
            <span class="hist-badge" style="background:{meta['color']}">{meta['label']}</span>
        </div>
        """, unsafe_allow_html=True)

    if len(st.session_state.history) > 0:
        hist_df = pd.DataFrame(st.session_state.history)[[
            "summary", "steps", "actual", "expected",
            "freq", "device_scope",
            "priority", "is_scoped", "scope_type", "scope_detail",
            "reason", "adjusted_note"
        ]]
        hist_df.columns = [
            "Summary", "Steps", "Actual Result", "Expected Result",
            "Reproduce Frequency", "Device/OS Scope",
            "Priority", "Device Specific", "Scope Type", "Scope Detail",
            "Reason", "Adjustments Applied"
        ]
        st.download_button(
            "⬇ Export session as CSV",
            data=hist_df.to_csv(index=False).encode("utf-8"),
            file_name="stp_session.csv",
            mime="text/csv",
            key=f"dl_hist_{len(st.session_state.history)}",
        )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="STP — Priority Analyzer",
        layout="wide",
        page_icon="🎯",
        initial_sidebar_state="collapsed",
    )

    inject_css()

    st.markdown("""
    <div class="stp-header">
        <div class="stp-title">STP <span>Priority</span> Analyzer</div>
        <div class="stp-subtitle">
            BiP QA · Scenario-based priority assignment &nbsp;·&nbsp;
            Gating · High · Medium · Low &nbsp;·&nbsp;
            Device / OS scope detection
        </div>
    </div>
    <div class="stp-divider"></div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown('<div class="form-label">Scenario Input</div>', unsafe_allow_html=True)

        summary = st.text_input(
            "Summary",
            placeholder="e.g. App crashes while sending voice message (Redmi 10)",
            label_visibility="collapsed",
            key="stp_summary_v2",
        )

        st.markdown('<div class="section-label">Steps to Reproduce</div>', unsafe_allow_html=True)
        steps = st.text_area(
            "Steps",
            placeholder="1. Open chat\n2. Tap voice message icon\n3. Record and send\n4. App force closes",
            height=110,
            label_visibility="collapsed",
            key="stp_steps_v2",
        )

        # Actual / Expected Result — side by side
        col_a, col_e = st.columns(2)
        with col_a:
            st.markdown('<div class="section-label">🔴 Actual Result</div>', unsafe_allow_html=True)
            actual = st.text_area(
                "Actual",
                placeholder="What happens?\ne.g. App force closes immediately",
                height=90,
                label_visibility="collapsed",
                key="stp_actual_v2",
            )
        with col_e:
            st.markdown('<div class="section-label">🟢 Expected Result</div>', unsafe_allow_html=True)
            expected = st.text_area(
                "Expected",
                placeholder="What should happen?\ne.g. Voice message sent successfully",
                height=90,
                label_visibility="collapsed",
                key="stp_expected_v2",
            )

        # Reproduce Frequency + Device Scope — side by side
        col_f, col_d = st.columns(2)
        with col_f:
            st.markdown('<div class="section-label">🔁 Reproduce Frequency</div>', unsafe_allow_html=True)
            freq_labels = {
                "always":       "🔁 Always",
                "frequently":   "🔄 Frequently",
                "occasionally": "🔃 Occasionally",
                "rarely":       "🔀 Rarely",
                "once":         "1️⃣ Once",
            }
            freq_display = list(freq_labels.values())
            freq_keys    = list(freq_labels.keys())
            selected_display = st.selectbox(
                "Frequency",
                options=freq_display,
                index=0,
                label_visibility="collapsed",
                key="stp_freq_v2",
            )
            freq = freq_keys[freq_display.index(selected_display)]

        with col_d:
            st.markdown('<div class="section-label">📱 Device / OS Scope</div>', unsafe_allow_html=True)
            device_scope = st.text_input(
                "Device Scope",
                placeholder="e.g. Samsung A5, iOS 16, Redmi 10…",
                label_visibility="collapsed",
                key="stp_device_v2",
            )
            st.markdown(
                '<div style="font-size:0.7rem;color:#3A4A6B;margin-top:3px">'
                'Leave empty if reproducible on all devices</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        analyze = st.button("▶  Analyze Priority", key="stp_analyze_v2")

        # Priority legend
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="form-label" style="color:#3A4A6B;margin-bottom:0.6rem">Priority Reference</div>', unsafe_allow_html=True)
        for p, m in PRIORITY_META.items():
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
                f'<span style="width:10px;height:10px;border-radius:50%;background:{m["color"]};display:inline-block;flex-shrink:0;margin-top:3px"></span>'
                f'<div>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.7rem;color:{m["color"]};font-weight:600">{p}</span>'
                f'<span style="font-size:0.76rem;color:#3A4A6B;display:block;margin-top:1px">{m["desc"]}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        # Gating criteria note
        st.markdown("""
        <div style="background:#0D1321;border:1px solid #1E2761;border-left:3px solid #E53935;
                    border-radius:8px;padding:0.8rem 1rem;margin-top:1rem">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:#E53935;
                        letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.4rem">
                Gating Criteria (BiP)
            </div>
            <div style="font-size:0.76rem;color:#6B7A99;line-height:1.7">
                • Messaging / calling / login completely broken<br>
                • Always or scenario-specific reproducible crash<br>
                • Fraud / financial loss risk<br>
                • Permanent data loss<br>
                • Only core flow — not every minor crash is Gating
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        if analyze:
            if not summary.strip():
                st.warning("Please enter at least a summary.")
            else:
                priority, is_scoped, scope_type, scope_detail, reason, adjusted_note = render_result(
                    summary, steps, actual, expected, freq, device_scope
                )
                st.session_state.history.append({
                    "summary":       summary,
                    "steps":         steps,
                    "actual":        actual,
                    "expected":      expected,
                    "freq":          freq,
                    "device_scope":  device_scope,
                    "priority":      priority,
                    "is_scoped":     is_scoped,
                    "scope_type":    scope_type,
                    "scope_detail":  scope_detail,
                    "reason":        reason,
                    "adjusted_note": adjusted_note,
                })
        else:
            st.markdown("""
            <div style="
                height:260px; border:1px dashed #1E2761; border-radius:12px;
                display:flex; flex-direction:column; align-items:center; justify-content:center;
                color:#2A3A5C; font-family:'JetBrains Mono',monospace; font-size:0.8rem;
                letter-spacing:0.06em; gap:8px;
            ">
                <div style="font-size:2rem">🎯</div>
                <div>PRIORITY RESULT WILL APPEAR HERE</div>
                <div style="font-size:0.68rem;opacity:0.5">Fill in the scenario and click Analyze</div>
            </div>
            """, unsafe_allow_html=True)

    render_history()


if __name__ == "__main__":
    main()


    
