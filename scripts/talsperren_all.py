"""Vollstaendige Zeitreihe der Fuellstaende von Obernau- und Breitenbachtalsperre
aus den amtlichen Berichten der Bezirksregierung Arnsberg (Dezernat 54).

Quellen: Jahresindex-Seiten talsperrenfuellstaende-<Jahr> (live + Wayback) sowie
alle im Wayback-Index gefundenen Fuellstands-PDFs.
"""
import io, json, re, sys, urllib.parse, urllib.request, pathlib, time

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Pegelstaende-Recherche)"}
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / ".cache" / "cache"; CACHE.mkdir(parents=True, exist_ok=True)
BASE = ("https://www.bra.nrw.de/umwelt-gesundheit-arbeitsschutz/umwelt/"
        "wasserwirtschaft-und-gewaesserschutz/talsperren/talsperrenfuellstaende-")
ORPHAN_PDFS = {
    "https://www.bra.nrw.de/system/files/media/document/file/2025-08-15_talsperrenfuellstaende.pdf",
    "https://www.bra.nrw.de/system/files/media/document/file/2025-09-01_talsperrenfuellstaende.pdf",
    "https://www.bra.nrw.de/system/files/media/document/file/2025-09-15_talsperrenfuellstaende.pdf",
    "https://www.bra.nrw.de/system/files/media/document/file/2025-10-01_talsperrenfuellstaende.pdf",
}


def get(url, tries=4, sleep=3):
    key = CACHE / (re.sub(r"[^A-Za-z0-9._-]", "_", url)[-120:])
    if key.exists():
        return key.read_bytes()
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                d = r.read()
            key.write_bytes(d)
            return d
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return b""
            time.sleep(sleep * (i + 1))
        except Exception:
            time.sleep(sleep * (i + 1))
    return b""


def index_pdfs(year):
    """PDF-Links einer Jahresseite - erst live, dann Wayback."""
    for u in (BASE + str(year),
              f"https://web.archive.org/web/2025id_/{BASE}{year}",
              f"https://web.archive.org/web/2023id_/{BASE}{year}"):
        h = get(u).decode("utf8", "replace")
        pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', h, re.I)
        if pdfs:
            out = set()
            for p in pdfs:
                p = re.sub(r"^https?://web\.archive\.org/web/[^/]+/", "", p)
                out.add(urllib.parse.urljoin("https://www.bra.nrw.de/", p))
            return sorted(out), u
    return [], None


def sammelseite():
    """Die aktuelle Live-Sammelseite listet alle Berichte 2015-2026."""
    u = BASE + "2015-bis-2026"
    h = get(u).decode("utf8", "replace")
    out = {urllib.parse.urljoin("https://www.bra.nrw.de/", p)
           for p in re.findall(r'href="([^"]*\.pdf[^"]*)"', h, re.I)}
    print(f"Sammelseite: {len(out)} PDFs")
    return sorted(out), u


def cdx_pdfs():
    """Wayback-Index, zwei Filter - der breite trifft die Dateien mit Datums-,
    der enge die mit Namensschema."""
    out = set()
    for f in (".*system/files.*\\.pdf", ".*[Tt]alsperrenf.*"):
        u = ("https://web.archive.org/cdx/search/cdx?url=bra.nrw.de&matchType=domain"
             "&fl=original&collapse=urlkey&limit=20000&filter=original:" + f)
        out.update(x for x in get(u).decode("utf8", "replace").split()
                   if x.lower().endswith(".pdf"))
    return sorted(out)


DATE_PATS = [
    (r"(20\d{2})-(\d{2})-(\d{2})", "ymd"),
    (r"\b(\d{2})[._-](\d{2})[._-](20\d{2})\b", "dmy"),
    (r"\b(\d{2})[._-](\d{2})[._-](\d{2})\b", "dmy2"),
    (r"^(\d{2})_(\d{2})_(\d{2})\.pdf$", "ymd2"),
]


def date_from(url):
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    m = re.match(r"^(\d{2})_(\d{2})_(\d{2})\.pdf$", name)   # YY_MM_DD.pdf
    if m:
        return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for pat, kind in DATE_PATS[:3]:
        m = re.search(pat, name)
        if not m:
            continue
        a, b, c = m.groups()
        if kind == "ymd":
            return f"{a}-{b}-{c}"
        y = c if len(c) == 4 else "20" + c
        return f"{y}-{b}-{a}"
    return None


NUM = r"(-?[\d.]+,\d+|-?\d+)"
ROW = re.compile(r"(Obernau|Breitenbach)\w*\s+" + r"\s+".join([NUM] * 3))


def parse_pdf(data):
    from pypdf import PdfReader
    try:
        txt = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return {}
    if "Sommerhalbjahr" in txt:
        return {}  # kumulierte Jahrestabelle; talsperren_jahrestabelle.py liest die Datumsspalten
    out = {}
    for m in ROW.finditer(txt.replace("\xa0", " ")):
        v = [float(x.replace(".", "").replace(",", ".")) for x in m.groups()[1:]]
        # Plausibilitaet: Stauraum muss zur Talsperre passen, Fuellgrad 0-105 %
        exp = 14.9 if m.group(1) == "Obernau" else 7.8
        if abs(v[0] - exp) < 0.6 and 0 <= v[2] <= 105:
            out[m.group(1)] = {"stauraum_mio_m3": v[0], "inhalt_mio_m3": v[1],
                               "fuellgrad_pct": v[2]}
    return out


def main():
    urls, idx_src = {}, {}
    sp, sp_src = sammelseite()
    for p in sp:
        urls[p] = sp_src
    for p in ORPHAN_PDFS:
        urls[p] = p
    for y in range(2005, 2027):
        pdfs, src = index_pdfs(y)
        for p in pdfs:
            urls[p] = src
        print(f"Index {y}: {len(pdfs)} PDFs" + (f"  ({src.split('/')[-1]})" if src else "  -"))
    for p in cdx_pdfs():
        if re.search(r"talsperren|^\d{2}_\d{2}_\d{2}\.pdf|20\d\d-\d\d-\d\d\.pdf",
                     p.rsplit("/", 1)[-1], re.I):
            urls.setdefault(p, "wayback-cdx")
    print(f"\n{len(urls)} PDF-Kandidaten gesamt\n")

    rows, misses = [], []
    for u in sorted(urls, key=lambda x: date_from(x) or "9999"):
        d = date_from(u)
        if not d:
            continue
        data = get(u)
        if data[:4] != b"%PDF":
            data = get("https://web.archive.org/web/2024id_/" + u)
        if data[:4] != b"%PDF":
            misses.append((d, u, "kein PDF")); continue
        got = parse_pdf(data)
        if not got:
            misses.append((d, u, "keine Talsperrenzeile")); continue
        for dam, v in got.items():
            rows.append({"datum": d, "talsperre": dam, **v, "quelle": u})

    # Duplikate (gleiches Datum + Talsperre) entfernen
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda r: (r["datum"], r["talsperre"])):
        k = (r["datum"], r["talsperre"])
        if k not in seen:
            seen.add(k); uniq.append(r)

    with open(DATA / "fuellstaende.csv", "w", encoding="utf8") as f:
        f.write("datum;talsperre;stauraum_mio_m3;inhalt_mio_m3;fuellgrad_pct;quelle\n")
        for r in uniq:
            f.write(";".join(str(r[k]) for k in ("datum", "talsperre", "stauraum_mio_m3",
                    "inhalt_mio_m3", "fuellgrad_pct", "quelle")) + "\n")
    (DATA / "fuellstaende.json").write_text(
        json.dumps(uniq, indent=1, ensure_ascii=False), encoding="utf8")

    years = sorted({r["datum"][:4] for r in uniq})
    print(f"{len(uniq)} eindeutige Datenpunkte, Jahre {years[0]}-{years[-1]}")
    for y in years:
        n = len([r for r in uniq if r["datum"].startswith(y)])
        print(f"  {y}: {n}")
    print(f"\n{len(misses)} Fehlschlaege")
    for m in misses[:15]:
        print("  ", m)


if __name__ == "__main__":
    main()
