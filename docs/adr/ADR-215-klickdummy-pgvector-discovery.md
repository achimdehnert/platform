---
id: ADR-215
title: "Klickdummy Discovery via Orchestrator pgvector (Stage 1.5)"
status: proposed
date: 2026-05-21
deciders: ["Achim Dehnert"]
tags: ["klickdummy", "discovery", "pgvector", "orchestrator", "stage-1.5"]
related:
  - "platform:ADR-211"          # Klickdummy-Rahmen (extends)
  - "platform:ADR-113"          # Orchestrator pgvector (extends)
  - "platform:ADR-210"          # Local-Staging-Prod-Architecture
  - "platform:ADR-212"          # Traefik-Ingress iil.pet
  - "meiki:ADR-027"             # Conversational Klickdummy (Schwester-Empirie)
  - "iilgmbh:iil-klickdummy v1.4" # aktuelles pip-Paket
supersedes: []
superseded_by: []
# Diese ADR beschreibt einen DISCOVERY-Layer, keinen Klickdummy-Instanz.
# Daher kein class/sunset_after Frontmatter.
---

# ADR-215 · Klickdummy Discovery via Orchestrator pgvector (Stage 1.5)

## Status

**proposed** — Diskussionsgrundlage. PoC in `iilgmbh/iil-klickdummy` (Issue
für v1.5). Empirie #1 als Cross-Repo-Picker-Fetch in `meiki-hub`.

## Kontext

Nach 14 Iterationen (Iter. 9–22, meiki-hub-Session 2026-05-21) sind **8
Klickdummy-Instanzen in 6 Repos × 5 Orgs × 3 UX-Genres** live:

| Genre | Anzahl | Repos |
|---|---|---|
| Forms | 6 | meiki-hub × 2, ttz-hub × 2, pg-hub, fristen-detail |
| Conversation | 2 | meiki-hub:ADR-027-assets (Frist-Auskunft), sqf-hub (AF1) |
| spec-demo | 1 | writing-hub (Lecture-Outline) |

Cross-Repo-Picker (Iter. 12–14) und Reachability-Probe (Iter. 16) wurden
mit der Skalierung **unhandlich**:

1. `CROSS_REPO_INDEX` ist als JS-Konstante in jedem Klickdummy gepflegt
   — bei 8 Instanzen = **8 Sync-Punkte für Drift**.
2. Reachability-Probe (HEAD-fetch auf `path_rel`) scheitert in ~50 %
   der lokalen Setups (Server-Root-Pfad-Abhängigkeit).
3. Stakeholder-Demos brauchen lokales `python3 -m http.server` —
   Hürde für Pilot-Reviews mit Raphael (sqf), Ilja (pg), TTZ-Pilot.
4. Feedback aus dem v0.5-Widget landet pro Repo separat — **keine
   Cross-Repo-Sicht** auf eingehende Stakeholder-Stimmen.

Parallel ist die Orchestrator-Datenbank (`orchestrator.iil.pet`,
`platform:ADR-113`) bereits **pgvector-fähig** und betriebsbereit
(`agent_memory_upsert`, `agent_memory_search` MCP-Tools).

Plus: `iil-klickdummy` v1.2 hat bereits einen `klickdummy-sync`-Befehl,
der NDJSON über alle Cross-Repo-Klickdummies erzeugt. Der API-Push in
pgvector fehlt nur als letzte Brücke.

## Entscheidung

**Stage 1.5: Klickdummy Discovery via Orchestrator pgvector.**

Klickdummies bleiben in ihren Repos (git-nativ, kein zentrales Hosting).
Was zentral wird, ist nur die **Discovery-Schicht**:

1. **`iil-klickdummy v1.5` `klickdummy sync push --to-orchestrator`**:
   Pro Klickdummy ein Embedding über `(title + purpose +
   parity_acceptance-Texte + topic)` + Metadaten (spec_id, version, class,
   topic, adr, repo, path_rel, last_seen, klickdummy_class, personas[]).
2. **Orchestrator-pgvector** speichert die Embeddings + Metadata in
   einer eigenen `agent_memory_*`-Sub-Collection `klickdummy-registry`.
3. **Cross-Repo-Picker (Renderer-Side)** fragt Orchestrator-API ab statt
   `CROSS_REPO_INDEX`-Konstante zu pflegen — neue Klickdummies erscheinen
   automatisch sobald sync gelaufen ist.
4. **Semantische Cross-Repo-Search**: „zeig alle Klickdummies zum Thema
   Eskalation" → pgvector liefert meiki:fristen.eskalation +
   sqf:af1.top-stoerfaelle + pg-hub:do-stichprobenvergleich + ttz:
   werkleiter.eskalation-stub.

## Was NICHT Inhalt dieser ADR

- **Hosting** der Klickdummies auf iil.pet (= Stage 2 / Lesart A) —
  separates ADR, vorbedingungs-frei wenn DSFA-Ergebnis weiter trägt
  (heutige DSFA-Klärung: nicht kritisch, nur Name+Vorname öffentlich)
- **Feedback-Aggregation cross-Repo** — kann später auf demselben
  pgvector-Layer aufsetzen (ADR-217 o. ä.)
- **Service-Boundary-Erweiterung** der Orchestrator-API — Discovery
  liegt klar im Orchestrator-Scope (analog `agent_memory_*`)

## I1–I4 (Pattern bleibt unverändert)

Klickdummies bleiben unverändert `platform:ADR-211`-konform. Discovery
ist ein **zusätzlicher Service**, kein Eingriff in die Klickdummy-
Invarianten. Spezifisch:

- **I1** Spec-First: weiterhin via `screens-spec.yaml` / `bot-spec.yaml`
  pro Repo. Discovery liest die Spec, ersetzt sie nicht.
- **I2** Prod-Sicherheit: `class: mock` bleibt für jeden Klickdummy.
  Discovery selbst hat `class: N/A` (kein Klickdummy, sondern Service).
- **I3** Off-Ramp: pro Klickdummy unverändert. Discovery kennt die Phase
  (A/B/C) und exponiert sie via API.
- **I4** Namensraum: `repo:ADR-NNN`-Refs bleiben Pflicht. Discovery
  liest `adr.local` und `adr.sister_of` aus den Specs.

## DSFA-Vermerk (User-Klärung 2026-05-21)

DSFA für Klickdummy-Discovery + späteres Hosting wurde durch den User
abgeschätzt:

- **Nicht kritisch** — die in den Klickdummies vorkommenden personen-
  bezogenen Daten beschränken sich auf **Name + Vorname** der involvierten
  Stakeholder (z. B. Raphael Bayer als Endkunde, Ilja Lerch als Citizen-
  Dev, Stephan Bachmann/Serdar Dag als Dispo-Beispiele).
- Diese Daten sind **öffentlich bekannt** (Funktions-Rollen, keine
  Privat-Daten) und betreffen **wenige Personen**.
- Echte Operativ-Daten (Wagennummern, Fall-IDs, BRMS-Berechnungen,
  Pflichten-Kataloge) sind in den Klickdummies durchgehend **synthetisch**
  (`class: mock`, klar dokumentiert in `class_evidence.no_backend`).

Konsequenz: Stage 1.5 (Discovery) ist DSGVO-unkritisch. Stage 2
(iil.pet-Hosting der Klickdummies selbst) wird nach demselben
DSFA-Ergebnis ebenfalls möglich — separate ADR.

## Konsequenzen

### Positiv

- **Drift-Robustheit**: CROSS_REPO_INDEX wird obsolet. Eine zentrale
  Datenquelle (Orchestrator) ersetzt 8 manuelle Synchronisations-Punkte.
- **Stakeholder-Demo-Reife**: Cross-Repo-Browser im Klickdummy-Renderer
  zeigt **alle** Schwester-Klickdummies live, ohne Repo-lokale Konfig.
- **Semantische Discovery**: pgvector erlaubt fachliche Such-Pattern
  („alle Eskalations-bezogenen Klickdummies cross-org") — neue
  Abstraktion über reine Repo/Klasse/Topic-Achsen hinaus.
- **iil-klickdummy v1.5-Pfad ist klar**: Renderer-Plug-in (Forms vs.
  Conversation) + Discovery-Push als gemeinsame Sub-Commands.
- **DSGVO-kompatibel** (siehe DSFA-Vermerk).

### Negativ

- **Single-Point-of-Failure** Orchestrator: wenn `orchestrator.iil.pet`
  down ist, fällt der Cross-Repo-Picker auf den lokalen Fallback zurück
  (= weiterhin Repo-lokale Konstante). **Mitigation**: Picker hat
  Auto-Fallback (`fetch.catch → CROSS_REPO_INDEX`).
- **Lock-in**: pgvector-Schema ist orchestrator-spezifisch. Migration
  zu anderem Vektor-DB-Backend = Schema-Übersetzung. **Mitigation**:
  Discovery-API-Vertrag (REST/JSON) abstrahiert vom Schema.
- **Latenz**: jeder Picker-Render lädt Discovery-Liste — Mitigation:
  Client-Cache + Pull-once-per-session.

## Alternativen

1. **Statisches JSON im `~/github`-Symlink-Pattern**: pro Klickdummy ein
   Sync auf eine globale `cross-repo-index.json` als Symlink. Niedriger
   Aufwand, aber keine semantische Search. *Verworfen*: pgvector ist
   schon da, der Mehrwert (semantic) ist Trumpf.
2. **GitHub Search API als Discovery**: über `gh search` alle Klickdummy-
   Specs cross-org finden. Authentisierung + Rate-Limit-Issue. *Verworfen*:
   nicht semantisch, Token-Drift-Risiko (siehe Drift-Memory
   `pat-in-remote-url-leak` aus Iter. 21).
3. **Stage 2 sofort (iil.pet-Hosting)**: mehr Mehrwert, aber höhere
   Komplexität (Hosting, DNS, TLS, Backup, Service-Lifecycle). *Verschoben*:
   Stage 1.5 zuerst, A nachgelagert nach Empirie.

## Phase-A-Bauauftrag (heute, Iter. 23)

| Schritt | Was | Wo |
|---|---|---|
| 1 | Diese ADR | `platform/docs/adr/ADR-215-...md` |
| 2 | Roadmap-Issue für iil-klickdummy v1.5 | `iilgmbh/iil-klickdummy/issues` |
| 3 | PoC `sync push --to-orchestrator` | `iilgmbh/iil-klickdummy` branch |
| 4 | Empirie-PR: Cross-Repo-Picker fetch | `meiki-hub` branch |

## Erfolgskriterien

- Discovery-API liefert mind. die 8 aktuell live Klickdummies + ihre
  Metadaten (spec_id, version, class, topic, adr).
- Cross-Repo-Picker in meiki-hub (Empirie #1) konsumiert die API,
  fällt bei Service-Ausfall auf lokalen Fallback zurück.
- Semantische Test-Query: „Eskalation" liefert mind. 3 relevante
  Klickdummies aus mind. 2 Orgs.

## Provenance

- 2026-05-21 (meiki-hub-Session Iter. 22): User-Frage „sind wir nun an der
  Schwelle um 1. klickdummy zu stagen → auf iil.pet ? 2 auf
  postgres/pgverctor?"
- Antwort: Trennung A (iil.pet-Hosting) vs. B (pgvector-Discovery);
  B als Stage 1.5 vorgeschlagen
- User-Entscheidung: Schritte 1–4 ausführen, DSFA-Ergebnis nicht kritisch
- Diese ADR ist Schritt 1.
