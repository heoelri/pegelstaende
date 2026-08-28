# Agent instructions

## Data refresh

This is an unofficial, independent visualization using only publicly available
data. Never imply affiliation with WVS or a public authority. Keep that
disclaimer prominent in `index.html` and `README.md`.

Use the smallest refresh path:

1. Set the operating year to the current year, or the next year in November
   and December.
2. Run `python .\scripts\talsperren_jahrestabelle.py <operating-year>`.
3. Confirm `data\fuellstaende_jahr.csv` is non-empty and its newest rows match the
   linked BRA PDF.
4. Run `python .\scripts\build_daten.py`.
5. Search WVS for publications newer than the latest `BERICHTE` entry.
6. Add only relevant, source-backed items to `PRESSEWERTE`, `BERICHTE`, and
   `EREIGNISSE` in `index.html`.

Do not run `scripts\talsperren_all.py` for a routine refresh. It scans the historical
archive and is only needed when BRA adds or changes older individual PDFs.

## Source rules

- Prefer the Bezirksregierung Arnsberg PDF for exact official measurements.
- Use WVS or authority publications for newer rounded values and measures.
- Every dataset, value, event, report, and derived statement must cite a directly verified public source. Prefer the primary source; if it is unavailable, use and clearly identify the best verifiable secondary source.
- Before using a source, check its license and terms of use. Document the license, required attribution, reuse restrictions, and any uncertainty in `SOURCES.md`.
- If no explicit reuse license exists, do not assume the content is freely licensed: use only the necessary factual data, avoid protected prose or media, and record the limitation in `SOURCES.md`.
- Do not use search-result summaries as evidence; open and verify the source.
- Do not bypass paywalls, authentication, robots restrictions, or access
  controls.
- If only a percentage is published, calculate volume as `percentage × 14.9`
  for Obernau or `percentage × 7.8` for Breitenbach, divided by 100 and rounded
  to two decimals.
- Do not duplicate a press value when `daten.js` already contains an official
  value for the same date and reservoir.
- Preserve known gaps instead of interpolating or inventing measurements.

## Page updates

When new data extends coverage, update the latest dates in the footer. Add a
report only when it materially changes the water-supply story; routine
measurement updates belong in `daten.js`, not `BERICHTE`.

Keep edits surgical. Do not add frameworks, dependencies, generated reports,
or new abstractions.

After any deep-dive review that produces no actual project change, ask the user whether the findings should be captured in a GitHub issue.

Do not add artificial line breaks to new or edited prose. Keep each new or edited paragraph or list item on one physical line unless the format requires otherwise; existing wrapping may remain until that text is changed.

## Checks

Run:

```powershell
node .\tests\test_trend.js
python -m py_compile .\scripts\talsperren_all.py .\scripts\talsperren_jahrestabelle.py .\scripts\build_daten.py
```

Also confirm the newest date and both reservoir names occur in `daten.js`, and
that inline JavaScript from `index.html` passes `node --check`.
