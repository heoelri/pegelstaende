"""Sucht die Fuellstandsberichte 2004-2014 in allen erreichbaren Webarchiven.

Die Indexseite von 2007 belegt die Dateinamen (Schema JJ_MM_TT.html unter dem
Pfad .../aufbau/..., ab 09/2007 .xls). Offen ist, ob sie irgendwo archiviert sind.
Geprueft werden: Wayback (beide Pfadvarianten, je Jahr) und Common Crawl.
"""
import json, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Pegelstaende-Recherche)"}
ALT = "dieBezirksregierung/aufgabenAufbau/abteilungen/abteilung5/dezernat54/talsperren/fuellstaende"
NEU = "dieBezirksregierung/aufbau/abteilungen/abteilung5/dezernat54/talsperren/fuellstaende"


def hol(url, timeout=180):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == 2:
                print(f"    FEHLER {url[:80]}: {e}")
            time.sleep(4 * (i + 1))
    return ""


def wayback_jahre():
    print("=== Wayback: Jahresordner 2004-2014, beide Pfadvarianten")
    gesamt = {}
    for jahr in range(2004, 2015):
        for pfad in (ALT, NEU):
            u = ("http://web.archive.org/cdx/search/cdx?url="
                 + urllib.parse.quote(f"bezreg-arnsberg.nrw.de/{pfad}/{jahr}/", safe="")
                 + "*&output=json&collapse=urlkey&limit=500")
            roh = hol(u)
            try:
                rows = json.loads(roh or "[]")[1:]
            except json.JSONDecodeError:
                rows = []
            if rows:
                gesamt.setdefault(jahr, []).extend(rows)
        print(f"  {jahr}: {len(gesamt.get(jahr, []))} archivierte Dateien")
    return gesamt


def wayback_bra_alt():
    print("\n=== Wayback: bra.nrw.de Talsperrenseiten VOR 2015")
    u = ("http://web.archive.org/cdx/search/cdx?url=bra.nrw.de&matchType=domain"
         "&output=json&collapse=urlkey&limit=5000&filter=urlkey:.*talsperr.*"
         "&to=20150101")
    try:
        rows = json.loads(hol(u) or "[]")[1:]
    except json.JSONDecodeError:
        rows = []
    print(f"  {len(rows)} Treffer vor 2015")
    for r in rows[:40]:
        print(f"    {r[1][:8]} {r[4]} {r[2][:120]}")
    return rows


def common_crawl():
    print("\n=== Common Crawl (unabhaengig vom Wayback, Crawls ab 2008)")
    info = hol("https://index.commoncrawl.org/collinfo.json")
    try:
        slots = [c["id"] for c in json.loads(info)]
    except Exception:
        print("  collinfo nicht abrufbar")
        return []
    # nur Crawls bis 2016 - spaeter existierte die alte Domain nicht mehr
    alt = [s for s in slots if any(j in s for j in
           ("2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016"))]
    print(f"  {len(slots)} Crawls gesamt, {len(alt)} davon aus 2008-2016")
    treffer = []
    for slot in alt:
        u = (f"https://index.commoncrawl.org/{slot}-index?url="
             + urllib.parse.quote("bezreg-arnsberg.nrw.de/*", safe="")
             + "&output=json&limit=2000")
        roh = hol(u, timeout=120)
        zeilen = [z for z in roh.splitlines() if "talsperr" in z.lower()
                  or "fuellstaende" in z.lower()]
        if zeilen:
            print(f"  {slot}: {len(zeilen)} Talsperren-URLs")
            treffer.extend(zeilen)
        else:
            print(f"  {slot}: -")
    return treffer


if __name__ == "__main__":
    jahre = wayback_jahre()
    bra = wayback_bra_alt()
    cc = common_crawl()
    json.dump({"wayback_jahre": {str(k): v for k, v in jahre.items()},
               "bra_vor_2015": bra, "common_crawl": cc},
              open("suche_2004_2014.json", "w", encoding="utf-8"), indent=1)
    print(f"\nErgebnis: Wayback-Jahresdateien {sum(len(v) for v in jahre.values())}, "
          f"bra.nrw.de vor 2015 {len(bra)}, Common Crawl {len(cc)}")
