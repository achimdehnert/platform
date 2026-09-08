---
description: Scan-Stapel (eine PDF, viele Dokumente) zerlegen und nach Paperless einspeisen — Leerseiten per Tinte-Anteil, Dublettencheck VOR dem Import, Rechte VOR dem Kopieren, Kontrolle an der Datenbank statt am Ordner
mode: write
---

# /scan — Stapel → Einzeldokumente → Paperless

> **Wann:** Der ScanSnap hat einen ganzen Stapel in EINE PDF gelegt und darin stecken
> mehrere Dokumente. **Wann NICHT:** Ein Blatt = ein Dokument — dann ist nichts zu tun,
> der Scanner legt es direkt in den Consume-Ordner und Paperless nimmt es auf.
> **Nie:** Originale löschen, Personendaten nach `platform` committen (öffentliches Repo).
>
> **Erprobt am 2026-09-06:** 27 Seiten → 13 Dokumente (Paperless 2364–2376).
> Jede Regel unten steht hier, weil sie an diesem Stapel einmal falsch war.

## Step 0: Lage aufnehmen

```bash
pdfinfo <stapel>.pdf
pdftotext -f 1 -l 1 <stapel>.pdf - | head
```

ScanSnap-PDFs haben **keinen Textlayer** — `pdftotext` liefert leer. Das ist der
Normalfall, kein Fehler. Einmal über den ganzen Stapel:

```bash
ocrmypdf -l deu --deskew <stapel>.pdf <stapel>-ocr.pdf
```

## Step 1: Rückseiten erkennen — über den Tinte-Anteil, NICHT über den Text

Duplex heißt: ungerade Seite = Vorderseite, gerade = Rückseite. Leere Rückseiten müssen
raus, sonst wird jede zweite Seite ein eigenes „Dokument".

**Nicht über OCR-Text entscheiden.** Durchscheinende Schrift der Vorderseite liefert
Zeichenmüll, und eine „leere" Seite hat dann Text. Stattdessen der Anteil dunkler Pixel:
40 dpi rendern, Autocontrast, Rand 5 % abschneiden, Pixel < 110 zählen.

| Tinte-Anteil | Urteil |
|---|---|
| < 0,3 % | leer |
| > 0,9 % | bedruckt |
| dazwischen | ansehen, nicht raten |

## Step 2: Drehung

`tesseract --psm 0 -l osd` braucht **mindestens 150 dpi** — bei den 40 dpi aus Step 1
liefert es gar nichts. `ocrmypdf --rotate-pages` dreht bei Standard-Schwelle **nicht**;
die Drehung explizit setzen:

```python
page.rotate(<OSD-Wert>)   # pypdf
```

## Step 3: Grenzen ziehen und Dubletten VOR dem Import prüfen

Grenzen aus den Seitenköpfen: Absender, Betreff, Rechnungs-/Vorgangsnummer. Unklare
Seiten als Bild ansehen, nicht raten.

**Pflicht vor jedem Import** — die Kennung gegen Paperless halten:

```bash
ssh hetzner-prod "docker exec -i iil_dochub_web python3 manage.py shell" <<'PY'
from documents.models import Document
print(Document.objects.filter(content__icontains="<Kennung>").count())
PY
```

Am 2026-09-06 lag ein Blatt bereits doppelt vor (435/664) — ohne diesen Schritt wäre es
ein zweites Mal im Archiv gelandet.

## Step 4: Zerlegen und je Datei OCR

Dateiname **ist** der Titel:

```
YYYY-MM-DD - <Korrespondent> - <Typ> - <Kennung>.pdf
```

Split per `pypdf`, danach `ocrmypdf` je Einzeldatei (nicht nur über den Stapel — die
Einzeldatei trägt den Textlayer, den Paperless indexiert).

## Step 5: Einspeisen — Rechte VOR dem Kopieren

Zielordner `/opt/paperless-consume/<tag>/` auf hetzner-prod; **jede Ordnerebene wird
ein Schlagwort** (`PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS=true`). Vorhandene Ordner:
`achim`, `bine`, `iil`, `mara`, `steuer`, `tilly`, `risk-hub`.

```bash
# neuer Ordner: anlegen und chownen in EINEM Zug, erst danach kopieren
ssh hetzner-prod 'mkdir -p /opt/paperless-consume/<tag> \
  && chown -R runner-wh:runner-wh /opt/paperless-consume/<tag> \
  && chmod -R 2775 /opt/paperless-consume/<tag>'
scp <dateien> hetzner-prod:/root/
ssh hetzner-prod 'install -o runner-wh -g runner-wh -m 664 /root/<datei> /opt/paperless-consume/<tag>/'
```

**Warum diese Reihenfolge:** Die Worker laufen als UID 1000 (`runner-wh`). Ein als root
angelegter Ordner (755) lässt sie die Datei parsen, aber nicht entfernen →
`PermissionError`, **kein** Dokument. Und ein nachträgliches `chown` weckt den Beobachter
nicht, weil er auf mtime reagiert, nicht auf ctime — dann zusätzlich `touch <datei>`.
Aufnahme danach ~10 s (`PAPERLESS_CONSUMER_POLLING_INTERVAL=10`).

## Step 6: Kontrolle an der Datenbank, nicht am Ordner

Ein leerer Ordner beweist nichts — eine Datei kann auch entfernt worden sein, ohne ein
Dokument zu werden (Realfall 2026-09-07/08, doc-hub#3).

```bash
ssh hetzner-prod "docker exec -i iil_dochub_web python3 manage.py shell" <<'PY'
from documents.models import Document
for d in Document.objects.order_by('-id')[:<anzahl>]:
    print(d.id, d.original_filename, '|', d.title, '|', [t.name for t in d.tags.all()])
PY
```

**Falle `created`:** Paperless liest ein Datum aus dem Text — bei alten Rechnungen ist
das oft das **Geburtsdatum** (Dok 2350/2353: 1961 → `jahr-unklar`). Datum, Korrespondent,
Typ und Jahres-Tag danach setzen; `jahr-unklar` entfernen.

## Step 7: Abschluss-Melder laufen lassen

```bash
python3 tools/scan_melder.py --ssh hetzner-prod
```

Meldet, was liegen geblieben ist **und** was verschwunden ist, ohne ein Dokument zu
werden. Exit 0 = sauber · 1 = etwas hängt · 4 = Verlust · 2 = blind.

## Abschluss-Checkliste (PFLICHT — alle Zeilen einmal abhaken)

| # | Prüfung | erledigt? |
|---|---|---|
| 1 | OCR über Stapel gelaufen (Step 0) | |
| 2 | Leerseiten über Tinte-Anteil bestimmt, nicht über Text (Step 1) | |
| 3 | Querformat/kopfüber explizit gedreht (Step 2) | |
| 4 | Dublettencheck gegen Paperless VOR dem Import (Step 3) | |
| 5 | Je Einzeldatei OCR, Dateiname = Titelschema (Step 4) | |
| 6 | Ordnerrechte VOR dem Kopieren gesetzt (Step 5) | |
| 7 | Ergebnis an der Datenbank geprüft, nicht am Ordner (Step 6) | |
| 8 | `created`-Datum je Dokument gesichtet (Geburtsdatum-Falle, Step 6) | |
| 9 | `scan_melder.py` gelaufen, Exit-Code genannt (Step 7) | |
| 10 | Originalstapel NICHT gelöscht | |

Eine bewusst übersprungene Zeile wird benannt („übersprungen, weil X") — stillschweigend
auslassen gilt als nicht erledigt.
