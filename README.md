# Pegelstände Obernau- und Breitenbachtalsperre

Inoffizielle, unabhängige Auswertung der Füllstände der Obernau- und
Breitenbachtalsperre sowie der regionalen Berichterstattung dazu.

Das Projekt ist weder vom Wasserverband Siegen-Wittgenstein (WVS) noch von
einer Behörde beauftragt, geprüft oder betrieben. Es verarbeitet ausschließlich
öffentlich zugängliche Daten. Verbindlich sind immer die in der Anwendung
verlinkten Originalquellen.

## Was die Seite zeigt

`index.html` visualisiert:

- Füllstände und Füllmengen beider Talsperren
- saisonale und jährliche Entwicklungen
- eine qualitative Tonalitätsauswertung öffentlich zugänglicher Berichte
- relevante Ereignisse und Maßnahmen
- alle verwendeten Messwerte mit ihrer jeweiligen Quelle

Die amtlichen Messreihen liegen in `daten.js`. Zusätzliche öffentlich
berichtete Einzelwerte, Ereignisse und Medienbeiträge stehen direkt in
`index.html`. Die Seite läuft ohne Server; `index.html` kann direkt im Browser
geöffnet werden. Nur Chart.js wird zur Laufzeit von einem CDN geladen.

## Verzeichnisstruktur

- `index.html`, `daten.js`: veröffentlichte Website
- `data/`: extrahierte Messreihen
- `scripts/`: Datenbeschaffung und Aufbereitung
- `research/`: Ergebnisse der historischen Quellensuche
- `tests/`: kleine ausführbare Prüfungen

## Daten aktualisieren

Die Python-Skripte lesen öffentlich erreichbare Veröffentlichungen der
Bezirksregierung Arnsberg und historische Seiten aus dem Internet Archive.

```powershell
python .\scripts\talsperren_all.py
python .\scripts\talsperren_jahrestabelle.py 2026
python .\scripts\build_daten.py
```

Aktuelle WVS-Pressewerte und neue Ereignisse werden nach Prüfung der
Originalquelle in den Arrays `PRESSEWERTE`, `BERICHTE` und `EREIGNISSE` in
`index.html` ergänzt.

## Grenzen

Die Daten können Lücken, nachträgliche Änderungen oder Übertragungsfehler
enthalten. Die Tonalität ist eine manuelle, qualitative Einordnung und keine
amtliche oder objektiv messbare Kennzahl. Dieses Projekt ersetzt keine
behördliche Auskunft zur Trinkwasserversorgung.
