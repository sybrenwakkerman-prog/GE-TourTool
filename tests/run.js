/*
 * Draait de zelftest uit tourtool.html buiten de browser om, zodat de
 * analyse te controleren is zonder telefoon in de hand.
 *
 *   node tests/run.js
 *
 * Node kent geen DOMParser, dus die staat hieronder als kleine XML-lezer.
 * De rest van de code komt letterlijk uit tourtool.html - er is maar een
 * plek waar de analyse woont.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

/* ------------------------- mini XML-parser ------------------------- */
function parseXML(src) {
  const root = mkEl("#document");
  const stack = [root];
  const re = /<([?!/]?)([A-Za-z_:][-\w.:]*)?([^>]*?)(\/?)>|([^<]+)/g;
  let m;
  while ((m = re.exec(src))) {
    const [, kind, name, attrs, selfClose, text] = m;
    if (text !== undefined) {
      const t = text.trim();
      if (t) stack[stack.length - 1].text += decode(t);
      continue;
    }
    if (kind === "?" || kind === "!") continue;
    if (kind === "/") { if (stack.length > 1) stack.pop(); continue; }
    const el = mkEl(name);
    (attrs || "").replace(/([-\w:.]+)\s*=\s*"([^"]*)"/g, (_, k, v) => { el.attrs[k] = decode(v); return ""; });
    stack[stack.length - 1].children.push(el);
    if (!selfClose) stack.push(el);
  }
  return root;
}
function decode(s) {
  return s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'").replace(/&amp;/g, "&");
}
function mkEl(nodeName) {
  const el = {
    nodeName, localName: nodeName.split(":").pop(), attrs: {}, children: [], text: "",
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    get textContent() {
      let t = this.text;
      for (const c of this.children) t += c.textContent;
      return t;
    },
    getElementsByTagName(tag) {
      const out = [];
      (function walk(n) {
        for (const c of n.children) {
          if (tag === "*" || c.nodeName === tag) out.push(c);
          walk(c);
        }
      })(el);
      return out;
    }
  };
  return el;
}
class DOMParser {
  parseFromString(src) { return parseXML(src); }
}

/* ------------------ script uit de HTML trekken --------------------- */
const html = fs.readFileSync(path.join(__dirname, "..", "tourtool.html"), "utf8");
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (blocks.length < 1) { console.error("scriptblok niet gevonden"); process.exit(1); }

const ctx = vm.createContext({ DOMParser, console, Date, Math, JSON, isFinite, isNaN, parseFloat, parseInt,
  Float64Array, Set, Map, Object, Array, String, Number, Error });
for (const b of blocks) {
  // De UI-code hangt aan document; die slaan we over.
  vm.runInContext(b.replace(/^\s*"use strict";/, ""), ctx, { filename: "tourtool.html" });
}

/* ----------------------------- draaien ----------------------------- */
const t0 = Date.now();
const res = vm.runInContext("runSelfTest()", ctx);
const ms = Date.now() - t0;

let fail = 0;
for (const a of res) {
  if (!a.ok) fail++;
  const mark = a.ok ? "  ok  " : " FOUT ";
  console.log(mark + a.naam + (a.detail ? "\n         " + a.detail : ""));
}
console.log("\n" + res.length + " controles, " + fail + " gefaald, " + ms + " ms");

/* ------------- extra: de echte dag-GPX'en er doorheen ---------------
 * De zelftest gebruikt gesimuleerde sporen. Hier gaan de echte Komoot-
 * bestanden door dezelfde molen, om te zien of de projectie en de
 * afstandscontrole ook op echte data kloppen.
 */
const gpxDir = path.join(__dirname, "..", "gpx");
const dagen = vm.runInContext("DEFAULT_DAYS", ctx);
console.log("\nechte dagbestanden:");
let realFail = 0;
dagen.forEach((d, i) => {
  const f = path.join(gpxDir, "dag" + (i + 1) + ".gpx");
  if (!fs.existsSync(f)) return;
  ctx.__gpx = fs.readFileSync(f, "utf8");
  ctx.__naam = d.label;
  const r = vm.runInContext('buildRider(__naam, 82, parseGPX(__gpx), "#38bdf8")', ctx);
  const routeKm = d.endKm - d.startKm;
  const afw = Math.abs(r.trackKm - routeKm) / routeKm * 100;
  const startOk = Math.abs(r.kmStart - d.startKm) < 1;
  const eindOk = Math.abs(r.kmEnd - d.endKm) < 1;
  const distOk = afw <= 5;
  let sum = 0, cnt = 0, worst = 0;
  for (let k = 0; k < r.n; k++) if (!isNaN(r.off[k])) { sum += r.off[k]; cnt++; worst = Math.max(worst, r.off[k]); }
  const projOk = cnt > 0 && sum / cnt < 20;
  const allOk = startOk && eindOk && distOk && projOk;
  if (!allOk) realFail++;
  console.log((allOk ? "  ok  " : " FOUT ") + d.label +
    ": spoor " + r.trackKm.toFixed(1) + " km tegen " + routeKm.toFixed(1) + " km route (" +
    afw.toFixed(1) + "% afwijking)");
  console.log("         projecteert op km " + r.kmStart.toFixed(1) + " tot " + r.kmEnd.toFixed(1) +
    " (verwacht " + d.startKm.toFixed(1) + " tot " + d.endKm.toFixed(1) + "), " +
    "gemiddeld " + (sum / cnt).toFixed(1) + " m naast de route, uitschieter " + Math.round(worst) + " m");
});
if (realFail) fail += realFail;

const meta = vm.runInContext("ROUTE_META", ctx);
console.log("\nroute: " + meta.totalKm + " km, +" + meta.gainM + " hm, top " + meta.maxEleM + " m, "
  + meta.points + " punten");
console.log("dagen: " + JSON.stringify(vm.runInContext("DEFAULT_DAYS", ctx)));
console.log("segmenten: " + vm.runInContext("DEFAULT_SEGMENTS", ctx)
  .map(s => s.name + " km " + s.startKm + "-" + s.endKm).join(", "));

process.exit(fail ? 1 : 0);
