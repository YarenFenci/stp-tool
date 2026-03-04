#!/usr/bin/env node
const pptxgen = require("pptxgenjs");
const data    = JSON.parse(process.argv[2]);
const outPath = process.argv[3] || "STPEXECUTIVEREPORT.pptx";
const d       = data.result;

const C = {
  navy:"1E2761", dark:"0D1B4B", ice:"CADCFC", white:"FFFFFF",
  accent:"4FC3F7", green:"43A047", red:"E53935", amber:"FB8C00",
  purple:"7B1FA2", orange:"FF6F00", blue:"1E88E5", gray:"64748B",
  lightbg:"F0F4FF", rowalt:"E8EEFF",
};
const prColor = { Gating:C.red, High:C.amber, Medium:C.blue, Low:C.green };
const makeShadow = () => ({ type:"outer", blur:8, offset:3, angle:135, color:"000000", opacity:0.12 });

let pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";

// ── SLIDE 1: Title ──────────────────────────────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.dark };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.22, h:7.5, fill:{color:C.accent}, line:{color:C.accent} });
  s.addText("STP Executive Report", {
    x:0.55, y:1.7, w:12, h:1.1, fontSize:48, bold:true, color:C.white, fontFace:"Calibri", align:"left", margin:0,
  });
  s.addText("Semantic Test Prioritization — Scenario-based priority assignment with device / OS scope detection", {
    x:0.55, y:2.95, w:11.5, h:0.6, fontSize:15, color:C.ice, fontFace:"Calibri", align:"left", margin:0,
  });

  // Stats row
  const stats = [
    { label:"Total Cases",       value:String(d.total)          },
    { label:"Priority Changes",  value:String(d.changed)        },
    { label:"Scoped Cases",      value:String(d.scoped_count)   },
    { label:"Gating Before",     value:String(d.gating_before)  },
    { label:"Gating After",      value:String(d.gating_after)   },
  ];
  stats.forEach((st2, i) => {
    const cx = 0.55 + i * 2.45;
    s.addShape(pres.shapes.RECTANGLE, {
      x:cx, y:3.8, w:2.2, h:1.0,
      fill:{color:"112255"}, line:{color:C.accent, pt:1},
    });
    s.addText(st2.value, {
      x:cx, y:3.85, w:2.2, h:0.5, fontSize:26, bold:true, color:C.accent,
      fontFace:"Calibri", align:"center", margin:0,
    });
    s.addText(st2.label, {
      x:cx, y:4.35, w:2.2, h:0.35, fontSize:10, color:C.ice,
      fontFace:"Calibri", align:"center", margin:0,
    });
  });

  s.addText("Confidential — QA Team", {
    x:0.55, y:7.05, w:12, h:0.28, fontSize:10, color:C.gray, align:"left", margin:0,
  });
}

// ── SLIDE 2: Executive Summary ──────────────────────────────
{
  const reduction    = d.gating_before - d.gating_after;
  const reductionPct = d.gating_before > 0 ? ((reduction/d.gating_before)*100).toFixed(1) : "0";
  const changedPct   = d.total > 0 ? ((d.changed/d.total)*100).toFixed(1) : "0";

  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Executive Summary", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const kpis = [
    { label:"Gating Removed",     value:String(reduction),       color:C.green  },
    { label:"Gating Reduction %", value:`${reductionPct}%`,      color:C.green  },
    { label:"Gating Before",      value:String(d.gating_before), color:C.amber  },
    { label:"Gating After",       value:String(d.gating_after),  color:C.accent },
    { label:"Cases Reclassified", value:`${changedPct}%`,        color:C.blue   },
    { label:"Scoped (Device/OS)", value:String(d.scoped_count),  color:C.purple },
  ];
  kpis.forEach((k, i) => {
    const cx = 0.25 + i * 2.15;
    s.addShape(pres.shapes.RECTANGLE, {
      x:cx, y:0.9, w:1.95, h:1.55,
      fill:{color:C.white}, line:{color:C.ice, pt:1}, shadow:makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, { x:cx, y:0.9, w:1.95, h:0.1, fill:{color:k.color}, line:{color:k.color} });
    s.addText(k.value, {
      x:cx, y:1.1, w:1.95, h:0.72, fontSize:28, bold:true, color:k.color,
      fontFace:"Calibri", align:"center", margin:0,
    });
    s.addText(k.label, {
      x:cx, y:1.82, w:1.95, h:0.5, fontSize:9, color:C.gray,
      fontFace:"Calibri", align:"center", margin:0,
    });
  });

  // Scope breakdown
  const scopeEntries = Object.entries(d.scope_breakdown || {});
  const scopeStr = scopeEntries.length > 0
    ? scopeEntries.map(([k,v]) => `${k}: ${v}`).join("   |   ")
    : "None detected";

  const bullets = [
    `${reduction} Gating cases re-prioritized — ${reductionPct}% reduction in Gating scope.`,
    `${d.changed} test cases (${changedPct}%) received a priority change from the STP engine.`,
    `${d.scoped_count} device/OS-specific scenarios detected: ${scopeStr}.`,
    `${d.scoped_changed} scoped cases had their priority adjusted (non-crash Gating→High, High→Medium).`,
    `Hard crashes on specific devices/OS versions remain Gating — a crash is never acceptable.`,
  ];

  s.addText("Key Insights", {
    x:0.4, y:2.65, w:12, h:0.38, fontSize:15, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
  });
  s.addText(
    bullets.map((b, i) => ({
      text:b,
      options:{ bullet:true, breakLine:i<bullets.length-1, color:C.dark, fontSize:12, fontFace:"Calibri" }
    })),
    { x:0.5, y:3.08, w:12.2, h:4.1, margin:4 }
  );
}

// ── SLIDE 3: Priority Distribution Chart ───────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Priority Distribution — Current vs STP", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const labels  = d.summary.map(r => r.priority);
  const current = d.summary.map(r => r.current);
  const stp     = d.summary.map(r => r.stp);

  s.addChart(pres.charts.BAR, [
    { name:"Current", labels, values:current },
    { name:"STP",     labels, values:stp },
  ], {
    x:0.6, y:0.88, w:12.0, h:5.9,
    barDir:"col", barGrouping:"clustered",
    chartColors:[C.amber, C.accent],
    chartArea:{ fill:{color:C.lightbg}, roundedCorners:false },
    catAxisLabelColor:C.gray, valAxisLabelColor:C.gray,
    valGridLine:{ color:"DDE3F5", size:0.5 }, catGridLine:{ style:"none" },
    showValue:true, dataLabelColor:C.dark, dataLabelFontSize:12,
    showLegend:true, legendPos:"b", legendFontSize:12,
  });
}

// ── SLIDE 4: Priority detail table ─────────────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Priority Detail", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const headers = ["Priority", "Current Count", "STP Count", "Change", "Change %", "Direction"];
  const rows = [
    headers.map(h => ({
      text:h,
      options:{ bold:true, color:C.white, fill:{color:C.navy}, fontSize:13, fontFace:"Calibri", align:"center" },
    })),
    ...d.summary.map((row, idx) => {
      const bg     = idx % 2 === 0 ? C.white : C.rowalt;
      const chgCol = row.change < 0 ? C.green : row.change > 0 ? C.red : C.gray;
      const prc    = prColor[row.priority] || C.gray;
      const dir    = row.change < 0 ? "↓ Reduced" : row.change > 0 ? "↑ Increased" : "→ No change";
      const cell   = (txt, extra={}) => ({
        text:String(txt),
        options:{ fill:{color:bg}, fontSize:13, fontFace:"Calibri", color:C.dark, align:"center", ...extra },
      });
      return [
        { text:row.priority, options:{ fill:{color:bg}, fontSize:13, fontFace:"Calibri", bold:true, color:prc, align:"center" } },
        cell(row.current),
        cell(row.stp),
        cell(row.change !== 0 ? (row.change > 0 ? `+${row.change}` : row.change) : "—", { color:chgCol, bold:row.change!==0 }),
        cell(row.change_pct !== 0 ? `${row.change_pct > 0 ? "+" : ""}${row.change_pct}%` : "—", { color:chgCol }),
        cell(dir, { color:chgCol, bold:row.change!==0 }),
      ];
    }),
  ];

  s.addTable(rows, {
    x:1.5, y:1.0, w:10.3,
    colW:[2.0, 2.0, 2.0, 1.8, 1.8, 2.0],
    border:{ pt:0.5, color:"D1D9FF" }, rowH:0.6,
  });

  // Note about device scope
  s.addText(
    "Note: Device/OS-specific non-crash Gating → High; device/OS High → Medium. Hard crashes always remain Gating.",
    { x:0.4, y:6.8, w:12.4, h:0.4, fontSize:10, color:C.gray, fontFace:"Calibri", align:"center", italic:true, margin:0 }
  );
}

pres.writeFile({ fileName: outPath })
  .then(() => console.log("OK:" + outPath))
  .catch(e  => { console.error("ERR:"+e.message); process.exit(1); });
