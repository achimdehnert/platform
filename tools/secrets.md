# Secrets — Werkzeuge

Kurzueberblick ueber die Secrets-Werkzeuge in `tools/`. Alle drei lesen
Secret-Dateien nur, um Form/Fingerabdruck zu ermitteln — keines gibt einen
Wert aus.

| Werkzeug | Zweck |
|---|---|
| `tools/secrets_inventory_check.py` | Prueft `infra/secrets-inventory.yaml` gegen sein Schema, zaehlt Eintraege/Konsumenten/Belege (Kill-Gate-Zahlen). |
| `tools/secrets-flatten.py` | Raeumt ein verschachteltes `~/.secrets/.secrets/` auf — Plan per SHA-256-Fingerabdruck, `--apply` fuehrt ihn aus. |
| `tools/secrets_pruefen.py` | Prueft eine einzelne Schluesseldatei (Form, Hash, optional HTTP-Gegenprobe) und meldet Dateien ohne `NAME=`-Form. |
| `tools/secret_lesen.sh` | Der EINE Weg, aus einem Shell-Skript an einen Wert zu kommen — versteht `bare` und `NAME=WERT`. Python-Seite: `infra/lib/secrets.py`. |

## Schlüssel prüfen ohne ihn zu zeigen

Anlass (2026-09-13): Eine Secret-Datei unter `~/.secrets/<name>` lag "nackt"
vor — nur der Wert, keine `NAME=WERT`-Form. Ein `. datei`-Sourcing, gedacht
fuer einen schnellen Hash-Vergleich, fuehrte den Wert stattdessen als
Kommando aus; die Shell schrieb ihn in ihre eigene Fehlermeldung. Der
bestehende, argumentbasierte Secret-Leak-Guard (fängt `cat`/`head`/`tail`/
`grep` mit einer Secret-Datei als Argument ab) hat dabei korrekt gefeuert —
er sichert aber kein Sourcing ab. `tools/secrets_pruefen.py` macht das
Sourcen ueberfluessig.

Drei Aufrufe:

```bash
# Form + Hash je Wert (nie der Wert selbst)
python3 tools/secrets_pruefen.py --datei cloudflare_api_token

# HTTP-Gegenprobe gegen den Provider — nur der Code wird gemeldet
python3 tools/secrets_pruefen.py --datei groq_api_key --http groq
python3 tools/secrets_pruefen.py --datei mixed_secrets --var GROQ_API_KEY --http groq

# Melder: welche Dateien der Basis liegen ohne NAME=-Form vor?
python3 tools/secrets_pruefen.py --alle
```

`--http` setzt einen eigenen `User-Agent` (`secrets_pruefen/1`) — die
urllib-Standardkennung wird von Cloudflare oft mit 403 geblockt; das ist ein
Hinweis auf Netzwerk/Provider, keine Rotation.

**Regel:** Schluesseldateien nie sourcen; Pruefung nur ueber
`secrets_pruefen.py`. Ziel: alle Dateien unter `~/.secrets` in `NAME=`-Form —
`--alle` ist der Melder dafuer (Exit 1, solange mindestens eine Datei
`bare` oder `gemischt` ist).

## Lesen

Eine Secret-Datei wird **nie** selbst gelesen — weder mit `cat`/`head`/`<`
noch mit `read_text().strip()`, und schon gar nicht per `source`/`. datei`.
Es gibt genau zwei Aufrufe, und beide verstehen **beide** Formen (`bare` =
ganze Datei ist der Wert, und `NAME=WERT` mit optionalen Kommentar- und
Leerzeilen davor):

```python
# Python — infra/lib/secrets.py ist die eine Implementierung
from infra.lib.secrets import secret_wert, secret_bytes

token = secret_wert(Path.home() / ".secrets" / "cloudflare_write_token")
token = secret_wert(pfad, name="CF_SECRET")   # Datei mit mehreren Variablen
key = secret_bytes(pfad)                      # Schluesselmaterial als Bytes
```

```bash
# Shell — ruft dieselbe Implementierung auf, kein zweiter Parser
TOKEN="$(tools/secret_lesen.sh cloudflare_write_token)"   # Name -> ~/.secrets/
TOKEN="$(tools/secret_lesen.sh /pfad/zur/datei CF_SECRET)"  # Auswahl
# Exit 2 = Datei fehlt · Exit 3 = mehrere Variablen, kein NAME angegeben
```

Verhalten im Detail: eine einzelne `NAME=WERT`-Zeile liefert den Teil hinter
dem ersten `=`, ohne beidseitig gleiche Anfuehrungszeichen. Mehrere Variablen
ohne `name`/`NAME` sind ein Fehler (nie stillschweigend die erste nehmen).
Alles andere ist `bare` und wird `strip()`-t — **exakt** wie vorher, damit die
Umstellung kein Verhalten aendert. `NAME=` ohne Wert und `NAME==` gelten als
base64-Auffuellung eines nackten Werts, nicht als leere Variable.

**Regel:** nie sourcen, nie `cat` — immer ueber den Leser. Ein Test
(`tools/tests/test_secret_lesen.py`) durchsucht `tools/`, `infra/`, `scripts/`
und `deployment/` nach Rueckfaellen und hat eine Positivkontrolle; eine
begruendete Ausnahme wird mit dem Kommentar `leser-ausnahme` markiert.

### Reihenfolge der Umstellung (platform#3129)

| Stufe | Inhalt | Stand |
|---|---|---|
| 1 | Alle Leser in `platform` verstehen beide Formen | dieser Stand |
| 2 | Dieselbe Umstellung in den uebrigen Repos (mcp-hub, dev-hub, risk-hub, writing-hub, music-lab, illustration-hub, illustration-fw, iil-pet-portal, ausschreibungs-hub) | offen |
| 3 | Die Dateien unter `~/.secrets` selbst auf `NAME=WERT` umstellen | offen, erst nach Stufe 2 |

Die Reihenfolge ist nicht beliebig: erst wenn **jeder** Leser tolerant ist,
darf die Form der Dateien wechseln — sonst liest ein zurueckgebliebener Leser
die ganze Zeile `NAME=WERT` als Wert und schickt sie als Token ins Netz (401,
im schlechteren Fall ein Wert im Fehlertext).
