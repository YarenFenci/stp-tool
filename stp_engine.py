"""
STP Streamlit App — platform-aware (Android / iOS / Both)
Upload Android CSV, iOS CSV, or both. Engine runs without feature selection.
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

PLATFORM_COLOR = {
    "Android": "#3DDC84",
    "iOS":     "#007AFF",
    "Both":    "#9C27B0",
    "":        "#888888",
}

SCOPE_LABEL = {
    "low_end_device": "Low-end device",
    "os_version":     "OS version",
    "chipset":        "Chipset",
    "single_device":  "Single device repro",
    "latest_version": "Latest version / beta",
    "":               "",
}


# ─────────────────────────────────────────────────────────────
# PPT builder
# ─────────────────────────────────────────────────────────────
def build_executive_ppt(platform_results: List[Dict]) -> Optional[bytes]:
    payload = json.dumps({"platforms": platform_results})
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        out_path = f.name
    try:
        result = subprocess.run(
            ["node", BUILD_PPT_SCRIPT, payload, out_path],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0 or not os.path.exists(out_path):
            st.error(f"PPT build failed:\n{result.stderr}")
            return None
        with open(out_path, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"PPT build error: {e}")
        return None
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def df_to_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


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
            border-radius:4px;font-weight:600;font-size:12px">{pr}</span>
          </td>
          <td style="text-align:center;padding:7px">{int(row['Current'])}</td>
          <td style="text-align:center;padding:7px;font-weight:700">{int(row['STP'])}</td>
          <td style="text-align:center;padding:7px;color:{c_col};font-weight:700">{chg_s}</td>
          <td style="text-align:center;padding:7px;color:{c_col}">{row['Change %']}%</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:12px">
      <thead>
        <tr style="background:#1E2761;color:#fff">
          <th style="padding:8px 12px;text-align:left">Priority</th>
          <th style="padding:8px;text-align:center">Current</th>
          <th style="padding:8px;text-align:center">STP</th>
          <th style="padding:8px;text-align:center">Change</th>
          <th style="padding:8px;text-align:center">Change %</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


def render_platform_breakdown(analysis_df: pd.DataFrame):
    """Platform distribution of the dataset."""
    counts = analysis_df["Platform"].value_counts()
    total  = len(analysis_df)
    parts  = []
    for plat, cnt in counts.items():
        col = PLATFORM_COLOR.get(plat, "#888")
        lbl = plat if plat else "Undetected"
        pct = round(cnt / total * 100, 1)
        parts.append(
            f'<span style="background:{col};color:#fff;padding:3px 10px;'
            f'border-radius:4px;font-size:12px;font-weight:600;margin-right:6px">'
            f'{lbl}: {cnt} ({pct}%)</span>'
        )
    st.markdown(" ".join(parts), unsafe_allow_html=True)


def render_device_table(device_df: pd.DataFrame):
    if device_df.empty:
        st.info("No device-specific cases detected.")
        return
    rows_html = ""
    for _, row in device_df.iterrows():
        stp_col  = PRIORITY_COLOR.get(row["STP Priority"], "#888")
        cur_col  = PRIORITY_COLOR.get(row["Current Priority"], "#888")
        plat_col = PLATFORM_COLOR.get(row["Platform"], "#888")
        scope    = SCOPE_LABEL.get(row["Device Scope"], row["Device Scope"])
        plat     = row["Platform"] or "—"
        changed  = row["Changed"]
        arrow    = '<span style="color:#E53935">↓</span> ' if changed else '<span style="color:#888">→</span> '
        rows_html += f"""
        <tr style="background:#FFF8F0">
          <td style="padding:6px 10px;font-family:monospace;font-size:12px">{row['Issue Key']}</td>
          <td style="padding:6px 10px;font-size:12px;max-width:260px">{str(row['Summary'])[:85]}{'…' if len(str(row['Summary']))>85 else ''}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{plat_col};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{plat}</span>
          </td>
          <td style="padding:6px;text-align:center">
            <span style="background:{cur_col};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['Current Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center">
            {arrow}<span style="background:{stp_col};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['STP Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center">
            <span style="background:#FF6F00;color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{scope}</span>
          </td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#FF6F00;color:#fff">
          <th style="padding:7px 10px;text-align:left">Issue Key</th>
          <th style="padding:7px 10px;text-align:left">Summary</th>
          <th style="padding:7px;text-align:center">Platform</th>
          <th style="padding:7px;text-align:center">Current</th>
          <th style="padding:7px;text-align:center">STP</th>
          <th style="padding:7px;text-align:center">Device Scope</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


def render_ui_edge_table(ui_df: pd.DataFrame):
    if ui_df.empty:
        st.info("No UI edge cases detected.")
        return
    rows_html = ""
    for _, row in ui_df.iterrows():
        cur_col = PRIORITY_COLOR.get(row["Current Priority"], "#888")
        changed = row["Changed"]
        arrow   = '<span style="color:#43A047">↓ Low</span>' if changed else '<span style="color:#888">Low</span>'
        rows_html += f"""
        <tr>
          <td style="padding:6px 10px;font-family:monospace;font-size:12px">{row['Issue Key']}</td>
          <td style="padding:6px 10px;font-size:12px;max-width:320px">{str(row['Summary'])[:95]}{'…' if len(str(row['Summary']))>95 else ''}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{cur_col};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['Current Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center">{arrow}</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#43A047;color:#fff">
          <th style="padding:7px 10px;text-align:left">Issue Key</th>
          <th style="padding:7px 10px;text-align:left">Summary</th>
          <th style="padding:7px;text-align:center">Current Priority</th>
          <th style="padding:7px;text-align:center">STP Priority</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Process one uploaded file
# ─────────────────────────────────────────────────────────────
def process_file(uploaded, platform_label: str) -> Optional[Dict]:
    st.subheader(f"{'🤖' if 'android' in platform_label.lower() else '🍎'} {platform_label}  ·  {uploaded.name}")

    try:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
        df  = pd.read_csv(io.StringIO(raw), sep=None, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return None

    try:
        analysis_df, summary_df, diff_df = run_stp(df)
    except ValueError as e:
        st.error(str(e))
        return None

    total         = len(analysis_df)
    changed       = int(analysis_df["Changed"].sum())
    device_cases  = analysis_df[analysis_df["Device Specific"] == "Yes"]
    ui_edge_cases = analysis_df[analysis_df["Reason"].str.startswith("UI / cosmetic")]
    gating_before = int(summary_df.loc[summary_df["Priority"] == "Gating", "Current"].iloc[0])
    gating_after  = int(summary_df.loc[summary_df["Priority"] == "Gating", "STP"].iloc[0])
    reduction     = gating_before - gating_after

    # KPIs
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total cases",     total)
    k2.metric("Changed",         changed,
              delta=f"{round(changed/total*100,1)}%" if total else None)
    k3.metric("Gating before",   gating_before)
    k4.metric("Gating after",    gating_after,
              delta=f"−{reduction}" if reduction > 0 else str(reduction),
              delta_color="inverse")
    k5.metric("Device-specific", len(device_cases),   delta_color="off")
    k6.metric("UI edge → Low",   len(ui_edge_cases[ui_edge_cases["Changed"]]), delta_color="off")

    # Platform breakdown
    st.markdown("**Platform distribution detected in dataset:**")
    render_platform_breakdown(analysis_df)
    st.markdown("")

    # Summary table
    st.markdown("**Priority Summary**")
    render_summary_table(summary_df)

    # UI edge cases
    ui_changed = ui_edge_cases[ui_edge_cases["Changed"]]
    if not ui_edge_cases.empty:
        with st.expander(
            f"🎨 UI Edge Cases — {len(ui_changed)} downgraded to Low ({len(ui_edge_cases)} total detected)",
            expanded=True,
        ):
            render_ui_edge_table(
                ui_edge_cases[["Issue Key", "Summary", "Current Priority", "STP Priority", "Changed"]]
            )

    # Device-specific
    if not device_cases.empty:
        with st.expander(
            f"📱 Device-specific cases ({len(device_cases)}) — priority unchanged, flagged for info",
            expanded=False,
        ):
            render_device_table(
                device_cases[["Issue Key", "Summary", "Platform",
                              "Current Priority", "STP Priority", "Device Scope", "Changed"]]
            )

    # All changed
    if not diff_df.empty:
        with st.expander(f"All changed rows ({len(diff_df)})", expanded=False):
            show = ["Issue Key", "Summary", "Current Priority", "STP Priority",
                    "Platform", "Device Specific", "Device Scope", "Reason"]
            st.dataframe(diff_df[show], use_container_width=True, hide_index=True)

    # Full table
    with st.expander("Full analysis table", expanded=False):
        show_all = ["Issue Key", "Summary", "Current Priority", "STP Priority",
                    "Platform", "Device Specific", "Device Scope", "Changed", "Reason"]
        st.dataframe(analysis_df[show_all], use_container_width=True, hide_index=True)

    # Downloads
    safe = platform_label.replace(" ", "")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇ Analysis CSV", df_to_bytes(analysis_df),
                           f"STPANALYSIS_{safe}.csv", "text/csv",
                           key=f"dl_a_{safe}")
    with c2:
        st.download_button("⬇ Summary CSV", df_to_bytes(summary_df),
                           f"STPSUMMARY_{safe}.csv", "text/csv",
                           key=f"dl_s_{safe}")
    with c3:
        st.download_button("⬇ Diff CSV", df_to_bytes(diff_df),
                           f"STPDIFF_{safe}.csv", "text/csv",
                           key=f"dl_d_{safe}")

    # Return data for PPT
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

    return {
        "name":           platform_label,
        "current_gating": gating_before,
        "stp_gating":     gating_after,
        "total_current":  total,
        "device_count":   len(device_cases),
        "ui_edge_count":  len(ui_changed),
        "summary":        summary_rows,
    }


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
        "Platform-aware priority rebalancing. "
        "UI/cosmetic edge cases → Low. Device-specific cases flagged (priority unchanged)."
    )

    with st.sidebar:
        st.header("How it works")
        st.markdown("""
**Priority decision (in order):**
1. UI cosmetic edge case? → **Low**
2. Core broken (crash/freeze/cannot)? → **Gating**
3. Core feature (send/call/login)? → **High**
4. Secondary UX (search/list/settings)? → **Medium**
5. Otherwise → **Low**

**Platform detection:**
Automatically detects Android / iOS / Both from scenario text — no manual selection needed.

**Device-specific:**
Flagged for visibility — priority NOT changed.
QA team can review these separately.

**UI edge cases → Low:**
Misalignment, wrong color, icon position,
text overlap, layout glitch, typo, etc.
Only if no functional failure is present.
        """)
        st.divider()
        st.caption("Deterministic — same CSV, same result every time.")

    # ── Upload ─────────────────────────────────────────────
    st.subheader("Upload CSV files")
    col_a, col_i = st.columns(2)
    with col_a:
        android_file = st.file_uploader("🤖 Android CSV", type=["csv"], key="android")
    with col_i:
        ios_file = st.file_uploader("🍎 iOS CSV", type=["csv"], key="ios")

    if not android_file and not ios_file:
        st.info("Upload at least one CSV (Android or iOS) to get started.")
        st.stop()

    if not st.button("▶  Run STP Analysis", type="primary"):
        st.stop()

    all_results = []

    if android_file:
        st.divider()
        result = process_file(android_file, "Android")
        if result:
            all_results.append(result)

    if ios_file:
        st.divider()
        result = process_file(ios_file, "iOS")
        if result:
            all_results.append(result)

    # ── Executive PPT ──────────────────────────────────────
    if all_results:
        st.divider()
        st.subheader("📊 Executive Report PPT")
        with st.spinner("Building PPT…"):
            ppt_bytes = build_executive_ppt(all_results)
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
