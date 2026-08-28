"""Historische Talsperren-Fuellstaende (alte BRA-Website 1998-2004, HTML) und
die Jahresindex-Seiten der neuen Website, zusammengefuehrt mit talsperren.py."""
import html, json, re, sys, urllib.parse, urllib.request, pathlib, time

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Pegelstaende-Recherche)"}
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / ".cache" / "cache"; CACHE.mkdir(parents=True, exist_ok=True)


def get(url, tries=3):
    key = CACHE / (re.sub(r"[^A-Za-z0-9._-]", "_", url)[-120:])
    if key.exists():
        return key.read_bytes()
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                d = r.read()
            key.write_bytes(d)
            return d
        except Exception as e:
            if i == tries - 1:
                print(f"  FAIL {url} -> {e}", file=sys.stderr)
                return b""
            time.sleep(2)


OLD = ("http://www.bra.nrw.de/dieBezirksregierung/aufbau/abteilungen/abteilung5"
       "/dezernat54/talsperren/fuellstaende/")


def cdx_old():
    u = ("https://web.archive.org/cdx/search/cdx?url="
         + urllib.parse.quote("bra.nrw.de/dieBezirksregierung/aufbau/abteilungen/abteilung5/"
                              "dezernat54/talsperren/fuellstaende/", safe="")
         + "*&fl=timestamp,original&collapse=urlkey&limit=3000")
    out = []
    for line in get(u).decode("utf8", "replace").splitlines():
        p = line.split()
        if len(p) == 2:
            out.append((p[0], p[1]))
    return out


def text_of(raw):
    t = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


NUM = r"(-?[\d.]+,\d+|-?\d+)"
ROW = re.compile(r"(Obernau|Breitenbach)\w*\s+" + r"\s+".join([NUM] * 3))


def parse(t):
    out = {}
    for m in ROW.finditer(t):
        v = [float(x.replace(".", "").replace(",", ".")) for x in m.groups()[1:]]
        out[m.group(1)] = {"stauraum_mio_m3": v[0], "inhalt_mio_m3": v[1], "fuellgrad_pct": v[2]}
    return out


def main():
    pages = [(ts, u) for ts, u in cdx_old()
             if re.search(r"/\d{2}_\d{2}_\d{2,4}\.html$", u)]
    print(f"{len(pages)} historische Tagesseiten im Wayback-Index")
    rows, misses = [], []
    for ts, u in sorted(pages, key=lambda x: x[1]):
        m = re.search(r"/(\d{2})_(\d{2})_(\d{2,4})\.html$", u)
        d, mo, y = m.groups()
        y = y if len(y) == 4 else ("19" + y if int(y) > 50 else "20" + y)
        datum = f"{y}-{mo}-{d}"
        raw = get(f"https://web.archive.org/web/{ts}id_/{u}")
        if not raw:
            misses.append(datum); continue
        got = parse(text_of(raw.decode("latin1", "replace")))
        if not got:
            misses.append(datum); continue
        for dam, v in got.items():
            rows.append({"datum": datum, "talsperre": dam, **v,
                         "quelle": f"https://web.archive.org/web/{ts}/{u}"})
        print(f"  {datum}: " + "  ".join(f"{k}={v['fuellgrad_pct']}%" for k, v in got.items()))

    print(f"\n{len(rows)} historische Datenpunkte, {len(misses)} ohne Treffer")
    (DATA / "fuellstaende_alt.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main()
