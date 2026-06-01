---
id: ADR-215
title: "Klickdummy Discovery via Orchestrator pgvector (Stage 1.5)"
status: accepted
date: 2026-05-21
deciders: ["Achim Dehnert"]
tags: ["klickdummy", "discovery", "pgvector", "orchestrator", "stage-1.5"]
related:
  - "platform:ADR-211"          # Klickdummy-Rahmen (extends)
  - "platform:ADR-113"          # Orchestrator pgvector (extends)
  - "platform:ADR-210"          # Local-Staging-Prod-Architecture
  - "platform:ADR-212"          # Traefik-Ingress iil.pet
  - "meiki:ADR-027"             # Conversational Klickdummy (Schwester-Empirie)
  - "iilgmbh:iil-klickdummy v1.8" # pip-Paket (discovery_push-PoC seit v1.8.0)
supersedes: []
superseded_by: []
# Diese ADR beschreibt einen DISCOVERY-Layer, keinen Klickdummy-Instanz.
# Daher kein class/sunset_after Frontmatter.
---

# ADR-215 · Klickdummy Discovery via Orchestrator pgvector (Stage 1.5)

## Status

**accepted** (2026-06-01, Decider: Achim Dehnert). Die Stage-1.5-Entscheidung
ist ratifiziert. PoC in `iilgmbh/iil-klickdummy` (gemergt, v1.8.0, **inert** —
kein fester Endpunkt, keine Automatik). Empirie #1 als Cross-Repo-Picker-Fetch
in `meiki-hub`.

> **Annahme-Auflage:** Die acht Punkte aus **§Amendment 1** (Review-Härtung
> 2026-06-01) sind mit der Annahme **verbindliche Implementierungs-Auflagen** —
> die Produktiv-Aktivierung (fester Endpunkt + Orchestrator-Schema-Migration)
> erfolgt erst, wenn sie erfüllt sind. „Accepted" ratifiziert den *Plan inkl.
> Auflagen*, nicht deren Fertigstellung.

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

1. **`iil-klickdummy` `klickdummy sync push --to-orchestrator`**:
   Pro Klickdummy ein Embedding über `(title + purpose +
   parity_acceptance-Texte + topic)` + Metadaten (spec_id, version, class,
   topic, adr, repo, path_rel, last_seen, klickdummy_class, personas[]).
   **Provenance-Pflichtfelder** (REC-1): `source_repo`, `source_ref` (Branch/Tag),
   `commit_sha`, `spec_sha256`, `generated_at` — damit jeder Registry-Eintrag auf
   seinen exakten Spec-Stand zurückführbar und gegen Drift prüfbar ist.
   **Upsert-Identität** (REC-2): `registry_key = org/repo + path_rel + spec_id`;
   `version`/`pipeline_status`/`adr` werden bei Änderung aktualisiert.
2. **Orchestrator-pgvector** speichert die Embeddings + Metadata in
   einer eigenen `agent_memory_*`-Sub-Collection `klickdummy-registry`.
   Diese Collection ist ein **abgeleiteter Index, kein System of Record** —
   normative Quelle bleibt die Spec im Repo (siehe §Amendment 1, REC-20).
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
- **Feedback-Aggregation cross-Repo** — **explizites Nicht-Ziel** dieser ADR
  (REC-13): keine Erfolgserwartung in Stage 1.5. Eine spätere Stage 1.6 braucht
  eine **eigene** Datenschutz-/Governance-Prüfung (Stakeholder-Stimmen cross-org
  ≠ Klickdummy-Metadaten) — nicht implizit „auf demselben Layer" mitlaufen lassen.
- **Server-seitig** liegt Discovery im bestehenden Orchestrator-Scope (analog
  `agent_memory_*`). **Klarstellung (AD-3):** *renderer-seitig* entsteht sehr wohl
  eine **neue, runtime-relevante Kopplung** (Picker → Orchestrator-API über mehrere
  Repos/Orgs). Deren Vertrag wird in §Amendment 1 (REC-4) verbindlich (API-Version,
  Timeout, Error-Shape, Degradationsmodus).

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
4. **Git-native Discovery-Manifeste + Orchestrator-Pull statt Repo-Push**
   (Review-Ansatz A): jedes Repo veröffentlicht ein signiertes
   `klickdummy.discovery.json`; der Orchestrator pullt/crawlt diese periodisch.
   Vorteil: kein Push-Token je Repo, stärkere Auditierbarkeit, klarere SSoT-Grenze.
   Nachteil: Orchestrator braucht Repo-Lesezugriff + Polling/Rate-Limit-Handling.
   *Offen gehalten*: ernsthaft als Härtung gegen Auth-/Audit-Lücken (REC-8/15) zu prüfen.
5. **Registry-Ledger zuerst, pgvector nur als Derived View** (Review-Ansatz B):
   append-only Tabelle (`repo`, `spec_id`, `commit_sha`, `spec_sha`, `adr`,
   `pipeline_status`, `visibility_scope`, `last_seen`, `tombstone`); Embeddings sind
   sekundäre Suchansicht. *Zielbild*: maximale SSoT-/Audit-Stärke (deckt REC-1/5/15).
   Stage 1.5 darf klein starten, diese Ledger-Form aber **nicht verbauen**.

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

## Amendment 1 (2026-06-01) — Härtung vor Annahme

Aus einer Review-Runde (externe Zweitmeinung via `/adr-handoff-extern` +
interner Evidenz-Prüfung gegen den PoC-Code). Verdikte/IDs als Nachweis im
Rückfluss-Protokoll. **Diese acht Punkte sind vor `accepted` verbindlich.**

**1 · Registry = abgeleiteter Index, nicht zweite Wahrheit** (REC-1, REC-20 ←
AD-1, AD-6, M28-1). Verbindlicher Leitsatz: *„Discovery steuert Auffindbarkeit,
Ranking und Navigation, niemals Acceptance, Lifecycle-Status oder fachliche
Wahrheit ohne Referenz auf Spec/ADR."* Provenance-Felder (`source_repo`,
`source_ref`, `commit_sha`, `spec_sha256`, `generated_at`) machen jeden Eintrag
rückführbar; Drift gegen `spec_sha256` ist erkennbar.

**2 · Lifecycle: TTL / Tombstone / De-Registration** (REC-5 ← AD-4, AD-18, M28-5).
`last_seen` ohne frischen Sync → Eintrag wird nach Frist als *stale* markiert,
dann ausgeblendet; bei ADR-211-Off-Ramp/Sunset (I3) → `tombstone`. Verhindert,
dass Discovery tote/archivierte/verschobene Klickdummies als Suchmüll hält.

**3 · Runtime-Kopplung + API-Vertrag** (REC-4, REC-10, REC-12 ← AD-3, AD-13, AD-15,
M28-7). Die Picker→Orchestrator-Abhängigkeit ist neu und runtime-relevant.
Mindestvertrag: `api_version`, `registry_schema_version`, Timeout, Error-Shape,
Cache-Verhalten, Degradationsmodus; Kompatibilitätsfenster bei Schema-Wechsel.
Route-Semantik (`route_kind`, `base_url_profile`) statt nur `path_rel`.

**4 · Sicherheit & Souveränität** (REC-6, REC-7, REC-8, REC-15 ← AD-7, AD-8, AD-9,
AD-10, AD-20, AD-21, M28-4). `visibility_scope ∈ {repo, org, allowlist,
public-demo}` mit erzwungenem Org-Filter (Public-Sector/Citizen-facing-Orgs
können engere Sichtbarkeit brauchen als die Default-Org). Ingestion-Guard: nur
`class: mock`-konforme, push-berechtigte Klickdummies; Embedding-Input
(`embedding_text`) ist redigiert + auditierbar. **AuthZ-Policy** (Mechanismus —
optionaler Bearer-Token — existiert bereits im PoC): Scope, Rotation,
Secret-Speicherort, CI-Nutzung festschreiben. Audit-Trail pro Push.

**5 · Sichtbarkeits-Governance** (REC-14 ← AD-17). „Erscheint automatisch nach
Sync" verschiebt Governance auf den Push. Gegenmaßnahme: `discoverable: true`
muss aus Spec/ADR/Repo-Konfig stammen — nicht allein durch technischen Push
entstehen.

**6 · Fallback härten** (REC-3 ← AD-2, AD-19, AD-23, M28-2). Der Picker fällt
nicht auf manuell gepflegte `CROSS_REPO_INDEX`-Konstanten zurück (= konserviert
genau die Drift, die Stage 1.5 abschafft), sondern auf den **zuletzt
erfolgreichen, signierten Orchestrator-Snapshot**. Manuelle Konstanten nur noch
temporär mit Ablaufdatum. *(pgvector-Backend bleibt gesetzt — ADR-113.)*

**7 · Erfolgskriterien & Skalierung** (REC-9, REC-17, REC-19 ← AD-11, AD-12,
M28-3, M28-8, M28-9). Statt Einzelquery eine **Search-Eval-Suite** (Fixture-Queries,
erwartete Top-k, Precision-Minimum, Negativbeispiele); Skalentest mit 50–100
Einträgen (Latenz, Suchqualität, Sync-Dauer); `embedding_model(_version)` +
Reindex-Befehl für Modellwechsel.

**8 · Filter/Taxonomie, Scope & Ist-Stand** (REC-13, REC-16, REC-18 ← AD-16,
AD-24, AD-25, M28-6, M28-10). Pflichtfilter für Discovery-Ergebnisse: Org, Repo,
Topic, UX-Genre, `class`, `pipeline_status`, Off-Ramp/Sunset-Status, Sichtbarkeit.
Stage-2-kompatible Felder benennen (Hosting-URLs/TLS/DNS vs. heutige
`path_rel`-Annahmen).

### Reconciliation mit bestehender Consumer-Hälfte (eigene Evidenz-Prüfung)

- **C-1:** Die **Query/Consumer-Seite existiert bereits** als Skill
  `klickdummy-search` (semantische Cross-Repo-Suche via Orchestrator-pgvector,
  read-only — ADR-211 Rev 14 Stufe-2-Konsument). ADR-215 (Push/Producer) und
  `klickdummy-search` (Query) sind zwei Hälften desselben Layers; der Discovery-
  API-Vertrag (Punkt 3) **muss** mit dem Such-Skill abgeglichen werden.
- **C-2:** Der PoC `discovery_push.py` (v1.8.0) implementiert bereits `--dry-run`,
  `push --to-orchestrator`, optionalen Bearer-Token, `sunset_after` und
  `embedding_text`. Mehrere obige Punkte sind damit **teil-erfüllt** — die ADR
  beschreibt den Soll-Zustand, nicht eine grüne Wiese.

## Provenance

- 2026-05-21 (meiki-hub-Session Iter. 22): User-Frage „sind wir nun an der
  Schwelle um 1. klickdummy zu stagen → auf iil.pet ? 2 auf
  postgres/pgverctor?"
- Antwort: Trennung A (iil.pet-Hosting) vs. B (pgvector-Discovery);
  B als Stage 1.5 vorgeschlagen
- User-Entscheidung: Schritte 1–4 ausführen, DSFA-Ergebnis nicht kritisch
- Diese ADR ist Schritt 1.
- 2026-06-01: PoC als `iil-klickdummy` v1.8.0 gemergt (inert). Review-Runde
  (externe Zweitmeinung + interne PoC-Evidenz-Prüfung) → §Amendment 1; 18 belegte
  Lücken eingearbeitet (platform PR #371).
- 2026-06-01: **Ratifiziert → `accepted`** (Decider: Achim Dehnert). Die acht
  §Amendment-1-Punkte gelten als verbindliche Implementierungs-Auflagen vor
  Produktiv-Aktivierung.
