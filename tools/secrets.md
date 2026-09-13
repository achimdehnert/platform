# Secrets — Werkzeuge

Kurzueberblick ueber die Secrets-Werkzeuge in `tools/`. Alle drei lesen
Secret-Dateien nur, um Form/Fingerabdruck zu ermitteln — keines gibt einen
Wert aus.

| Werkzeug | Zweck |
|---|---|
| `tools/secrets_inventory_check.py` | Prueft `infra/secrets-inventory.yaml` gegen sein Schema, zaehlt Eintraege/Konsumenten/Belege (Kill-Gate-Zahlen). |
| `tools/secrets-flatten.py` | Raeumt ein verschachteltes `~/.secrets/.secrets/` auf — Plan per SHA-256-Fingerabdruck, `--apply` fuehrt ihn aus. |
| `tools/secrets_pruefen.py` | Prueft eine einzelne Schluesseldatei (Form, Hash, optional HTTP-Gegenprobe) und meldet Dateien ohne `NAME=`-Form. |

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
