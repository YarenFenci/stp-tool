#!/usr/bin/env node
/**
 * STP Executive Report PPT builder (PptxGenJS)
 * Usage: node build_ppt.js '<json>' '<output.pptx>'
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const data     = JSON.parse(process.argv[2]);
const outPath  = process.argv[3] || "STPEXECUTIVEREPORT.pptx";
const features = data.features || [];

const C = {
  navy:    "1E2761",
  dark:    "0D1B4B",
  ice:     "CADCFC",
  white:   "FFFFFF",
  accent:  "4FC3F7",
  green:   "43A047",
  red:     "E53935",
  amber:   "FB8C00",
  orange:  "FF6F00",
  blue:    "1E88E5",
  gray:    "64748B",
  lightbg: "F0F4FF",
  rowalt:  "E8EEFF",
};

const makeShadow = () => ({
  type: "outer", blur: 8, offset: 3, angle: 135,
  color: "000000", opacity: 0.12,
});

let pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

// ══════════════════════════════════════════════
// SLIDE 1 — Title
// ══════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.dark };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.22, h: 7.5,
    fill: { color: C.accent }, line: { color: C.accent },
  });

  s.addText("STP Executive Report", {
    x: 0.55, y: 1.6, w: 12, h: 1.2,
    fontSize: 48, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", margin: 0,
  });
  s.addText("Semantic Test Prioritization — Scenario-based priority rebalancing with device-specific detection", {
    x: 0.55, y: 2.95, w: 11, h: 0.65,
    fontSize: 16, color: C.ice, fontFace: "Calibri", align: "left", margin: 0,
  });

  // Feature pills
  let px = 0.55;
  features.forEach(f => {
    const w = Math.max(1.1, f.name.length * 0.14 + 0.4);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: px, y: 3.9, w, h: 0.38,
      fill: { color: C.navy }, line: { color: C.accent, pt: 1.5 }, rectRadius: 0.08,
    });
    s.addText(f.name, {
      x: px, y: 3.9, w, h: 0.38,
      fontSize: 11, color: C.accent, bold: true, align: "center",
      fontFace: "Calibri", margin: 0,
    });
    px += w + 0.18;
  });

  s.addText("Confidential — QA Team", {
    x: 0.55, y: 7.05, w: 12, h: 0.3,
    fontSize: 10, color: C.gray, align: "left", margin: 0,
  });
}

// ══════════════════════════════════════════════
// SLIDE 2 — Executive Summary KPIs
// ══════════════════════════════════════════════
{
  const totalFalseGating = features.reduce((s, f) => s + (f.current_gating - f.stp_gating), 0);
  const totalTests       = features.reduce((s, f) => s + (f.total_current || 0), 0);
  const totalGatBefore   = features.reduce((s, f) => s + f.current_gating, 0);
  const totalGatAfter    = features.reduce((s, f) => s + f.stp_gating, 0);
  const totalDevice      = features.reduce((s, f) => s + (f.device_count || 0), 0);
  const shareBefore      = totalTests ? (totalGatBefore / totalTests * 100).toFixed(1) : "—";
  const shareAfter       = totalTests ? (totalGatAfter  / totalTests * 100).toFixed(1) : "—";
  const reduction        = totalGatBefore ? ((totalFalseGating / totalGatBefore) * 100).toFixed(1) : "0";

  let s = pres.addSlide();
  s.background = { color: C.lightbg };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.3, h: 0.72,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  s.addText("Executive Summary", {
    x: 0.4, y: 0, w: 12, h: 0.72,
    fontSize: 22, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0,
  });

  // 5 KPI cards
  const kpis = [
    { label: "False Gating Removed",  value: String(totalFalseGating), color: C.green },
    { label: "Gating Share Before",   value: `${shareBefore}%`,        color: C.amber },
    { label: "Gating Share After",    value: `${shareAfter}%`,         color: C.accent },
    { label: "Gating Reduction",      value: `${reduction}%`,          color: C.green },
    { label: "Device-Specific Cases", value: String(totalDevice),      color: C.orange },
  ];

  kpis.forEach((k, i) => {
    const cx = 0.3 + i * 2.54;
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 0.95, w: 2.3, h: 1.55,
      fill: { color: C.white }, line: { color: C.ice, pt: 1 },
      shadow: makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 0.95, w: 2.3, h: 0.1,
      fill: { color: k.color }, line: { color: k.color },
    });
    s.addText(k.value, {
      x: cx, y: 1.15, w: 2.3, h: 0.75,
      fontSize: 32, bold: true, color: k.color,
      fontFace: "Calibri", align: "center", margin: 0,
    });
    s.addText(k.label, {
      x: cx, y: 1.9, w: 2.3, h: 0.45,
      fontSize: 10, color: C.gray,
      fontFace: "Calibri", align: "center", margin: 0,
    });
  });

  // Bullets
  const bullets = [
    `${totalFalseGating} test cases incorrectly marked as Gating — re-prioritized by STP engine.`,
    `Gating share reduced from ${shareBefore}% to ${shareAfter}% of total test suite.`,
    `${totalDevice} device-specific scenarios detected and downgraded (low-end device / OS version / single repro).`,
    `Hard crashes on specific devices kept as Gating — a crash is a crash regardless of device.`,
    `Deterministic engine: same CSV always produces the same output.`,
  ];

  s.addText("Key Insights", {
    x: 0.4, y: 2.72, w: 12, h: 0.38,
    fontSize: 15, bold: true, color: C.navy, fontFace: "Calibri", margin: 0,
  });

  s.addText(
    bullets.map((b, i) => ({
      text: b,
      options: {
        bullet: true, breakLine: i < bullets.length - 1,
        color: C.dark, fontSize: 12, fontFace: "Calibri",
      }
    })),
    { x: 0.5, y: 3.15, w: 12.2, h: 4.0, margin: 4 }
  );
}

// ══════════════════════════════════════════════
// SLIDE 3 — Gating Reduction by Feature
// ══════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.3, h: 0.72,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  s.addText("Gating Reduction by Feature", {
    x: 0.4, y: 0, w: 12, h: 0.72,
    fontSize: 22, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0,
  });

  const headers = ["Feature", "Current Gating", "STP Gating", "Reduction", "Reduction %", "Device-Specific"];
  const tableData = [
    headers.map(h => ({
      text: h,
      options: {
        bold: true, color: C.white, fill: { color: C.navy },
        fontSize: 12, fontFace: "Calibri", align: "center",
      },
    })),
    ...features.map((f, idx) => {
      const red    = f.current_gating - f.stp_gating;
      const redPct = f.current_gating > 0 ? (red / f.current_gating * 100).toFixed(1) + "%" : "—";
      const bg     = idx % 2 === 0 ? C.white : C.rowalt;
      const rc     = red > 0 ? C.green : red < 0 ? C.red : C.gray;
      const cell   = (txt, extra = {}) => ({
        text: String(txt),
        options: { fill: { color: bg }, fontSize: 12, fontFace: "Calibri", color: C.dark, align: "center", ...extra },
      });
      return [
        { text: f.name, options: { fill: { color: bg }, fontSize: 12, fontFace: "Calibri", bold: true, color: C.navy, align: "left" } },
        cell(f.current_gating),
        cell(f.stp_gating),
        cell(red > 0 ? `−${red}` : red, { color: rc, bold: true }),
        cell(redPct, { color: rc, bold: true }),
        cell(f.device_count || 0, { color: C.orange, bold: (f.device_count || 0) > 0 }),
      ];
    }),
  ];

  s.addTable(tableData, {
    x: 0.4, y: 0.95, w: 12.4,
    colW: [2.2, 2.0, 2.0, 2.0, 2.0, 2.2],
    border: { pt: 0.5, color: "D1D9FF" },
    rowH: 0.46,
  });
}

// ══════════════════════════════════════════════
// SLIDE 4 — Priority Distribution Chart
// ══════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.3, h: 0.72,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  s.addText("Priority Distribution — Current vs STP", {
    x: 0.4, y: 0, w: 12, h: 0.72,
    fontSize: 22, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0,
  });

  const totals = { Gating: [0, 0], High: [0, 0], Medium: [0, 0], Low: [0, 0] };
  features.forEach(f => {
    (f.summary || []).forEach(row => {
      if (totals[row.priority]) {
        totals[row.priority][0] += row.current;
        totals[row.priority][1] += row.stp;
      }
    });
  });

  const labels  = ["Gating", "High", "Medium", "Low"];
  const current = labels.map(l => totals[l][0]);
  const stp     = labels.map(l => totals[l][1]);

  s.addChart(pres.charts.BAR, [
    { name: "Current", labels, values: current },
    { name: "STP",     labels, values: stp },
  ], {
    x: 0.6, y: 0.9, w: 12.0, h: 5.9,
    barDir: "col",
    barGrouping: "clustered",
    chartColors: [C.amber, C.accent],
    chartArea: { fill: { color: C.lightbg }, roundedCorners: false },
    catAxisLabelColor: C.gray,
    valAxisLabelColor: C.gray,
    valGridLine: { color: "DDE3F5", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelColor: C.dark,
    dataLabelFontSize: 11,
    showLegend: true,
    legendPos: "b",
    legendFontSize: 12,
  });
}

// ══════════════════════════════════════════════
// SLIDE 5 — Full Priority Breakdown per Feature
// ══════════════════════════════════════════════
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.3, h: 0.72,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  s.addText("Feature Detail — Full Priority Breakdown", {
    x: 0.4, y: 0, w: 12, h: 0.72,
    fontSize: 22, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0,
  });

  const prColors = { Gating: C.red, High: C.amber, Medium: C.blue, Low: C.green };
  const headers  = ["Feature", "Priority", "Current", "STP", "Change", "Change %"];
  const rows     = [
    headers.map(h => ({
      text: h,
      options: {
        bold: true, color: C.white, fill: { color: C.navy },
        fontSize: 11, fontFace: "Calibri", align: "center",
      },
    })),
  ];

  let rowIdx = 0;
  features.forEach(f => {
    (f.summary || []).forEach(row => {
      const bg     = rowIdx % 2 === 0 ? C.white : C.rowalt;
      const chgCol = row.change < 0 ? C.green : row.change > 0 ? C.red : C.gray;
      const prCol  = prColors[row.priority] || C.gray;
      const cell   = (txt, extra = {}) => ({
        text: String(txt),
        options: { fill: { color: bg }, fontSize: 11, fontFace: "Calibri", color: C.dark, align: "center", ...extra },
      });
      rows.push([
        { text: f.name, options: { fill: { color: bg }, fontSize: 11, fontFace: "Calibri", bold: true, color: C.navy, align: "left" } },
        cell(row.priority, { color: prCol, bold: true }),
        cell(row.current),
        cell(row.stp),
        cell(row.change !== 0 ? (row.change > 0 ? `+${row.change}` : row.change) : "—", { color: chgCol, bold: row.change !== 0 }),
        cell(row.change_pct !== 0 ? `${row.change_pct > 0 ? "+" : ""}${row.change_pct}%` : "—", { color: chgCol }),
      ]);
      rowIdx++;
    });
  });

  s.addTable(rows, {
    x: 0.4, y: 0.9, w: 12.4,
    colW: [2.2, 1.9, 1.8, 1.8, 1.9, 1.8],
    border: { pt: 0.5, color: "D1D9FF" },
    rowH: 0.38,
  });
}

pres.writeFile({ fileName: outPath })
  .then(() => console.log("OK:" + outPath))
  .catch(e  => { console.error("ERR:" + e.message); process.exit(1); });
