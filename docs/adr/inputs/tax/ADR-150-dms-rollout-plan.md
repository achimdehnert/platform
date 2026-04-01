---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-146  # risk-hub → DMS Audit Trail (Phase 0, bereits accepted)
  - ADR-149  # Inbound Scan HP E58650 + Fujitsu iX1600
  - ADR-044  # MCP-Hub Architecture Consolidation
  - ADR-036  # Chat-Agent Ecosystem
  - ADR-050  # Hub Landscape
staleness_months: 6
drift_check_paths:
  - src/dms_archive/
  - src/dms_inbound/
  - mcp-hub/servers/dvelop_mcp.py
  - research-hub/apps/archive/
---

# ADR-150: Adopt fünfstufigen Rollout-Plan für d.velop DMS Platform-Integration

## Metadaten

| Attribut       | Wert                                                                          |
|----------------|-------------------------------------------------------------------------------|
| **Status**     | Proposed                                                                      |
| **Scope**      | platform                                                                      |
| **Erstellt**   | 2026-03-25                                                                    |
| **Autor**      | Achim Dehnert                                                                 |
| **Relates to** | ADR-146, ADR-149, ADR-044, ADR-036, ADR-050                                  |

## Repo-Zugehörigkeit

| Repo           | Rolle    | Betroffen                                        |
|----------------|----------|--------------------------------------------------|
| `dms-hub`      | Primär   | alle 5 Phasen                                    |
| `mcp-hub`      | Sekundär | Phase 2 (`dvelop_mcp.py`)                        |
| `risk-hub`     | Sekundär | Phase 0 bereits done (ADR-146)                   |
| `research-hub` | Sekundär | Phase 4 (`apps/archive/`)                        |
| `platform`     | Referenz | ADRs, Outline-Ablösung Phase 5                   |

---

## Decision Drivers

- **Landratsamt geht produktiv**: Erste Behördenkunde erwartet Ende-zu-Ende-DMS-Integration — kein Big-Bang-Release, sondern schrittweiser Aufbau mit nachweisbarem Fortschritt nach jeder Phase.
- **Abhängigkeiten erzwingen Reihenfolge**: MCP-Agenten-Zugriff ohne Dokumente im DMS ist wertlos — Inbound Scan muss vor dem MCP-Server produktiv sein.
- **Risikominimierung**: Jede Phase ist ein eigenständig deploybare Einheit. Schlägt Phase 3 fehl, laufen Phase 1 und 2 unberührt weiter.
- **Outline-Ablösung ist Change-Management**: Die größte Verhaltensänderung für Nutzer kommt zuletzt, wenn das DMS-Fundament erprobt ist.

---

## 1. Context and Problem Statement

ADR-146 (risk-hub Audit Trail) ist Phase 0 — bereits spezifiziert. Fünf weitere
Integrationsstufen bauen aufeinander auf, wurden aber noch nicht als verbindliche
Reihenfolge festgelegt. Ohne diese Priorisierung besteht das Risiko, dass der
MCP-Server (niedrigster Aufwand) zuerst gebaut wird, aber mangels Dokumenten im
DMS keinen Mehrwert liefert.

### 1.1 Abhängigkeitsgraph

```
Phase 0  risk-hub Audit Trail          → ADR-146 ✅ spezifiziert
         │
Phase 1  Inbound Scan (ADR-149)        → Dokumente fließen erstmals ins DMS
         │
Phase 2  MCP-Server dvelop             → Cascade kann jetzt auf Dokumente zugreifen
         │
Phase 3  KI-Klassifikation             → verbessert Phase 1 (aifw-Routing)
         │
Phase 4  research-hub Quellenarchiv    → unabhängig, aber baut auf DMS-Client auf
         │
Phase 5  Schriftgutverwaltung          → löst Outline-Seiten ab; nur wenn 1–4 stabil
```

---

## 2. Considered Options

### Option A — Sequenzieller Rollout (gewählt) ✅

Feste Reihenfolge, jede Phase hat eigene Acceptance Criteria.
Nächste Phase startet erst wenn Done-Kriterien der vorherigen erfüllt.

### Option B — Paralleler Aufbau

Alle 5 Phasen laufen gleichzeitig, unabhängige Teams.

**Abgelehnt**: Solo-Entwickler-Setup; parallele Arbeit erzeugt halbfertige
Integrationen ohne Nutzbarkeit. Abhängigkeiten (Phase 2 braucht Phase 1)
machen Parallelisierung sinnlos.

### Option C — MCP-First

MCP-Server zuerst als Entwickler-Testtool während Inbound gebaut wird.

**Abgelehnt**: MCP ohne Dokumente im DMS hat kein Produktions-Nutzen.
Testnutzen rechtfertigt keinen eigenen Roadmap-Schritt — MCP kann als
Nebenprodukt von Phase 1 entstehen (unter 1 Tag Aufwand).

---

## 3. Decision Outcome

**Gewählt: Option A** — sequenzieller Rollout mit Gates zwischen den Phasen.

Die korrigierte Reihenfolge gegenüber dem ursprünglichen Vorschlag:
`Inbound Scan → MCP → KI → research-hub → Schriftgut` statt
`MCP → Inbound → KI → research-hub → Schriftgut`.

---

## 4. Phasenbeschreibungen

### Phase 1 — Inbound Scan (ADR-149)

**Ziel**: Beide Scanner schreiben automatisch in d.velop DMS.

**Scope**:
- WireGuard-Peer für Fritzbox Landratsamt konfiguriert
- Samba-Container (`dms-samba`) in `dms-hub` deployed
- HP PageWide E58650 EWS-Konfiguration: SMBv3, Subfolder `hp-e58650/`
- Fujitsu iX1600 PaperStream-Profil: SMB-Zielordner `ix1600/`
- `dms_inbound` Django-App: `InboundScanRecord`, `process_scan_directory`-Task
- Celery Beat alle 30s, SHA-256-Duplikaterkennung, Kategorie aus Ordnerstruktur

**Done-Kriterien**:
- [ ] Testdokument via HP E58650 → `InboundScanRecord(status=SUCCESS)` in DB
- [ ] Testdokument via iX1600 → `InboundScanRecord(status=SUCCESS)` in DB
- [ ] Duplikat-Test: gleiche Datei zweimal → zweiter Eintrag `status=DUPLICATE`
- [ ] d.velop-Dokument unter `https://iil.d-velop.cloud` abrufbar
- [ ] `dms-samba` Healthcheck grün in `docker ps`

**Aufwand**: ~3–4 Tage

---

### Phase 2 — MCP-Server für d.velop (ADR-147)

**Ziel**: Cascade/Windsurf kann Dokumente im DMS suchen, abrufen und ablegen.

**Scope**: Neuer FastMCP-Server `dvelop_mcp.py` in `mcp-hub` mit 4 Tools:

```python
@mcp.tool()
def dvelop_search(query: str, category: str | None = None) -> list[dict]:
    """Volltext-Suche im d.velop DMS."""

@mcp.tool()
def dvelop_get_document(doc_id: str) -> dict:
    """Dokument-Metadaten und Download-URL abrufen."""

@mcp.tool()
def dvelop_upload(filename: str, content_b64: str, category: str,
                  properties: dict) -> str:
    """Dokument ins DMS hochladen, doc_id zurückgeben."""

@mcp.tool()
def dvelop_list_categories(repo_id: str) -> list[dict]:
    """Verfügbare Kategorien im Repository auflisten."""
```

**Implementierungsregel**: Alle Tools sind synchron — `asgiref.async_to_sync`
wenn nötig, niemals `asyncio.run()` in FastMCP-Kontext.

**Done-Kriterien**:
- [ ] `dvelop_search("Bebauungsplan")` gibt ≥ 1 Ergebnis aus Phase-1-Dokumenten zurück
- [ ] `dvelop_upload(...)` legt Testdokument im DMS an, gibt valide `doc_id`
- [ ] Server in Windsurf `mcp_servers.json` eingetragen und verbunden
- [ ] Cascade kann via Tool auf Dokument aus Phase 1 zugreifen

**Aufwand**: ~1 Tag (nutzt bestehenden `DvelopDmsClient` aus ADR-146)

---

### Phase 3 — KI-gestützte Dokumentenklassifikation

**Ziel**: Eingehende Scans werden automatisch kategorisiert und verschlagwortet —
kein manuelles Einsortieren durch Mitarbeitende.

**Scope**:
- Neues Celery-Task `classify_inbound_document` auf Queue `"ai"`
- Wird nach erfolgreichem `process_scan_directory` getriggert
- Nutzt `aifw` (ADR-095/096) mit Quality Level `MEDIUM` (Sonnet)
- Prompt: Dokumentbild (erste Seite als Base64) → JSON mit `category`, `tags`, `confidence`
- `InboundScanRecord` erhält Felder: `ai_category`, `ai_tags`, `ai_confidence`
- Wenn `confidence >= 0.85`: d.velop-Kategorie automatisch gesetzt
- Wenn `confidence < 0.85`: Dokument landet in `INBOX_UNCLASSIFIED` zur manuellen Prüfung

**Kategorien** (initial, erweiterbar):
```python
DMS_CATEGORY_HINTS = {
    "Bebauungsplan":        "INBOUND_BPLAN",
    "Bescheid":             "INBOUND_BESCHEID",
    "Antrag":               "INBOUND_ANTRAG",
    "Protokoll":            "INBOUND_PROTOKOLL",
    "Rechnung":             "INBOUND_RECHNUNG",
    "Vertrag":              "INBOUND_VERTRAG",
}
```

**Done-Kriterien**:
- [ ] 10 Testdokumente klassifiziert: ≥ 8 korrekte Kategorie (80 % Accuracy)
- [ ] `confidence < 0.85` → Dokument in `INBOX_UNCLASSIFIED` (kein stiller Fehler)
- [ ] `aifw`-Task-ID im `InboundScanRecord` protokolliert
- [ ] Kein `asyncio.run()` im Celery-Task (ADR-Plattformregel)

**Aufwand**: ~2–3 Tage

---

### Phase 4 — research-hub Quellenarchiv

**Ziel**: Rechercheergebnisse (PDFs, Webseiten-Snapshots, Gutachten) werden aus
research-hub dauerhaft im d.velop DMS archiviert — durchsuchbar über d.velop
Volltext-Index statt nur in der research-hub-Datenbank.

**Scope**:
- Neue Django-App `archive` in `research-hub`
- `ResearchArchiveRecord` (analog `DmsArchiveRecord` aus ADR-146, gleiche Struktur)
- Service-Hook in `research-hub/apps/research/services.py`: nach `finalize_source()`
- Celery-Task auf Queue `"dms"`, nutzt denselben `DvelopDmsClient`
- d.velop-Kategorie: `RESEARCH_SOURCE`
- Properties: `{"Titel": ..., "URL": ..., "Quelle": "research-hub", "Datum": ...}`

**Abgrenzung**: Dieser Schritt archiviert **abgeschlossene** Recherche-Quellen,
keine laufenden oder Draft-Dokumente. Outline-Wiki-Seiten bleiben unberührt.

**Done-Kriterien**:
- [ ] `finalize_source()` → `ResearchArchiveRecord(status=SUCCESS)` in DB
- [ ] Quelldokument in d.velop unter Kategorie `RESEARCH_SOURCE` abrufbar
- [ ] Volltext-Suche via `dvelop_search` (Phase-2-MCP-Tool) findet archivierte Quelle
- [ ] Kein Einfluss auf bestehende research-hub-Tests

**Aufwand**: ~1–2 Tage

---

### Phase 5 — Schriftgutverwaltung (Outline-Ablösung)

**Ziel**: Dienstanweisungen, Verfahrensanweisungen und rechtsverbindliche
Dokumente aus Outline-Seiten in d.velop überführen — mit Freigabe-Workflow
und Revisionssicherheit.

**Scope**:
- Identifikation der Outline-Seiten die in d.velop gehören
  (Kriterium: Freigabepflicht, Aufbewahrungspflicht, oder rechtliche Bindung)
- Einmaliger Export: Outline-API → Markdown → PDF → d.velop-Upload
- d.velop-Kategorie: `DIENSTANWEISUNG`, `VERFAHRENSANWEISUNG`, `BETRIEBSKONZEPT`
- Outline bleibt für interne IIL-Entwicklerdokumentation (ADRs, Konzepte, Wikis)
- Einfaches HTMX-Widget in dms-hub: "Dokument aus Outline importieren"

**Abgrenzung — was NICHT migriert wird**:
- ADRs → bleiben in GitHub (`platform/docs/adr/`)
- Konzeptpapiere → bleiben in Outline
- Sprint-Notizen, Meeting-Notes → bleiben in Outline
- Technische Handbücher für Entwickler → bleiben in Outline

**Done-Kriterien**:
- [ ] Kriterien-Tabelle "was gehört ins DMS" schriftlich definiert und in ADR eingetragen
- [ ] ≥ 3 produktive Outline-Seiten erfolgreich nach d.velop migriert
- [ ] Freigabe-Workflow in d.velop für `DIENSTANWEISUNG` konfiguriert
- [ ] Outline-Seiten nach Migration mit Hinweis versehen: "Maßgebliche Version: d.velop"
- [ ] Kein Datenverlust: Outline-Original bleibt als Archiv-Read-Only erhalten

**Aufwand**: ~3–5 Tage (inkl. Inhalts-Entscheidungen)

---

## 5. Migration Tracking

| Phase | Beschreibung                  | ADR     | Status          | Datum | Notiz                      |
|-------|-------------------------------|---------|-----------------|-------|----------------------------|
| 0     | risk-hub Audit Trail          | ADR-146 | ⬜ Ausstehend   | –     | Spezifiziert, impl. pending |
| 1     | Inbound Scan                  | ADR-149 | ⬜ Ausstehend   | –     | WG-Peer + Samba + Task     |
| 2     | MCP-Server dvelop             | ADR-147 | ⬜ Ausstehend   | –     | 4 Tools, ~1 Tag            |
| 3     | KI-Klassifikation             | –       | ⬜ Ausstehend   | –     | aifw MEDIUM, 80 % Accuracy |
| 4     | research-hub Quellenarchiv    | –       | ⬜ Ausstehend   | –     | analog ADR-146             |
| 5     | Schriftgutverwaltung          | –       | ⬜ Ausstehend   | –     | nach Phase 1–4 stabil      |

**Gate-Regel**: Phase N+1 startet erst wenn alle Done-Kriterien von Phase N erfüllt.

---

## 6. Consequences

### 6.1 Good

- Jede Phase liefert eigenständig nutzbaren Mehrwert — kein "Alles oder Nichts"
- Abhängigkeitsfehler werden durch Gates ausgeschlossen
- Aufwandspeak verteilt sich: ~1–2 Wochen gesamt über 4–6 Wochen Kalenderzeit
- MCP-Server (Phase 2) profitiert sofort von Phase-1-Dokumenten

### 6.2 Bad

- Sequenzieller Rollout bedeutet: Phase 5 ist frühestens in ~6 Wochen produktiv
- Gate-Disziplin erfordert explizite Done-Bestätigung vor jedem nächsten Schritt

### 6.3 Nicht in Scope

- Automatische Outline-zu-d.velop-Synchronisation in Echtzeit
- d.velop-Benutzeroberfläche für Endnutzer (liegt beim Landratsamt, nicht Platform)
- d.velop Workflow-Engine (Genehmigungsprozesse über die vorhandenen Basis-Workflows hinaus)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| HP EWS SMBv3-Probleme verzögern Phase 1 | Mittel | Mittel | Frühzeitiger Verbindungstest; Fallback-Firmware-Update |
| d.velop API-Änderung bricht Phasen 2–4 | Niedrig | Hoch | Client isoliert in `dms_hub/client/`; ADR-Drift alle 6 Monate |
| KI-Accuracy < 80 % in Phase 3 | Mittel | Mittel | Confidence-Threshold senken; mehr Trainingsbeispiele im Prompt |
| Phase-5-Inhalts-Entscheidungen dauern länger | Hoch | Niedrig | Gate schützt Phasen 1–4; Phase 5 kann warten |

---

## 8. Confirmation

1. **Gates**: Jede Phase hat messbare Done-Kriterien (Checkboxen in §4). Keine Phase startet ohne vollständige Done-Bestätigung der vorherigen.
2. **Migration Tracking**: §5 wird nach jeder Phase aktualisiert (`⬜ → ✅`).
3. **Drift-Detector**: Dieses ADR wird alle 6 Monate auf Aktualität geprüft — Phase-Status muss aktuell sein.
4. **ADR-147**: wird erstellt wenn Phase 2 beginnt (MCP-Server Spezifikation).

---

## 9. More Information

| Referenz | Inhalt |
|----------|--------|
| ADR-146 | risk-hub → DMS Audit Trail — Phase 0, Celery-Task-Muster |
| ADR-149 | Inbound Scan — HP E58650 + iX1600, SMB, WireGuard |
| ADR-044 | MCP-Hub Architektur — FastMCP-Server-Pattern |
| ADR-095/096 | aifw Quality-Level-Routing — Phase 3 nutzt MEDIUM |
| ADR-050 | Hub Landscape — research-hub, dms-hub Einordnung |

---

## 11. Migration Tracking — Detaillog

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-150 erstellt | ✅ Done | 2026-03-25 | |
| ADR-150 Review | ⬜ Pending | – | |
| Phase 1 Start | ⬜ Pending | – | Warten auf WG-Key Landratsamt |
| Phase 1 Done (alle Kriterien ✅) | ⬜ Pending | – | |
| Phase 2 Start | ⬜ Pending | – | Gate Phase 1 |
| Phase 2 Done | ⬜ Pending | – | |
| Phase 3 Start | ⬜ Pending | – | Gate Phase 2 |
| Phase 3 Done | ⬜ Pending | – | |
| Phase 4 Start | ⬜ Pending | – | Gate Phase 3 |
| Phase 4 Done | ⬜ Pending | – | |
| Phase 5 Start | ⬜ Pending | – | Gate Phase 4 + explizite Freigabe |
| Phase 5 Done | ⬜ Pending | – | |
| ADR-150 Status → Accepted | ⬜ Pending | – | Nach Phase 2 Done |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
