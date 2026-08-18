---
concept_id: KONZ-platform-045
title: "Die Schleuse — Orte, Inhalte, Verfall"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "kein ADR — Aufraeum-Regel und Werkzeug, keine Architekturentscheidung"
review_by: 2026-11-18
kill_criteria: >
  Die Zahl der Eintraege aelter als 30 Tage steigt ueber drei Sitzungen in Folge,
  obwohl das Werkzeug laeuft — dann taugt entweder eine Frist nicht oder ein
  Zielort fehlt, und die Regel wird nachgezogen statt die Zahl ignoriert.
---

# KONZ-platform-045: Die Schleuse — Orte, Inhalte, Verfall

**Status:** Vorschlag · **Datum:** 2026-08-18 · **Anlass:** Owner-Befund
„auf shared hat sich mittlerweile auch Chaos breit gemacht" · **Größe:** T2

## Das Problem in einer Zahl

`~/shared` enthält am 2026-08-18: **247 Einträge, 3,8 GB**. Der älteste stammt
vom 2026-04-21 (119 Tage). 113 Einträge stammen aus dem Vormonat. Darunter:
ADR-Übergaben, deren ADR längst entschieden ist; Audit-Berichte, die im Repo
stehen sollten; ein `__pycache__` von einem Skript, das hier nie hätte laufen
sollen; ein Stash-Backup vom Juni; 1,2 GB LoRA-Dateien von der Box und 1,1 GB
CAD-Daten.

Kein Eintrag davon ist falsch entstanden. Sie sind alle korrekt **angekommen**
— und dann nie **weitergegangen**.

## Der Kernsatz

> Die Schleuse ist ein **Förderband, kein Regal.**

Alles darin ist unterwegs von A nach B. Was liegen bleibt, ist entweder noch
nicht angekommen oder gehört an einen anderen Ort. Daraus folgt alles Weitere:
jeder Inhalt hat einen **Zielort** und eine **Frist**.

## Die Orte

| Ort | Rolle | wer schreibt | Verweildauer |
|---|---|---|---|
| `~/shared/` (Dev-Host) | Übergabe Owner ↔ Agent | beide | befristet |
| `~/shared/inbox/secrets/` | Secrets im Klartext | Owner | **bis zur Übernahme, max. 1 Tag** |
| `~/shared/von-box/` | Box → Dev-Host | `box-schleuse.sh hol` | 14 Tage |
| `~/shared/_archiv/<datum>/` | Wartezimmer vor dem Löschen | nur `schleuse.py` | 90 Tage |
| Prod `…/schleuse/{von-box,zur-box}/` | Relais | `box-schleuse.sh` | Durchgang |
| `D:\schleuse\{raus,rein}\` (Box) | Box-Seite | `box-schleuse-sync.ps1` | Durchgang |
| **Repo / Outline / pgvector / Paperless** | **Zielorte** | Agent | dauerhaft |

Die letzte Zeile ist die wichtigste: **die Schleuse ist nie ein Zielort.** Wenn
etwas dauerhaft aufbewahrt werden soll, gehört es in ein Repo (Code, Skripte,
Konzepte), nach Outline (Runbooks, Lessons), in pgvector (Session-Wissen) oder
nach Paperless (Belege).

## Die Inhalte und ihre Fristen

| Klasse | Erkennung | Frist | Zielort |
|---|---|---|---|
| Werkzeug-Rest | `__pycache__`, `stash-backup-*` | **0 Tage** | gehört gar nicht hierher |
| Secret | `inbox/secrets/*` | **1 Tag** | `~/.secrets`, dann löschen |
| Box-Paket | `sprache/`, `box-*`, `gpu-*` | 14 Tage | Quelle ist `box-setup/` im Repo |
| Box-Skript | `box-*.ps1`, `*-tunnel-*.sh` … | 14 Tage | Repo |
| Box-Lane | `von-box/` | 14 Tage | Ziel-Repo, dann `box-schleuse.sh leere von-box` |
| Box-Ergebnis | `*ERGEBNIS*.txt` | 30 Tage | `AGENT_HANDOVER` / Konzept |
| ADR-Übergabe | `adr-handoff-*`, `charta-review-*` | 30 Tage | ADR + Outline |
| Bericht | `repo-optimize-*`, `platform-audit-*`, `analyse-*`, `review-*` | 30 Tage | `docs/` des Repos |
| alles Übrige | — | **30 Tage bis zur Frage** | Entscheidung nötig |

„Alles Übrige" verfällt nicht automatisch — fremde Daten (CAD, Angebote,
Gutachten) dürfen nicht nach Frist verschwinden. Sie werden nach 30 Tagen als
**unentschieden** gemeldet, bis jemand einen Zielort nennt. Ein Posten, der
niemandem gehört, ist ein Befund, kein Kandidat für den Automatismus.

## Der Mechanismus

`platform/tools/schleuse.py` — drei Stufen, absichtlich getrennt:

```bash
python3 tools/schleuse.py                        # Bericht, aendert nichts
python3 tools/schleuse.py --aufraeumen           # zeigt, was ins Archiv wandert
python3 tools/schleuse.py --aufraeumen --apply   # verschiebt nach _archiv/<datum>/
python3 tools/schleuse.py --endgueltig --apply   # loescht Archiv aelter als 90 Tage
```

**Warum zwei Stufen statt einer:** `--aufraeumen` **verschiebt**, es löscht
nicht. Zwischen „aus dem Weg" und „weg" liegen 90 Tage im `_archiv`. Ein
Werkzeug, das in einem Schritt löscht, wird irgendwann versehentlich gestartet —
und die Schleuse ist genau der Ort, an dem Dinge liegen, die es sonst nirgends
mehr gibt (der Sieger-Song vom 2026-08-17 war so ein Fall: nicht nachbaubar).

**Secrets sind ausgenommen.** Sie werden nie archiviert, sondern gemeldet: sie
gehören nach `~/.secrets` und danach sofort gelöscht. Das ist bereits durch den
Session-Start-Check 0.5.1 abgedeckt; `schleuse.py` wiederholt die Meldung nur.

**Sichtbarkeit:** Der Bericht läuft im Session-Start (Phase 0.5.2). Eine Regel,
die niemand liest, ist keine Regel — dieselbe Lehre wie bei den Selbsttests, die
zwei Tage lang da lagen und von nichts gerufen wurden.

## Was dieses Konzept NICHT tut

- Es räumt nicht rückwirkend auf. Der erste `--aufraeumen`-Lauf ist eine
  bewusste Entscheidung mit Freigabe, kein Teil dieses Vorschlags.
- Es fasst `D:\schleuse` auf der Box nicht an — dort gilt dieselbe Idee, aber
  die Box hat gerade einen eigenen Umzug (`music-lab/box-setup/UMZUG-D.md`).
- Es ersetzt `box-schleuse.sh` nicht. Das Transportwerkzeug bleibt; hier geht es
  nur darum, was **nach** dem Transport passiert.

## Messgröße

Zahl der Einträge in `~/shared` mit Alter > 30 Tage. Heute: **43** (19 fällig,
24 unentschieden). Ziel: dauerhaft unter 10. Steigt die Zahl über drei Sitzungen
in Folge, taugt entweder eine Frist nicht oder ein Zielort fehlt — dann wird
das Konzept nachgezogen, nicht die Zahl ignoriert.
