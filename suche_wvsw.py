"""Durchsucht das Wayback-Archiv der alten WVS-Domain wvsw.de nach belegten
Fuellstandsangaben zu Obernau- und Breitenbachtalsperre.

Hintergrund: Fuer 2004-2014 existiert keine amtliche Berichtsreihe im Archiv.
Presseveroeffentlichungen des Verbands nennen aber immer wieder Einzelwerte.
Das ersetzt keine Zeitreihe, schliesst aber Stuetzpunkte in der Luecke.
"""
import json, os, re, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
CACHE = "cache_wvsw"
os.makedirs(CACHE, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Pegelstaende-Recherche)"}

# Zahl + Einheit in der Naehe eines Talsperrennamens
KONTEXT = re.compile(r"(obernau|breitenbach|talsperre|f\W?llstand|f\W?llung|stauinhalt)", re.I)
WERT = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*(%|prozent|mio\.?\s*m|millionen\s*kubik)", re.I)


def hol(url):
    pfad = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", url)[-140:])
    if os.path.exists(pfad):
        return open(pfad, "rb").read()
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=90) as r:
                d = r.read()
            open(pfad, "wb").write(d)
            return d
        except Exception:
            time.sleep(2 * (i + 1))
    return b""


def text_aus(daten, url):
    if url.lower().endswith(".pdf") or daten[:4] == b"%PDF":
        try:
            import io

            from pypdf import PdfReader
            return "\n".join(p.extract_text() or ""
                             for p in PdfReader(io.BytesIO(daten)).pages)
        except Exception:
            return ""
    if url.lower().endswith(".swf") or daten[:3] in (b"CWS", b"FWS", b"ZWS"):
        # Flash: lesbare Textfragmente herausziehen, reicht fuer Zahlen
        return "".join(chr(b) if 32 <= b < 127 else " " for b in daten)
    import html as h
    t = daten.decode("utf-8", "replace")
    if t.count("\ufffd") > len(t) / 50:
        t = daten.decode("latin-1", "replace")
    t = re.sub(r"<script[\s\S]*?</script>", " ", t, flags=re.I)
    return re.sub(r"\s+", " ", h.unescape(re.sub(r"<[^>]+>", " ", t)))


def main():
    rows = json.load(open("cdx_wvsw.json"))
    kandidaten = [(r[1], r[2]) for r in rows
                  if r[4] == "200"
                  and re.search(r"\.(html?|pdf|swf)$|/$", r[2], re.I)
                  and not re.search(r"\.(jpg|jpeg|gif|png|css|js)$", r[2], re.I)]
    print(f"{len(kandidaten)} Seiten zu pruefen\n")

    funde = []
    for i, (ts, url) in enumerate(kandidaten, 1):
        daten = hol(f"https://web.archive.org/web/{ts}id_/{url}")
        if not daten:
            continue
        txt = text_aus(daten, url)
        if not KONTEXT.search(txt):
            continue
        for m in WERT.finditer(txt):
            a, b = max(0, m.start() - 220), m.end() + 120
            umfeld = txt[a:b]
            if not re.search(r"obernau|breitenbach|talsperre", umfeld, re.I):
                continue
            funde.append({"ts": ts, "url": url, "wert": m.group(0),
                          "umfeld": umfeld.strip()})
        if i % 40 == 0:
            print(f"  {i}/{len(kandidaten)} geprueft, {len(funde)} Fundstellen")

    # nach Umfeld entdoppeln
    gesehen, eindeutig = set(), []
    for f in funde:
        s = re.sub(r"\s+", " ", f["umfeld"])[:160]
        if s not in gesehen:
            gesehen.add(s)
            eindeutig.append(f)

    print(f"\n{len(eindeutig)} eindeutige Fundstellen\n")
    for f in eindeutig:
        print(f"[{f['ts'][:8]}] {f['wert']}  {f['url'].rsplit('/', 1)[-1][:40]}")
        print(f"    ...{f['umfeld'][:300]}...\n")
    json.dump(eindeutig, open("wvsw_funde.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
