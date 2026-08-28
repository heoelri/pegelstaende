/* Selbsttest fuer trendlinie() und kanal() aus index.html.  Aufruf: node test_trend.js */
const assert = require("assert");
const fs = require("fs");

const html = fs.readFileSync("index.html", "utf8");
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join("\n");
new Function(js); // Syntaxpruefung des gesamten SPA-Skripts

const hol = name => js.match(new RegExp(`function ${name}\\([\\s\\S]*?\\n}`))[0];
const {trendlinie, kanal} = new Function(
  `${hol("trendlinie")}\n${hol("kanal")}\nreturn {trendlinie, kanal};`)();
const {saisonNormal, korrWert} = new Function(
  `const ms = s => new Date(s + "T12:00:00Z").getTime();
   ${hol("median")}
   ${hol("saisonNormal")}
   ${hol("datensatzAm")}
   ${hol("korrWert")}
   return {saisonNormal, korrWert};`)();

const JAHR = 31557600000, tag = (y, m, d) => Date.UTC(y, m - 1, d);

// 1) exakte Gerade: 10 %-Punkte pro Jahr
const t = trendlinie([{x:tag(2020,1,1), y:0}, {x:tag(2021,1,1), y:10}, {x:tag(2022,1,1), y:20}]);
assert.ok(Math.abs(t.proJahr - 10) < 0.1, "Steigung falsch: " + t.proJahr);
assert.ok(Math.abs(t.punkte[0].y - 0) < 0.1 && Math.abs(t.punkte[1].y - 20) < 0.1);

// 2) zu wenig Punkte -> keine Gerade
assert.strictEqual(trendlinie([{x:1, y:1}]), null);
assert.strictEqual(trendlinie([]), null);

// 3) Kanal: Saegezahn mit Maxima 90->80 und Minima 50->30 ueber 3 Jahre
const saege = [];
for (let i = 0; i < 3; i++) {
  saege.push({x:tag(2020 + i, 5, 1), y:90 - 5 * i});
  saege.push({x:tag(2020 + i, 10, 1), y:50 - 10 * i});
}
const k = kanal(saege);
assert.ok(k.oben.proJahr < 0 && k.unten.proJahr < 0, "beide Trends muessen fallen");
assert.ok(Math.abs(k.oben.proJahr + 5) < 0.5, "Topline: " + k.oben.proJahr);
assert.ok(Math.abs(k.unten.proJahr + 10) < 0.5, "Bottomline: " + k.unten.proJahr);
assert.ok(k.oben.punkte[0].y > k.unten.punkte[0].y, "Topline muss oben liegen");
// beide Geraden spannen den vollen Zeitraum
assert.strictEqual(k.oben.punkte[0].x, k.unten.punkte[0].x);
assert.strictEqual(k.oben.punkte[1].x, Math.max(...saege.map(p => p.x)));

// 4) Kanal auf den echten Daten
const src = fs.readFileSync("daten.js", "utf8");
const D = JSON.parse(src.slice(src.indexOf("["), src.lastIndexOf("]") + 1));
for (const dam of ["Obernautalsperre", "Breitenbachtalsperre"]) {
  const pts = D.filter(r => r.t === dam).map(r => ({x:Date.parse(r.d), y:r.p}));
  const kk = kanal(pts);
  assert.ok(kk.oben && kk.unten, dam + ": Kanal fehlt");
  assert.ok(kk.oben.punkte.every((p, i) => p.y > kk.unten.punkte[i].y),
    dam + ": Topline schneidet Bottomline");
  console.log(`${dam}: Höchststände ${kk.oben.proJahr.toFixed(2)} , ` +
    `Tiefststände ${kk.unten.proJahr.toFixed(2)} %-Pkt./Jahr`);
}

// 5) Einzeljahr -> keine Gerade, aber kein Absturz
const einJahr = D.filter(r => r.t === "Obernautalsperre" && r.d.startsWith("2020"))
                 .map(r => ({x:Date.parse(r.d), y:r.p}));
assert.strictEqual(kanal(einJahr).oben, null);

// 6) Saisonnormal: gleicher Halbmonat, nur amtliche Vorjahre
const normal = saisonNormal(
  {d:"2022-08-21", t:"Obernautalsperre", p:50},
  [
    {d:"2020-08-15", t:"Obernautalsperre", p:60, amtlich:true},
    {d:"2021-08-20", t:"Obernautalsperre", p:80, amtlich:true},
    {d:"2021-08-20", t:"Obernautalsperre", p:99, amtlich:false},
    {d:"2021-08-01", t:"Obernautalsperre", p:10, amtlich:true}
  ]);
assert.deepStrictEqual(normal, {wert:70, n:2});

// 7) Korrelationswert folgt der Auswahl; gemeinsam nach 22,7 Mio. m3 gewichtet
const paar = [
  {d:"2020-01-01", t:"Obernautalsperre", p:50, m:7.45},
  {d:"2020-01-01", t:"Breitenbachtalsperre", p:50, m:3.9}
];
assert.strictEqual(korrWert("2020-01-01", ["Breitenbachtalsperre"], paar), 50);
assert.ok(Math.abs(korrWert("2020-01-01",
  ["Obernautalsperre", "Breitenbachtalsperre"], paar) - 50) < 0.001);
assert.strictEqual(korrWert("2020-01-01",
  ["Obernautalsperre", "Breitenbachtalsperre"], paar.slice(0, 1)), null);
assert.strictEqual(korrWert("2020-03-01", ["Obernautalsperre"], paar), null);

console.log("alle Tests bestanden");
