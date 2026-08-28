"""Liest die Jahrestabelle 'stauinhalt_<BETRIEBSJAHR>.pdf' der Bezirksregierung Arnsberg.

Seit August 2025 veroeffentlicht die BRA keine Einzelberichte mehr, sondern eine
Jahrestabelle je Betriebsjahr (1.11. bis 15.10.). Sie besteht aus zwei
Halbjahrestabellen:
    Tabelle 1: 1.11 15.11 1.12 15.12 | 1.1 ... 15.4
    Tabelle 2: 1.5 ... 15.10
Datumsspalten ohne Jahr - Monat 11/12 gehoert zum Vorjahr des Betriebsjahres.
Jede Zelle enthaelt "<Inhalt Mio m3> <Fuellgrad %>", noch nicht erreichte
Stichtage stehen als "0,00 0,00".

Die Spaltenzuordnung ist nur ueber die Tabellenstruktur eindeutig, nicht ueber
den Rohtext - deshalb pdfplumber statt pypdf.

Ergebnis: fuellstaende_jahr.csv / .json (Schema wie fuellstaende.csv)
"""
import csv, io, json, re, sys, urllib.parse, urllib.request

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8")

BASIS = "https://www.bra.nrw.de/system/files/media/document/file/"
SAMMELSEITE = ("https://www.bra.nrw.de/umwelt-gesundheit-arbeitsschutz/umwelt/"
               "wasserwirtschaft-und-gewaesserschutz/talsperren/"
               "talsperrenfuellstaende-2015-bis-2026")
STAURAUM = {"Obernautalsperre": 14.9, "Breitenbachtalsperre": 7.8}
DATUMSKOPF = re.compile(r"^(\d{1,2})\.(\d{1,2})$")
PAAR = re.compile(r"(-?\d+(?:,\d+)?)\s+(-?\d+(?:,\d+)?)")


def zahl(s):
    return float(s.replace(".", "").replace(",", "."))


def hol(betriebsjahr):
    url = f"{BASIS}stauinhalt_{betriebsjahr}.pdf"
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=180) as r:
            return r.read(), url
    except Exception:
        pass

    try:
        req = urllib.request.Request(SAMMELSEITE, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            html = r.read().decode("utf-8", "replace")
        links = sorted({
            urllib.parse.urljoin(SAMMELSEITE, p)
            for p in re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I)
            if re.search(rf"/{betriebsjahr}-\d{{2}}-\d{{2}}_talsperrenfuellstaende\.pdf", p)
        })
        url = links[-1]
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=180) as r:
            return r.read(), url
    except Exception as e:
        print(f"  Betriebsjahr {betriebsjahr} -> {e}")
        return None, url


def tabelle_auswerten(tab, betriebsjahr, quelle):
    """Kopfzeile mit Datumsspalten finden, dann die Talsperrenzeilen lesen."""
    spalten = {}
    for zeile in tab[:3]:
        for i, z in enumerate(zeile or []):
            m = DATUMSKOPF.match((z or "").strip())
            if m:
                tag, monat = int(m.group(1)), int(m.group(2))
                jahr = betriebsjahr - 1 if monat >= 11 else betriebsjahr
                spalten[i] = f"{jahr:04d}-{monat:02d}-{tag:02d}"
        if spalten:
            break
    if not spalten:
        return []

    treffer = []
    for zeile in tab:
        text = " ".join(str(z) for z in zeile if z)
        name = ("Obernautalsperre" if "bernautalsperre" in text else
                "Breitenbachtalsperre" if "reitenbachtalsperre" in text else None)
        if not name:
            continue
        for i, datum in spalten.items():
            if i >= len(zeile):
                continue
            m = PAAR.search((zeile[i] or "").strip())
            if not m:
                continue
            inhalt, proz = zahl(m.group(1)), zahl(m.group(2))
            if inhalt == 0 and proz == 0:
                continue          # Stichtag noch nicht erreicht
            if not (0 < proz <= 105) or inhalt > STAURAUM[name] + 0.5:
                continue
            treffer.append({"datum": datum, "talsperre": name,
                            "fuellgrad_pct": round(proz, 2),
                            "inhalt_mio_m3": round(inhalt, 3), "quelle": quelle})
    return treffer


def main(jahre):
    zeilen = []
    for bj in jahre:
        daten, url = hol(bj)
        if not daten:
            continue
        with pdfplumber.open(io.BytesIO(daten)) as pdf:
            for seite in pdf.pages:
                for tab in seite.extract_tables():
                    zeilen.extend(tabelle_auswerten(tab, bj, url))
        print(f"  Betriebsjahr {bj}: {len(zeilen)} Messwerte kumuliert")

    einmalig = {}
    for z in zeilen:
        einmalig[(z["datum"], z["talsperre"])] = z
    zeilen = sorted(einmalig.values(), key=lambda z: (z["datum"], z["talsperre"]))

    print(f"\n{len(zeilen)} Messwerte")
    if zeilen:
        print(f"Zeitraum {zeilen[0]['datum']} bis {zeilen[-1]['datum']}")
        for z in zeilen:
            print(f"   {z['datum']}  {z['talsperre']:22s} "
                  f"{z['fuellgrad_pct']:6.2f} %  {z['inhalt_mio_m3']:6.2f} Mio m3")

    with open("fuellstaende_jahr.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, delimiter=";", fieldnames=[
            "datum", "talsperre", "fuellgrad_pct", "inhalt_mio_m3", "quelle"])
        w.writeheader()
        w.writerows(zeilen)
    json.dump(zeilen, open("fuellstaende_jahr.json", "w", encoding="utf-8"), indent=1)
    print("-> fuellstaende_jahr.csv")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [2024, 2025, 2026, 2027])
