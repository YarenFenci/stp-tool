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
        "desc":   "Yük çıkmadan önce çözülmeli — temel fonksiyon bozuk veya reproducible crash.",
    },
    "High": {
        "color":  "#FB8C00",
        "bg":     "#FFF8F0",
        "border": "#FFE0B2",
        "icon":   "🟠",
        "label":  "HIGH",
        "desc":   "Önemli özellik etkilenmiş — 2 hafta içinde çözülmeli, PO/QA Lead kararı gerekir.",
    },
    "Medium": {
        "color":  "#1E88E5",
        "bg":     "#F0F6FF",
        "border": "#BBDEFB",
        "icon":   "🔵",
        "label":  "MEDIUM",
        "desc":   "İkincil UX sorunu — workaround var, 6 hafta içinde çözülmeli.",
    },
    "Low": {
        "color":  "#43A047",
        "bg":     "#F0FFF0",
        "border": "#C8E6C9",
        "icon":   "🟢",
        "label":  "LOW",
        "desc":   "Kozmetik / küçük edge case — fonksiyonel etkisi yok.",
    },
}

SCOPE_META = {
    "device":              {"label": "Cihaz Özelinde",       "color": "#FF6F00"},
    "os_version":          {"label": "OS Versiyonu Özelinde", "color": "#7B1FA2"},
    "chipset":             {"label": "Chipset Özelinde",      "color": "#C62828"},
    "single_device_repro": {"label": "Tek Cihazda Repro",    "color": "#AD1457"},
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
def render_result(summary: str, steps: str, actual: str, expected: str):
    base_text = (summary + " " + steps).lower()
    priority, is_scoped, scope_type, scope_detail, reason = decide_priority(
        base_text, actual_result=actual, expected_result=expected
    )
    meta = PRIORITY_META[priority]
    hits = find_hit_keywords(base_text + " " + actual + " " + expected, priority)

    # Result card
    st.markdown(f"""
    <div class="result-card" style="background:{meta['bg']};border-color:{meta['border']};">
        <div class="result-priority-label" style="color:{meta['color']}">STP PRIORITY</div>
        <div class="result-priority-value" style="color:{meta['color']}">{meta['icon']} {meta['label']}</div>
        <div class="result-desc" style="color:{meta['color']}">{meta['desc']}</div>
        {"" if not is_scoped else f'''
        <div class="device-badge" style="
            background:{SCOPE_META.get(scope_type,{}).get('color','#FF6F00')}22;
            border:1px solid {SCOPE_META.get(scope_type,{}).get('color','#FF6F00')}66;
            color:{SCOPE_META.get(scope_type,{}).get('color','#FF6F00')};
        ">
            ⚠ {SCOPE_META.get(scope_type,{}).get('label','Cihaz Özelinde')}: {scope_detail}
        </div>
        '''}
    </div>
    """, unsafe_allow_html=True)

    # Actual vs Expected comparison
    if actual.strip() or expected.strip():
        actual_html = actual.strip() if actual.strip() else "<em style='opacity:0.4'>Belirtilmedi</em>"
        expected_html = expected.strip() if expected.strip() else "<em style='opacity:0.4'>Belirtilmedi</em>"
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

    # Reason
    st.markdown(f"""
    <div class="reason-box">
        <div class="reason-title">Neden bu priority?</div>
        <div class="reason-text">{reason}</div>
    </div>
    """, unsafe_allow_html=True)

    # Matched keywords
    if hits:
        chips = "".join(f'<span class="kw-chip">{kw}</span>' for kw in hits)
        st.markdown(f"""
        <div class="keyword-box">
            <div class="reason-title" style="margin-bottom:0.4rem">Eşleşen sinyaller</div>
            {chips}
        </div>
        """, unsafe_allow_html=True)

    return priority, is_scoped, scope_type, scope_detail, reason


# ─────────────────────────────────────────────
# History
# ─────────────────────────────────────────────
def render_history():
    if not st.session_state.history:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="form-label" style="color:#6B7A99;margin-bottom:0.6rem">'
        f'OTURUM GEÇMİŞİ &nbsp;·&nbsp; {len(st.session_state.history)} senaryo</div>',
        unsafe_allow_html=True,
    )

    for i, entry in enumerate(reversed(st.session_state.history)):
        meta     = PRIORITY_META[entry["priority"]]
        dev_html = (
            f'<span class="hist-device">⚠ {entry["scope_detail"]}</span>'
            if entry["is_scoped"] else ""
        )
        st.markdown(f"""
        <div class="hist-row">
            <span class="hist-key">#{len(st.session_state.history)-i}</span>
            <span class="hist-summary">{entry['summary'][:70]}{'…' if len(entry['summary'])>70 else ''}</span>
            {dev_html}
            <span class="hist-badge" style="background:{meta['color']}">{meta['label']}</span>
        </div>
        """, unsafe_allow_html=True)

    if len(st.session_state.history) > 0:
        hist_df = pd.DataFrame(st.session_state.history)[[
            "summary", "steps", "actual", "expected",
            "priority", "is_scoped", "scope_type", "scope_detail", "reason"
        ]]
        hist_df.columns = [
            "Summary", "Steps", "Actual Result", "Expected Result",
            "Priority", "Device Specific", "Scope Type", "Scope Detail", "Reason"
        ]
        st.download_button(
            "⬇ CSV olarak dışa aktar",
            data=hist_df.to_csv(index=False).encode("utf-8"),
            file_name="stp_session.csv",
            mime="text/csv",
            key="dl_hist",
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
            BiP QA · Senaryo bazlı öncelik atama &nbsp;·&nbsp;
            Gating · High · Medium · Low &nbsp;·&nbsp;
            Cihaz / OS scope tespiti
        </div>
    </div>
    <div class="stp-divider"></div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown('<div class="form-label">Senaryo Girişi</div>', unsafe_allow_html=True)

        summary = st.text_input(
            "Summary",
            placeholder="Örn: Sesli mesaj gönderirken uygulama crash oluyor (Redmi 10)",
            label_visibility="collapsed",
            key="inp_summary",
        )

        st.markdown('<div class="section-label">Adımlar</div>', unsafe_allow_html=True)
        steps = st.text_area(
            "Steps",
            placeholder="1. Sohbeti aç\n2. Sesli mesaj ikonuna bas\n3. Kaydet ve gönder\n4. Uygulama kapanıyor",
            height=110,
            label_visibility="collapsed",
            key="inp_steps",
        )

        # Actual / Expected Result — yan yana
        col_a, col_e = st.columns(2)
        with col_a:
            st.markdown('<div class="section-label">🔴 Actual Result</div>', unsafe_allow_html=True)
            actual = st.text_area(
                "Actual",
                placeholder="Ne oluyor?\nÖrn: Uygulama force close ile kapanıyor",
                height=100,
                label_visibility="collapsed",
                key="inp_actual",
            )
        with col_e:
            st.markdown('<div class="section-label">🟢 Expected Result</div>', unsafe_allow_html=True)
            expected = st.text_area(
                "Expected",
                placeholder="Ne olmalıydı?\nÖrn: Sesli mesaj başarıyla gönderilmeli",
                height=100,
                label_visibility="collapsed",
                key="inp_expected",
            )

        st.markdown("<br>", unsafe_allow_html=True)
        analyze = st.button("▶  Priority Analiz Et", key="btn_analyze")

        # Priority legend
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="form-label" style="color:#3A4A6B;margin-bottom:0.6rem">Priority Referans</div>', unsafe_allow_html=True)
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
                Gating Kriterleri (BiP)
            </div>
            <div style="font-size:0.76rem;color:#6B7A99;line-height:1.7">
                • Mesajlaşma / arama / giriş tamamen çalışmıyor<br>
                • Her zaman veya belirli senaryo ile crash<br>
                • Fraud / maddi kayıp riski<br>
                • Kalıcı veri kaybı<br>
                • Story / group gibi her yerde crash değil, sadece core akış
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        if analyze:
            if not summary.strip():
                st.warning("Lütfen en azından bir summary girin.")
            else:
                priority, is_scoped, scope_type, scope_detail, reason = render_result(
                    summary, steps, actual, expected
                )
                st.session_state.history.append({
                    "summary":      summary,
                    "steps":        steps,
                    "actual":       actual,
                    "expected":     expected,
                    "priority":     priority,
                    "is_scoped":    is_scoped,
                    "scope_type":   scope_type,
                    "scope_detail": scope_detail,
                    "reason":       reason,
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
                <div>PRIORITY SONUCU BURADA GÖRÜNECEK</div>
                <div style="font-size:0.68rem;opacity:0.5">Senaryoyu doldurun ve analiz edin</div>
            </div>
            """, unsafe_allow_html=True)

    render_history()


if __name__ == "__main__":
    main()
