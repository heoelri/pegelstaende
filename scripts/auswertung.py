"""Kurzauswertung der zusammengefuehrten Reihe fuer die textliche Zusammenfassung."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = (ROOT / "daten.js").read_text(encoding="utf-8")
D = json.loads(s[s.index("["):s.rindex("]") + 1])
print("Messpunkte:", len(D), "|", D[0]["d"], "bis", D[-1]["d"])

for dam in ("Obernautalsperre", "Breitenbachtalsperre"):
    v = [r for r in D if r["t"] == dam]
    mn, mx = min(v, key=lambda r: r["p"]), max(v, key=lambda r: r["p"])
    print(f"{dam:22s} n={len(v):3d}  min={mn['p']:6.2f}% ({mn['d']})  "
          f"max={mx['p']:6.2f}% ({mx['d']})")

print("\nJahr   Obernau min/max      Breitenbach min/max")
jahre = {}
for r in D:
    jahre.setdefault(r["d"][:4], {}).setdefault(r["t"], []).append(r["p"])
for y in sorted(jahre):
    o = jahre[y].get("Obernautalsperre", [])
    b = jahre[y].get("Breitenbachtalsperre", [])
    f = lambda v: f"{min(v):5.1f} / {max(v):5.1f}" if v else "    -      "
    print(f"{y}   {f(o)}        {f(b)}")
