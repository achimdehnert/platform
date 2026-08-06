# Konvention: Hosts hinter Cloudflare Access prüfen

**Kurzfassung:** Eine Domain hinter Cloudflare Access ist prüfbar — mit dem
Service-Token aus dem Schlüsselkasten. `tools/cf-access-fetch.sh` ist der eine
Ort, der es kennt. Wer stattdessen eine Prüfung abschaltet oder „kann ich nicht
prüfen" schreibt, hat die Lücke nicht geschlossen, sondern dokumentiert.

## Das Problem

Domains hinter Access antworten jedem nicht angemeldeten Aufruf mit **302** auf
die Anmeldeseite. Ein Agent oder CI-Job sieht davon nur den Redirect — er kann
weder feststellen, ob eine Seite existiert, noch was auf ihr steht.

Der naheliegende Schluss ist der falsche: *„Cloudflare ist kein Prüfmittel."*
Das stimmt nur ohne Token. Er hat zweimal Geld gekostet:

| Fall | Folge |
|---|---|
| `apo-hub` (2026-07-18) | externer Deploy-Healthcheck dauerhaft per `skip_external_verify` stillgelegt — der Eintrag notierte sogar *„kein Umgehen möglich ohne Cloudflare-Access-Service-Token"*, ohne nachzusehen, ob es eins gibt |
| `risk-hub` (2026-08-05) | Frage nach der KD-Struktur auf iil.pet blieb unbeantwortet („müsste durch Cloudflare"), obwohl die Antwort einen Aufruf entfernt war |

Gemeinsame Wurzel: eine **Merkregel, die vor einem Irrweg schützen sollte, wurde
zur Denkblockade**. Sie beschrieb einen Zustand („geht nicht") statt einer
Bedingung („geht nicht *ohne X*") — und niemand prüfte, ob X vorliegt.

## Die Lösung

Cloudflare Access kennt **Service-Tokens**: zwei Kopfzeilen, keine Anmeldung,
kein Browser. Eins liegt seit Längerem im Schlüsselkasten:

```
~/.secrets/cf_svc_client_id
~/.secrets/cf_svc_client_secret
```

> Es gibt daneben `cf_access_client_id`/`cf_access_client_secret` — die sind für
> iil.pet **nicht** berechtigt (gemessen 2026-08-05: 302). Wer das falsche Paar
> greift, hält das Ergebnis für eine Access-Wand statt für ein falsches Token.

Benutzung ausschließlich über den Wrapper, damit die Werte nie in der
Prozessliste oder in Logs landen:

```bash
tools/cf-access-fetch.sh https://iil.pet/kd/risk-hub/
tools/cf-access-fetch.sh https://iil.pet/kd/ -o /dev/null -w '%{http_code}\n'
tools/cf-access-fetch.sh --selftest    # beweist, dass die Messung beißt
tools/cf-access-fetch.sh --coverage    # welche Hosts der Token abdeckt
```

## Abdeckung (gemessen 2026-08-05)

| Host | Token wirkt | Anmerkung |
|---|---|---|
| `iil.pet` | ja | 200 statt 302 |
| `staging-*.iil.pet` | ja | eigene Access-App, Token gilt trotzdem |
| `knowledge.iil.pet` | ja | |
| `kd.iil.pet` | **nein** | eigene Access-App, Token nicht berechtigt |
| `orchestrator.iil.pet` | n/a | keine Access-Wand, API-Key statt dessen |

`--coverage` misst das neu, statt dieser Tabelle zu glauben.

## Pflicht: die Gegenprobe

Ein `200` **allein beweist nichts** — es könnte auch heißen, dass vor dem Host
gar keine Wand steht. Jede Prüfung braucht die Messung ohne Token daneben:

```
mit Token : 200
ohne Token: 302     ← erst dieser Unterschied ist der Beleg
```

Genau das macht `--selftest`, und er scheitert laut, wenn eine der beiden Seiten
nicht stimmt. Ein stiller Erfolg wäre hier die gefährlichere Variante.

## Rückbau

Dieses Werkzeug ist eine Krücke um eine Zugangswand, kein Architektur-Baustein.
Es gehört gelöscht, sobald einer dieser Fälle eintritt:

| # | Auslöser | Nachweis |
|---|---|---|
| 1 | Access fällt für die Hosts weg | `--coverage` zeigt für **alle** Zeilen „keine Wirkung" (Exit 1) |
| 2 | Token wird zurückgezogen | `--selftest` schlägt fehl (Exit 1) |
| 3 | ein Jahr ohne Aufrufer | `grep -rl cf-access-fetch ~/github --include='*.sh' --include='*.yml' --include='*.md' \| grep -v platform/tools` ist leer |

**Kill-Gate: 2027-08-05.** Bis dahin einmal gegen die drei Fälle prüfen.

Der Rückbau selbst ist `git rm tools/cf-access-fetch.sh` plus diese Datei. Kein
Zustand, keine Migration, keine Abhängigkeit in Gegenrichtung — bewusst so
gebaut. Wer entfernt, muss nur die Aufrufer nachziehen, und die findet der grep
aus Fall 3.

## Offene Folgearbeit

`apo-hub` kann seinen externen Healthcheck wieder scharf schalten
(`skip_external_verify` zurücknehmen, Probe über den Wrapper). Nicht hier
gemacht — eigenes Repo, eigener PR.
