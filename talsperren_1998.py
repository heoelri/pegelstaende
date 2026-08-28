"""Extrahiert die Talsperren-Fuellstaende ab 1998 aus dem Wayback-Archiv der
ALTEN Domain bezreg-arnsberg.nrw.de (Dezernat 54).

Seiten: .../talsperren/fuellstaende/<JAHR>/<TT>_<MM>_<JJ>.html
Inhalt: dieselbe Tabelle wie die spaeteren PDFs, mit Zeile
        "Obernautalsperre 14,9 8,66 58,12 8,93"
        (Vollstau | akt. Stauinhalt | Inhalt % | Veraenderung % zum Vormonat)

Ergebnis: fuellstaende_alt.csv / .json  (Schema wie fuellstaende.csv)
"""
import csv, html, json, os, re, sys, time, urllib.parse, urllib.request

CDX = "http://web.archive.org/cdx/search/cdx"
CACHE = "cache_alt"
STAURAUM = {"Obernautalsperre": 14.9, "Breitenbachtalsperre": 7.8}
os.makedirs(CACHE, exist_ok=True)


def hol(url):
    pfad = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", url)[-150:])
    if os.path.exists(pfad):
        return open(pfad, "rb").read()
    for versuch in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                daten = r.read()
            open(pfad, "wb").write(daten)
            return daten
        except Exception as e:
            print(f"    Versuch {versuch+1}: {e}", file=sys.stderr)
            time.sleep(3 * (versuch + 1))
    return b""


def cdx(url, filt=None, limit=5000):
    p = {"url": url, "output": "json", "collapse": "urlkey", "limit": str(limit)}
    if filt:
        p["filter"] = filt
    try:
        rows = json.loads(hol(CDX + "?" + urllib.parse.urlencode(p)).decode() or "[]")
    except json.JSONDecodeError:
        return []
    return rows[1:] if rows else []


def seiten():
    gefunden = {}
    for url, filt in [
        ("bezreg-arnsberg.nrw.de*", "urlkey:.*talsperr.*fuellstaende.*"),
        ("bezreg-arnsberg.nrw.de*", "urlkey:.*dezernat54.*"),
    ]:
        rows = cdx(url, filt)
        print(f"  CDX {filt}: {len(rows)} Zeilen")
        for r in rows:
            ts, orig, status = r[1], r[2], r[4]
            if status == "200" and "fuellstaende/" in orig and orig.endswith(".html") \
                    and not orig.endswith("index.html"):
                gefunden.setdefault(orig, ts)
    return gefunden


ZAHL = r"(\d[\d.,]*)"
ZEILE = re.compile(r"(Obernau|Breitenbach)\w*" + (r"\s+" + ZAHL) * 3, re.I)
STAND = re.compile(r"Stand:\s*(\d{1,2})\.(\d{1,2})\.(\d{4})")


def zu_float(s):
    """Die Seiten wechseln ab Q4/2002 von deutschem Komma auf englischen Punkt.
    ponytail: Komma entscheidet ueber das Format - fuer diese Talsperren bleiben
    alle Werte dreistellig, Tausendertrenner treten nie auf."""
    s = s.strip(".,")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return float(s)


def datum_aus_name(url):
    """Rueckfall, falls 'Stand:' fehlt. Ordnerjahr entscheidet TT_MM_JJ vs JJ_MM_TT."""
    m = re.search(r"fuellstaende/(\d{4})/(\d{2})_(\d{2})_(\d{2})\.html?$", url)
    if not m:
        return None
    ordner = int(m.group(1))
    a, b, c = (int(m.group(i)) for i in (2, 3, 4))
    jj = ordner % 100
    if c == jj and 1 <= b <= 12 and 1 <= a <= 31:      # TT_MM_JJ
        return f"{ordner:04d}-{b:02d}-{a:02d}"
    if a == jj and 1 <= b <= 12 and 1 <= c <= 31:      # JJ_MM_TT
        return f"{ordner:04d}-{b:02d}-{c:02d}"
    return None


def parse(roh, quelle, url):
    txt = roh.decode("latin-1", "replace")
    txt = re.sub(r"<script[\s\S]*?</script>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", html.unescape(txt))

    m = STAND.search(txt)
    datum = (f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
             if m else datum_aus_name(url))
    if not datum:
        return []

    treffer = []
    for t in ZEILE.finditer(txt):
        name = ("Obernautalsperre" if t.group(1).lower().startswith("obernau")
                else "Breitenbachtalsperre")
        voll, inhalt, proz = (zu_float(t.group(i)) for i in (2, 3, 4))
        if abs(voll - STAURAUM[name]) > 0.6 or not (0 <= proz <= 105) \
                or inhalt > voll + 0.5:
            continue
        treffer.append({"datum": datum, "talsperre": name,
                        "fuellgrad_pct": round(proz, 2),
                        "inhalt_mio_m3": round(inhalt, 3), "quelle": quelle})
    return treffer


def main():
    gefunden = seiten()
    print(f"\n{len(gefunden)} archivierte Einzelseiten\n")
    zeilen, leer = [], []
    for i, (orig, ts) in enumerate(sorted(gefunden.items()), 1):
        quelle = f"https://web.archive.org/web/{ts}id_/{orig}"
        roh = hol(quelle)
        neu = parse(roh, quelle, orig) if roh else []
        if not neu:
            leer.append(orig)
        zeilen.extend(neu)
        if i % 25 == 0:
            print(f"  {i}/{len(gefunden)} Seiten, {len(zeilen)} Messwerte")

    einmalig = {}
    for z in zeilen:
        einmalig[(z["datum"], z["talsperre"])] = z
    zeilen = sorted(einmalig.values(), key=lambda z: (z["datum"], z["talsperre"]))

    print(f"\nSeiten ohne Messwerte: {len(leer)}")
    for u in leer[:10]:
        print("   ", u[-70:])
    print(f"\n{len(zeilen)} Messwerte")
    if zeilen:
        print(f"Zeitraum {zeilen[0]['datum']} bis {zeilen[-1]['datum']}")
        jahre = {}
        for z in zeilen:
            jahre[z["datum"][:4]] = jahre.get(z["datum"][:4], 0) + 1
        print("je Jahr:", dict(sorted(jahre.items())))

    # gleiches Schema wie fuellstaende.csv, damit build_daten.py es ohne Sonderfall liest
    with open("fuellstaende_alt.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, delimiter=";", fieldnames=[
            "datum", "talsperre", "fuellgrad_pct", "inhalt_mio_m3", "quelle"])
        w.writeheader()
        w.writerows(zeilen)
    json.dump(zeilen, open("fuellstaende_alt.json", "w", encoding="utf-8"), indent=1)
    print("-> fuellstaende_alt.csv")


if __name__ == "__main__":
    main()
