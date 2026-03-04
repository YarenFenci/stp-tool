#!/usr/bin/env node
const pptxgen = require("pptxgenjs");
const data     = JSON.parse(process.argv[2]);
const outPath  = process.argv[3] || "STPEXECUTIVEREPORT.pptx";
const platforms = data.platforms || [];

const C = {
  navy: "1E2761", dark: "0D1B4B", ice: "CADCFC", white: "FFFFFF",
  accent: "4FC3F7", green: "43A047", red: "E53935", amber: "FB8C00",
  orange: "FF6F00", blue: "1E88E5", purple: "9C27B0",
  gray: "64748B", lightbg: "F0F4FF", rowalt: "E8EEFF",
  android: "3DDC84", ios: "007AFF",
};
const platColor = { "Android": C.android, "iOS": C.ios, "Both": C.purple };
const makeShadow = () => ({ type:"outer", blur:8, offset:3, angle:135, color:"000000", opacity:0.12 });

let pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";

// ── SLIDE 1: Title ──────────────────────────────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.dark };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.22, h:7.5, fill:{color:C.accent}, line:{color:C.accent} });
  s.addText("STP Executive Report", {
    x:0.55, y:1.6, w:12, h:1.2, fontSize:48, bold:true, color:C.white, fontFace:"Calibri", align:"left", margin:0,
  });
  s.addText("Semantic Test Prioritization — Platform-aware scenario-based priority rebalancing", {
    x:0.55, y:2.95, w:11, h:0.6, fontSize:16, color:C.ice, fontFace:"Calibri", align:"left", margin:0,
  });

  let px = 0.55;
  platforms.forEach(p => {
    const w   = Math.max(1.2, p.name.length * 0.15 + 0.5);
    const col = platColor[p.name] || C.accent;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x:px, y:3.85, w, h:0.42, fill:{color:C.navy}, line:{color:col, pt:2}, rectRadius:0.08,
    });
    s.addText(p.name, {
      x:px, y:3.85, w, h:0.42, fontSize:13, color:col, bold:true,
      align:"center", fontFace:"Calibri", margin:0,
    });
    px += w + 0.22;
  });

  s.addText("Confidential — QA Team", {
    x:0.55, y:7.05, w:12, h:0.3, fontSize:10, color:C.gray, align:"left", margin:0,
  });
}

// ── SLIDE 2: Executive Summary ──────────────────────────────
{
  const totalFalseGating = platforms.reduce((s,p) => s + (p.current_gating - p.stp_gating), 0);
  const totalTests       = platforms.reduce((s,p) => s + (p.total_current || 0), 0);
  const totalGatBefore   = platforms.reduce((s,p) => s + p.current_gating, 0);
  const totalGatAfter    = platforms.reduce((s,p) => s + p.stp_gating, 0);
  const totalDevice      = platforms.reduce((s,p) => s + (p.device_count || 0), 0);
  const totalUiEdge      = platforms.reduce((s,p) => s + (p.ui_edge_count || 0), 0);
  const shareBefore      = totalTests ? (totalGatBefore/totalTests*100).toFixed(1) : "—";
  const shareAfter       = totalTests ? (totalGatAfter/totalTests*100).toFixed(1) : "—";
  const reduction        = totalGatBefore ? ((totalFalseGating/totalGatBefore)*100).toFixed(1) : "0";

  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Executive Summary", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const kpis = [
    { label:"False Gating Removed",  value:String(totalFalseGating), color:C.green  },
    { label:"Gating Share Before",   value:`${shareBefore}%`,        color:C.amber  },
    { label:"Gating Share After",    value:`${shareAfter}%`,         color:C.accent },
    { label:"Gating Reduction",      value:`${reduction}%`,          color:C.green  },
    { label:"Device-Specific Cases", value:String(totalDevice),      color:C.orange },
    { label:"UI Edge → Low",         value:String(totalUiEdge),      color:C.blue   },
  ];

  kpis.forEach((k, i) => {
    const cx = 0.25 + i * 2.15;
    s.addShape(pres.shapes.RECTANGLE, {
      x:cx, y:0.92, w:1.95, h:1.55,
      fill:{color:C.white}, line:{color:C.ice, pt:1}, shadow:makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, { x:cx, y:0.92, w:1.95, h:0.1, fill:{color:k.color}, line:{color:k.color} });
    s.addText(k.value, {
      x:cx, y:1.1, w:1.95, h:0.72, fontSize:28, bold:true, color:k.color,
      fontFace:"Calibri", align:"center", margin:0,
    });
    s.addText(k.label, {
      x:cx, y:1.82, w:1.95, h:0.5, fontSize:9, color:C.gray,
      fontFace:"Calibri", align:"center", margin:0,
    });
  });

  const bullets = [
    `${totalFalseGating} test cases were incorrectly marked as Gating and re-prioritized by STP.`,
    `Gating share dropped from ${shareBefore}% to ${shareAfter}% across all platforms.`,
    `${totalUiEdge} UI/cosmetic edge cases downgraded to Low — visual only, no functional impact.`,
    `${totalDevice} device-specific scenarios flagged for QA review (priority unchanged).`,
    `Deterministic engine: same CSV always produces the same output.`,
  ];

  s.addText("Key Insights", {
    x:0.4, y:2.68, w:12, h:0.38, fontSize:15, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
  });
  s.addText(
    bullets.map((b, i) => ({
      text: b,
      options: { bullet:true, breakLine: i < bullets.length-1, color:C.dark, fontSize:12, fontFace:"Calibri" }
    })),
    { x:0.5, y:3.1, w:12.2, h:4.0, margin:4 }
  );
}

// ── SLIDE 3: Platform comparison table ─────────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Gating Reduction by Platform", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const headers = ["Platform", "Total Cases", "Current Gating", "STP Gating", "Reduction", "Reduction %", "Device-Specific", "UI Edge → Low"];
  const tableData = [
    headers.map(h => ({
      text: h,
      options: { bold:true, color:C.white, fill:{color:C.navy}, fontSize:11, fontFace:"Calibri", align:"center" },
    })),
    ...platforms.map((p, idx) => {
      const red    = p.current_gating - p.stp_gating;
      const redPct = p.current_gating > 0 ? (red/p.current_gating*100).toFixed(1)+"%" : "—";
      const bg     = idx % 2 === 0 ? C.white : C.rowalt;
      const rc     = red > 0 ? C.green : red < 0 ? C.red : C.gray;
      const pc     = platColor[p.name] || C.gray;
      const cell   = (txt, extra={}) => ({
        text: String(txt),
        options: { fill:{color:bg}, fontSize:11, fontFace:"Calibri", color:C.dark, align:"center", ...extra },
      });
      return [
        { text:p.name, options:{ fill:{color:bg}, fontSize:12, fontFace:"Calibri", bold:true, color:pc, align:"center" } },
        cell(p.total_current),
        cell(p.current_gating),
        cell(p.stp_gating),
        cell(red > 0 ? `−${red}` : String(red), { color:rc, bold:true }),
        cell(redPct, { color:rc, bold:true }),
        cell(p.device_count || 0, { color:C.orange, bold:(p.device_count||0)>0 }),
        cell(p.ui_edge_count || 0, { color:C.blue,   bold:(p.ui_edge_count||0)>0 }),
      ];
    }),
  ];

  s.addTable(tableData, {
    x:0.4, y:0.92, w:12.4,
    colW:[1.6, 1.5, 1.6, 1.5, 1.4, 1.4, 1.7, 1.7],
    border:{ pt:0.5, color:"D1D9FF" }, rowH:0.5,
  });
}

// ── SLIDE 4: Priority Distribution Chart ───────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Priority Distribution — Current vs STP", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const totals = { Gating:[0,0], High:[0,0], Medium:[0,0], Low:[0,0] };
  platforms.forEach(p => {
    (p.summary||[]).forEach(r => {
      if (totals[r.priority]) { totals[r.priority][0]+=r.current; totals[r.priority][1]+=r.stp; }
    });
  });
  const labels  = ["Gating","High","Medium","Low"];
  const current = labels.map(l => totals[l][0]);
  const stp     = labels.map(l => totals[l][1]);

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
    showValue:true, dataLabelColor:C.dark, dataLabelFontSize:11,
    showLegend:true, legendPos:"b", legendFontSize:12,
  });
}

// ── SLIDE 5: Full breakdown per platform ───────────────────
{
  let s = pres.addSlide();
  s.background = { color: C.lightbg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:13.3, h:0.72, fill:{color:C.navy}, line:{color:C.navy} });
  s.addText("Full Priority Breakdown by Platform", {
    x:0.4, y:0, w:12, h:0.72, fontSize:22, bold:true, color:C.white,
    fontFace:"Calibri", align:"left", valign:"middle", margin:0,
  });

  const prColors = { Gating:C.red, High:C.amber, Medium:C.blue, Low:C.green };
  const headers  = ["Platform", "Priority", "Current", "STP", "Change", "Change %"];
  const rows = [
    headers.map(h => ({
      text:h,
      options:{ bold:true, color:C.white, fill:{color:C.navy}, fontSize:11, fontFace:"Calibri", align:"center" },
    })),
  ];

  let ri = 0;
  platforms.forEach(p => {
    const pc = platColor[p.name] || C.gray;
    (p.summary||[]).forEach(row => {
      const bg     = ri % 2 === 0 ? C.white : C.rowalt;
      const chgCol = row.change < 0 ? C.green : row.change > 0 ? C.red : C.gray;
      const prc    = prColors[row.priority] || C.gray;
      const cell   = (txt, extra={}) => ({
        text:String(txt),
        options:{ fill:{color:bg}, fontSize:11, fontFace:"Calibri", color:C.dark, align:"center", ...extra },
      });
      rows.push([
        { text:p.name, options:{ fill:{color:bg}, fontSize:11, fontFace:"Calibri", bold:true, color:pc, align:"center" } },
        cell(row.priority, { color:prc, bold:true }),
        cell(row.current),
        cell(row.stp),
        cell(row.change!==0 ? (row.change>0?`+${row.change}`:row.change) : "—", { color:chgCol, bold:row.change!==0 }),
        cell(row.change_pct!==0 ? `${row.change_pct>0?"+":""}${row.change_pct}%` : "—", { color:chgCol }),
      ]);
      ri++;
    });
  });

  s.addTable(rows, {
    x:0.4, y:0.9, w:12.4,
    colW:[2.2, 2.0, 1.9, 1.9, 2.0, 2.0],
    border:{ pt:0.5, color:"D1D9FF" }, rowH:0.38,
  });
}

pres.writeFile({ fileName: outPath })
  .then(() => console.log("OK:" + outPath))
  .catch(e  => { console.error("ERR:"+e.message); process.exit(1); });
