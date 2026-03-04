"""
STP Streamlit App — single CSV, smart priority assignment.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from stp_engine import run_stp, PRIORITY_ORDER

BUILD_PPT_SCRIPT = str(Path(__file__).parent / "build_ppt.js")

PRIORITY_COLOR = {
    "Gating": "#E53935",
    "High":   "#FB8C00",
    "Medium": "#1E88E5",
    "Low":    "#43A047",
}

SCOPE_COLOR = {
    "Device":               "#FF6F00",
    "Os Version":           "#7B1FA2",
    "Chipset":              "#C62828",
    "Single Device Repro":  "#AD1457",
    "":                     "#888888",
}


# ─────────────────────────────────────────────────────────────
# PPT
# ─────────────────────────────────────────────────────────────
def build_ppt(result: Dict) -> Optional[bytes]:
    payload = json.dumps({"result": result})
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        out_path = f.name
    try:
        r = subprocess.run(
            ["node", BUILD_PPT_SCRIPT, payload, out_path],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0 or not os.path.exists(out_path):
            st.error(f"PPT build failed:\n{r.stderr}")
            return None
        with open(out_path, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"PPT error: {e}")
        return None
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def df_to_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────
def pri_badge(p: str) -> str:
    c = PRIORITY_COLOR.get(p, "#888")
    return (f'<span style="background:{c};color:#fff;padding:2px 9px;'
            f'border-radius:4px;font-size:12px;font-weight:600">{p}</span>')


def scope_badge(scope_type: str, scope_detail: str) -> str:
    if not scope_type:
        return ""
    c = SCOPE_COLOR.get(scope_type, "#888")
    return (f'<span style="background:{c};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:500">'
            f'{scope_type}: {scope_detail}</span>')


def render_summary_table(summary_df: pd.DataFrame):
    rows_html = ""
    for _, row in summary_df.iterrows():
        pr    = row["Priority"]
        color = PRIORITY_COLOR.get(pr, "#888")
        chg   = int(row["Change"])
        chg_s = f"+{chg}" if chg > 0 else str(chg)
        c_col = "#E53935" if chg > 0 else "#43A047" if chg < 0 else "#888"
        rows_html += f"""
        <tr>
          <td style="padding:7px 12px">
            <span style="background:{color};color:#fff;padding:2px 10px;
            border-radius:4px;font-weight:600;font-size:13px">{pr}</span>
          </td>
          <td style="text-align:center;padding:7px;font-size:14px">{int(row['Current'])}</td>
          <td style="text-align:center;padding:7px;font-size:14px;font-weight:700">{int(row['STP'])}</td>
          <td style="text-align:center;padding:7px;color:{c_col};font-weight:700;font-size:14px">{chg_s}</td>
          <td style="text-align:center;padding:7px;color:{c_col};font-size:14px">{row['Change %']}%</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:12px">
      <thead>
        <tr style="background:#1E2761;color:#fff">
          <th style="padding:9px 12px;text-align:left">Priority</th>
          <th style="padding:9px;text-align:center">Current</th>
          <th style="padding:9px;text-align:center">STP</th>
          <th style="padding:9px;text-align:center">Change</th>
          <th style="padding:9px;text-align:center">Change %</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


def render_scoped_table(scoped_df: pd.DataFrame):
    if scoped_df.empty:
        st.info("No device/OS-specific cases detected.")
        return
    rows_html = ""
    for _, row in scoped_df.iterrows():
        cur_c  = PRIORITY_COLOR.get(row["Current Priority"], "#888")
        stp_c  = PRIORITY_COLOR.get(row["STP Priority"], "#888")
        sc     = SCOPE_COLOR.get(row["Scope Type"], "#888")
        changed = row["Changed"]
        arrow  = "↓" if changed else "="
        a_col  = "#E53935" if changed else "#888"
        rows_html += f"""
        <tr>
          <td style="padding:6px 10px;font-family:monospace;font-size:12px">{row['Issue Key']}</td>
          <td style="padding:6px 10px;font-size:12px;max-width:260px">{str(row['Summary'])[:80]}{'…' if len(str(row['Summary']))>80 else ''}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{sc};color:#fff;padding:1px 8px;border-radius:3px;font-size:11px">
              {row['Scope Type']}: {row['Scope Detail']}
            </span>
          </td>
          <td style="padding:6px;text-align:center">
            <span style="background:{cur_c};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['Current Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center;color:{a_col};font-size:14px;font-weight:700">{arrow}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{stp_c};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['STP Priority']}</span>
          </td>
          <td style="padding:6px;font-size:11px;color:#444;max-width:200px">{str(row['Reason'])[:90]}{'…' if len(str(row['Reason']))>90 else ''}</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#7B1FA2;color:#fff">
          <th style="padding:7px 10px;text-align:left">Issue Key</th>
          <th style="padding:7px 10px;text-align:left">Summary</th>
          <th style="padding:7px;text-align:center">Scope</th>
          <th style="padding:7px;text-align:center">Current</th>
          <th style="padding:7px;text-align:center"></th>
          <th style="padding:7px;text-align:center">STP</th>
          <th style="padding:7px;text-align:left">Reason</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


def render_changed_table(diff_df: pd.DataFrame):
    if diff_df.empty:
        return
    rows_html = ""
    for _, row in diff_df.iterrows():
        cur_c = PRIORITY_COLOR.get(row["Current Priority"], "#888")
        stp_c = PRIORITY_COLOR.get(row["STP Priority"], "#888")
        cur_r = ["Gating","High","Medium","Low"].index(row["Current Priority"]) if row["Current Priority"] in ["Gating","High","Medium","Low"] else 3
        stp_r = ["Gating","High","Medium","Low"].index(row["STP Priority"]) if row["STP Priority"] in ["Gating","High","Medium","Low"] else 3
        arrow_col = "#E53935" if stp_r < cur_r else "#43A047"
        arrow_sym = "↑" if stp_r < cur_r else "↓"
        rows_html += f"""
        <tr>
          <td style="padding:6px 10px;font-family:monospace;font-size:12px">{row['Issue Key']}</td>
          <td style="padding:6px 10px;font-size:12px;max-width:280px">{str(row['Summary'])[:85]}{'…' if len(str(row['Summary']))>85 else ''}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{cur_c};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['Current Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center;color:{arrow_col};font-size:14px;font-weight:700">{arrow_sym}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{stp_c};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['STP Priority']}</span>
          </td>
          <td style="padding:6px;font-size:11px;color:#444">{str(row['Scope Type']) + ': ' + str(row['Scope Detail']) if row['Scope Type'] else '—'}</td>
          <td style="padding:6px;font-size:11px;color:#444;max-width:220px">{str(row['Reason'])[:85]}{'…' if len(str(row['Reason']))>85 else ''}</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#37474F;color:#fff">
          <th style="padding:7px 10px;text-align:left">Issue Key</th>
          <th style="padding:7px 10px;text-align:left">Summary</th>
          <th style="padding:7px;text-align:center">Current</th>
          <th style="padding:7px;text-align:center"></th>
          <th style="padding:7px;text-align:center">STP</th>
          <th style="padding:7px;text-align:center">Scope</th>
          <th style="padding:7px;text-align:left">Reason</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="STP — Semantic Test Prioritization",
        layout="wide",
        page_icon="🎯",
    )

    st.title("🎯 Semantic Test Prioritization (STP)")
    st.caption(
        "Scenario-based priority assignment. "
        "Device/OS-specific cases detected and adjusted separately."
    )

    with st.sidebar:
        st.header("Priority Logic")
        st.markdown("""
**Decision order:**

🔴 **Gating** — app/feature completely broken  
crash, freeze, cannot send/call/login, force close

🟠 **High** — core feature defect  
send message, voice/video call, login, upload

🔵 **Medium** — secondary UX, non-blocking  
search, list, settings, profile, navigation

🟢 **Low** — cosmetic only, no functional impact  
misalign, wrong color, typo, icon glitch

---
**Device / OS scope adjustment:**

If scenario is device/OS specific:
- crash/freeze → stays **Gating** (crash is always Gating)
- Gating (non-crash) → **High** (not universal blocker)
- High → **Medium** (scoped to one device/OS)
- Medium/Low → unchanged, annotated

---
*Deterministic — same CSV, same result.*
        """)

    # ── Upload ──────────────────────────────────────────────
    st.subheader("Upload Test Case CSV")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if not uploaded:
        st.info("Upload a CSV file to get started.")
        st.stop()

    if not st.button("▶  Run STP Analysis", type="primary"):
        st.stop()

    # ── Parse & run ─────────────────────────────────────────
    try:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
        df  = pd.read_csv(io.StringIO(raw), sep=None, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    try:
        analysis_df, summary_df, diff_df = run_stp(df)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    total        = len(analysis_df)
    changed      = int(analysis_df["Changed"].sum())
    scoped_cases = analysis_df[analysis_df["Scoped"] == "Yes"]
    gat_before   = int(summary_df.loc[summary_df["Priority"] == "Gating", "Current"].iloc[0])
    gat_after    = int(summary_df.loc[summary_df["Priority"] == "Gating", "STP"].iloc[0])
    reduction    = gat_before - gat_after

    # ── KPIs ────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total cases",       total)
    k2.metric("Priority changed",  changed,
              delta=f"{round(changed/total*100,1)}%" if total else None)
    k3.metric("Gating before",     gat_before)
    k4.metric("Gating after",      gat_after,
              delta=f"−{reduction}" if reduction > 0 else str(reduction),
              delta_color="inverse")
    k5.metric("Device/OS scoped",  len(scoped_cases), delta_color="off")

    # ── Summary ─────────────────────────────────────────────
    st.markdown("### Priority Summary")
    render_summary_table(summary_df)

    # ── Scoped cases ────────────────────────────────────────
    if not scoped_cases.empty:
        scoped_changed = scoped_cases[scoped_cases["Changed"]]
        with st.expander(
            f"📱 Device / OS Specific Cases — {len(scoped_cases)} total, "
            f"{len(scoped_changed)} priority adjusted",
            expanded=True,
        ):
            render_scoped_table(
                scoped_cases[[
                    "Issue Key", "Summary", "Scope Type", "Scope Detail",
                    "Current Priority", "STP Priority", "Changed", "Reason"
                ]]
            )

    # ── All changed ─────────────────────────────────────────
    if not diff_df.empty:
        with st.expander(f"All priority changes ({len(diff_df)})", expanded=False):
            render_changed_table(
                diff_df[[
                    "Issue Key", "Summary", "Current Priority", "STP Priority",
                    "Scope Type", "Scope Detail", "Reason"
                ]]
            )

    # ── Full table ──────────────────────────────────────────
    with st.expander("Full analysis table", expanded=False):
        show = ["Issue Key", "Summary", "Current Priority", "STP Priority",
                "Scoped", "Scope Type", "Scope Detail", "Changed", "Reason"]
        st.dataframe(analysis_df[show], use_container_width=True, hide_index=True)

    # ── Downloads ───────────────────────────────────────────
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇ Analysis CSV", df_to_bytes(analysis_df),
                           "STPANALYSIS.csv", "text/csv")
    with c2:
        st.download_button("⬇ Summary CSV", df_to_bytes(summary_df),
                           "STPSUMMARY.csv", "text/csv")
    with c3:
        st.download_button("⬇ Diff CSV", df_to_bytes(diff_df),
                           "STPDIFF.csv", "text/csv")

    # ── PPT ─────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Executive Report PPT")

    summary_rows = [
        {
            "priority":   r["Priority"],
            "current":    int(r["Current"]),
            "stp":        int(r["STP"]),
            "change":     int(r["Change"]),
            "change_pct": float(r["Change %"]),
        }
        for _, r in summary_df.iterrows()
    ]

    # Scope breakdown for PPT
    scope_counts = scoped_cases["Scope Type"].value_counts().to_dict() if not scoped_cases.empty else {}
    scoped_changed_count = int(scoped_cases["Changed"].sum()) if not scoped_cases.empty else 0

    ppt_payload = {
        "total":               total,
        "changed":             changed,
        "gating_before":       gat_before,
        "gating_after":        gat_after,
        "scoped_count":        len(scoped_cases),
        "scoped_changed":      scoped_changed_count,
        "scope_breakdown":     scope_counts,
        "summary":             summary_rows,
    }

    with st.spinner("Building PPT…"):
        ppt_bytes = build_ppt(ppt_payload)

    if ppt_bytes:
        st.success("Ready!")
        st.download_button(
            "⬇ Download STPEXECUTIVEREPORT.pptx",
            data=ppt_bytes,
            file_name="STPEXECUTIVEREPORT.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
        )


if __name__ == "__main__":
    main()
