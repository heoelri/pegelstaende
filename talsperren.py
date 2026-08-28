"""Zieht die Talsperrenfuellstaende-Berichte der Bezirksregierung Arnsberg und
extrahiert die Zeitreihe fuer Obernau- und Breitenbachtalsperre."""
import io, json, re, sys, urllib.parse, urllib.request, pathlib, time

UA = {"User-Agent": "Mozilla/5.0 (Pegelstaende-Recherche)"}
CACHE = pathlib.Path("cache"); CACHE.mkdir(exist_ok=True)


def get(url, tries=3):
    key = CACHE / (re.sub(r"[^A-Za-z0-9._-]", "_", url)[-120:])
    if key.exists():
        return key.read_bytes()
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                data = r.read()
            key.write_bytes(data)
            return data
        except Exception as e:
            if i == tries - 1:
                print(f"  FAIL {url} -> {e}", file=sys.stderr)
                return b""
            time.sleep(2)


def cdx(pattern):
    """Alle jemals archivierten URLs von bra.nrw.de, die auf das Muster passen."""
    u = ("https://web.archive.org/cdx/search/cdx?url=bra.nrw.de&matchType=domain"
         "&fl=original&collapse=urlkey&filter=original:" + urllib.parse.quote(pattern))
    return sorted(set(get(u).decode("utf8", "replace").split()))


DATE_PATS = [
    r"(\d{4})-(\d{2})-(\d{2})",          # 2023-07-15
    r"(\d{2})[.\-](\d{2})[.\-](\d{4})",  # 15.03.2022 / 15-11-2021
    r"(\d{2})[.\-](\d{2})[.\-](\d{2})\b",  # 15.09.21
]


def date_from_name(url):
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    for i, p in enumerate(DATE_PATS):
        m = re.search(p, name)
        if not m:
            continue
        a, b, c = m.groups()
        if i == 0:
            return f"{a}-{b}-{c}"
        y = c if len(c) == 4 else ("20" + c)
        return f"{y}-{b}-{a}"
    return None


# Die PDFs sind Excel-Exporte: "<Name> <Stauraum> <Inhalt> <Prozent> ..."
NUM = r"(-?[\d.]+,\d+|-?\d+)"
ROW = re.compile(r"(Obernau|Breitenbach)\w*\s+" + r"\s+".join([NUM] * 3))


def parse_pdf(data):
    from pypdf import PdfReader
    try:
        txt = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    except Exception as e:
        return {}, f"pdf-error: {e}"
    out = {}
    for m in ROW.finditer(txt.replace("\xa0", " ")):
        dam = m.group(1)
        vals = [float(v.replace(".", "").replace(",", ".")) for v in m.groups()[1:]]
        out[dam] = {"stauraum_mio_m3": vals[0], "inhalt_mio_m3": vals[1], "fuellgrad_pct": vals[2]}
    return out, txt


def main():
    pdfs = [u for u in cdx(".*[Tt]alsperrenf.*") if u.lower().endswith(".pdf")]
    pdfs = [u for u in pdfs if re.search(r"f(ue|ü|u)llst", u, re.I)]
    print(f"{len(pdfs)} Füllstands-PDFs im Wayback-Index gefunden")

    rows, raw_dump = [], {}
    for u in sorted(pdfs, key=lambda x: date_from_name(x) or "9999"):
        d = date_from_name(u)
        if not d:
            print(f"  ? kein Datum: {u}"); continue
        data = get(u) or get("https://web.archive.org/web/2024id_/" + u)
        if not data[:4] == b"%PDF":
            data = get("https://web.archive.org/web/2024id_/" + u)
        if data[:4] != b"%PDF":
            print(f"  ? kein PDF: {u}"); continue
        parsed, txt = parse_pdf(data)
        raw_dump[d] = txt if isinstance(txt, str) else ""
        if not parsed:
            print(f"  ! keine Treffer in {d} ({u})"); continue
        for dam, v in parsed.items():
            rows.append({"datum": d, "talsperre": dam, **v, "quelle": u})
        print(f"  {d}: " + "  ".join(f"{k}={v['fuellgrad_pct']}%" for k, v in parsed.items()))

    pathlib.Path("fuellstaende_wayback.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf8")
    with open("fuellstaende_wayback.csv", "w", encoding="utf8") as f:
        f.write("datum;talsperre;stauraum_mio_m3;inhalt_mio_m3;fuellgrad_pct;quelle\n")
        for r in rows:
            f.write(";".join(str(r[k]) for k in
                    ("datum", "talsperre", "stauraum_mio_m3", "inhalt_mio_m3",
                     "fuellgrad_pct", "quelle")) + "\n")
    print(f"\n{len(rows)} Datenpunkte -> fuellstaende.csv / .json")
    # Beispieltext zur Kontrolle des Parsers
    if raw_dump:
        k = sorted(raw_dump)[-1]
        print("\n--- Kontrollauszug", k, "---\n", raw_dump[k][:1200])


if __name__ == "__main__":
    main()
