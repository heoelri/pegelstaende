"""Wayback-CDX mit SERVERSEITIGEM Filter - sonst schneidet das Limit vor dem Filtern ab."""
import json, urllib.parse, urllib.request

CDX = "http://web.archive.org/cdx/search/cdx"


def cdx(url, filt=None, limit=2000):
    p = {"url": url, "output": "json", "collapse": "urlkey", "limit": str(limit)}
    if filt:
        p["filter"] = filt
    req = urllib.request.Request(CDX + "?" + urllib.parse.urlencode(p),
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            rows = json.loads(r.read().decode("utf-8", "replace") or "[]")
    except Exception as e:
        print(f"    FEHLER: {e}")
        return []
    return rows[1:] if rows else []


ABFRAGEN = [
    ("bezreg-arnsberg.nrw.de*", "urlkey:.*talsperr.*"),
    ("bezreg-arnsberg.nrw.de*", "urlkey:.*(stauinhalt|fuellung|f%C3%BCll).*"),
    ("bezreg-arnsberg.nrw.de*", "urlkey:.*(obernau|breitenbach).*"),
    ("bra.nrw.de*",             "urlkey:.*(stauinhalt|obernau|breitenbach).*"),
    ("lanuv.nrw.de*",           "urlkey:.*(gewaesserkundlich|jahrbuch|dgj).*"),
    ("*.nrw.de*",               "urlkey:.*obernautalsperre.*"),
    ("wvs.nrw*",                None),
]

alle = {}
for url, filt in ABFRAGEN:
    print(f"\n=== {url}   filter={filt}")
    rows = cdx(url, filt)
    print(f"    {len(rows)} Treffer")
    for r in rows[:80]:
        print(f"      {r[1][:4]}  {r[4]}  {r[2][:140]}")
        alle[r[2]] = r

print(f"\nGesamt {len(alle)} eindeutige URLs")
json.dump(list(alle.values()), open("kandidaten_alt.json", "w", encoding="utf-8"), indent=1)
