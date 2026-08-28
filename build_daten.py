"""Erzeugt daten.js fuer die SPA: fuehrt alle extrahierten Zeitreihen zusammen."""
import csv, glob, json, pathlib, sys

sys.stdout.reconfigure(encoding="utf-8")

NAMEN = {"Obernau": "Obernautalsperre", "Breitenbach": "Breitenbachtalsperre"}
best = {}   # (Datum, Talsperre) -> Datensatz

for pfad in sorted(glob.glob("fuellstaende*.csv")):
    with open(pfad, encoding="utf8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            t = NAMEN.get(r["talsperre"], r["talsperre"])
            best.setdefault((r["datum"], t), {
                "d": r["datum"], "t": t,
                "p": round(float(r["fuellgrad_pct"]), 2),
                "m": round(float(r["inhalt_mio_m3"]), 2),
                "q": r["quelle"],
            })
    print(f"gelesen: {pfad}")

rows = sorted(best.values(), key=lambda r: (r["d"], r["t"]))
pathlib.Path("daten.js").write_text(
    "// Amtliche Fuellstaende der Bezirksregierung Arnsberg (Dezernat 54 Wasserwirtschaft),\n"
    "// automatisch extrahiert aus der Berichtsreihe 'Talsperrenfuellstaende' (Stichtage 1. und 15.).\n"
    "const FUELLSTAENDE = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n",
    encoding="utf8")

jahre = {}
for r in rows:
    jahre[r["d"][:4]] = jahre.get(r["d"][:4], 0) + 1
print(f"\n{len(rows)} Messpunkte -> daten.js")
for j in sorted(jahre):
    print(f"  {j}: {jahre[j] // 2} Stichtage")
