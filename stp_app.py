"""
STP Streamlit App — Semantic Test Prioritization
Upload test case CSVs, assign features, run STP engine,
download reports + Executive PPT.
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
FEATURES = ["Calls", "Chats", "Channels", "Status", "More", "Others"]

PRIORITY_COLOR = {
    "Gating": "#E53935",
    "High":   "#FB8C00",
    "Medium": "#1E88E5",
    "Low":    "#43A047",
}

SCOPE_LABEL = {
    "low_end_device": "Low-end device",
    "os_version":     "OS version specific",
    "chipset":        "Chipset specific",
    "single_device":  "Single device repro",
    "latest_version": "Latest version / beta",
    "":               "",
}


# ─────────────────────────────────────────────────────────────
# PPT builder
# ─────────────────────────────────────────────────────────────
def build_executive_ppt(feature_results: List[Dict]) -> Optional[bytes]:
    payload = json.dumps({"features": feature_results})
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


def badge(text: str, color: str) -> str:
    return (f'<span style="background:{color};color:#fff;padding:2px 9px;'
            f'border-radius:4px;font-size:12px;font-weight:600">{text}</span>')


def render_summary_table(summary_df: pd.DataFrame):
    rows_html = ""
    for _, row in summary_df.iterrows():
        pr     = row["Priority"]
        color  = PRIORITY_COLOR.get(pr, "#888")
        chg    = int(row["Change"])
        chg_s  = f"+{chg}" if chg > 0 else str(chg)
        c_col  = "#E53935" if chg > 0 else "#43A047" if chg < 0 else "#888"
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


def render_device_table(device_df: pd.DataFrame):
    """Renders device-specific cases with scope badges."""
    if device_df.empty:
        st.info("No device-specific cases detected.")
        return

    rows_html = ""
    for _, row in device_df.iterrows():
        stp_col   = PRIORITY_COLOR.get(row["STP Priority"], "#888")
        cur_col   = PRIORITY_COLOR.get(row["Current Priority"], "#888")
        scope_txt = SCOPE_LABEL.get(row["Device Scope"], row["Device Scope"])
        changed   = row["Changed"]
        arrow     = (f'<span style="color:#E53935">↓</span> '
                     if changed else '<span style="color:#888">→</span> ')
        rows_html += f"""
        <tr style="background:#FFF8F0">
          <td style="padding:6px 10px;font-family:monospace;font-size:12px">{row['Issue Key']}</td>
          <td style="padding:6px 10px;font-size:12px;max-width:280px">{row['Summary'][:90]}{'…' if len(row['Summary'])>90 else ''}</td>
          <td style="padding:6px;text-align:center">
            <span style="background:{cur_col};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['Current Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center">
            {arrow}<span style="background:{stp_col};color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{row['STP Priority']}</span>
          </td>
          <td style="padding:6px;text-align:center">
            <span style="background:#FF6F00;color:#fff;padding:1px 7px;border-radius:3px;font-size:11px">{scope_txt}</span>
          </td>
          <td style="padding:6px;font-size:11px;color:#555;max-width:220px">{row['Reason'][:80]}{'…' if len(row['Reason'])>80 else ''}</td>
        </tr>"""

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#FF6F00;color:#fff">
          <th style="padding:7px 10px;text-align:left">Issue Key</th>
          <th style="padding:7px 10px;text-align:left">Summary</th>
          <th style="padding:7px;text-align:center">Current</th>
          <th style="padding:7px;text-align:center">STP</th>
          <th style="padding:7px;text-align:center">Device Scope</th>
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
        "Scenario-based priority rebalancing with device-specific detection. "
        "Low-end device / OS-version / single-device scenarios are automatically downgraded."
    )

    # ── Sidebar: info + config ────────────────────────────────
    with st.sidebar:
        st.header("How it works")
        st.markdown("""
**Priority decision order:**
1. Scenario keywords → base priority
2. Device-specific signal? → downgrade 1 level
3. Exception: hard crash stays **Gating**

**Device signals detected:**
- Low-end device names (Redmi, Tecno, Infinix…)
- OS version pins (Android 10, iOS 14…)
- Chipset signals (Unisoc, Helio G…)
- Single-device repro phrases
- Latest version / beta / after-update

**Features supported:**
Calls · Chats · Channels · Status · More · Others
        """)
        st.divider()
        st.caption("Deterministic engine — same CSV → same result every time.")

    # ── Upload ────────────────────────────────────────────────
    st.subheader("1 · Upload CSVs")
    uploaded_files = st.file_uploader(
        "Upload one or more test case CSV files",
        type=["csv"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("Upload at least one CSV to get started.")
        st.stop()

    # ── Feature assignment ────────────────────────────────────
    st.subheader("2 · Assign feature to each file")
    file_feature_map: Dict[str, str] = {}
    cols = st.columns(min(len(uploaded_files), 3))
    for i, f in enumerate(uploaded_files):
        with cols[i % len(cols)]:
            file_feature_map[f.name] = st.selectbox(
                f.name, FEATURES, index=i % len(FEATURES), key=f"feat_{i}"
            )

    # ── Run ───────────────────────────────────────────────────
    if not st.button("▶  Run STP Analysis", type="primary"):
        st.stop()

    all_results = []

    for uploaded in uploaded_files:
        feature = file_feature_map[uploaded.name]
        st.divider()
        st.subheader(f"📂 {uploaded.name}  ·  Feature: **{feature}**")

        try:
            raw = uploaded.getvalue().decode("utf-8", errors="replace")
            df  = pd.read_csv(io.StringIO(raw), sep=None, engine="python", on_bad_lines="skip")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            continue

        try:
            analysis_df, summary_df, diff_df = run_stp(df, feature)
        except ValueError as e:
            st.error(str(e))
            continue

        total         = len(analysis_df)
        changed       = int(analysis_df["Changed"].sum())
        device_cases  = analysis_df[analysis_df["Device Specific"] == "Yes"]
        gating_before = int(summary_df.loc[summary_df["Priority"] == "Gating", "Current"].iloc[0])
        gating_after  = int(summary_df.loc[summary_df["Priority"] == "Gating", "STP"].iloc[0])
        reduction     = gating_before - gating_after

        # KPI row
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total cases",       total)
        k2.metric("Changed",           changed,
                  delta=f"{round(changed/total*100,1)}%" if total else None)
        k3.metric("Gating before",     gating_before)
        k4.metric("Gating after",      gating_after,
                  delta=f"−{reduction}" if reduction > 0 else str(reduction),
                  delta_color="inverse")
        k5.metric("Device-specific",   len(device_cases),
                  delta=f"{round(len(device_cases)/total*100,1)}%" if total else None,
                  delta_color="off")

        # Priority summary table
        st.markdown("**Priority Summary**")
        render_summary_table(summary_df)

        # Device-specific section
        if not device_cases.empty:
            with st.expander(
                f"⚠️ Device-specific cases ({len(device_cases)}) — "
                f"{len(device_cases[device_cases['Changed']])} downgraded",
                expanded=True,
            ):
                render_device_table(device_cases[
                    ["Issue Key", "Summary", "Current Priority",
                     "STP Priority", "Device Scope", "Changed", "Reason"]
                ])

        # All changed rows
        if not diff_df.empty:
            with st.expander(f"All changed rows ({len(diff_df)})", expanded=False):
                show = ["Issue Key", "Summary", "Current Priority",
                        "STP Priority", "Device Specific", "Device Scope", "Reason"]
                st.dataframe(diff_df[show], use_container_width=True, hide_index=True)

        # Full analysis preview
        with st.expander("Full analysis table", expanded=False):
            show_all = ["Issue Key", "Summary", "Current Priority", "STP Priority",
                        "Device Specific", "Device Scope", "Changed", "Reason"]
            st.dataframe(analysis_df[show_all], use_container_width=True, hide_index=True)

        # Downloads
        safe_name = feature.replace(" ", "")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "⬇ Analysis CSV",
                data=df_to_bytes(analysis_df),
                file_name=f"STPREBALANCEANALYSIS_{safe_name}.csv",
                mime="text/csv",
                key=f"dl_a_{safe_name}_{uploaded.name}",
            )
        with c2:
            st.download_button(
                "⬇ Summary CSV",
                data=df_to_bytes(summary_df),
                file_name=f"STPREBALANCESUMMARY_{safe_name}.csv",
                mime="text/csv",
                key=f"dl_s_{safe_name}_{uploaded.name}",
            )
        with c3:
            st.download_button(
                "⬇ Diff CSV",
                data=df_to_bytes(diff_df),
                file_name=f"STPREBALANCEDIFF_{safe_name}.csv",
                mime="text/csv",
                key=f"dl_d_{safe_name}_{uploaded.name}",
            )

        # Accumulate for PPT
        summary_rows = []
        for _, row in summary_df.iterrows():
            summary_rows.append({
                "priority":   row["Priority"],
                "current":    int(row["Current"]),
                "stp":        int(row["STP"]),
                "change":     int(row["Change"]),
                "change_pct": float(row["Change %"]),
            })

        all_results.append({
            "name":           feature,
            "current_gating": gating_before,
            "stp_gating":     gating_after,
            "total_current":  total,
            "total_stp":      total,
            "device_count":   len(device_cases),
            "summary":        summary_rows,
        })

    # ── Executive PPT ─────────────────────────────────────────
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
