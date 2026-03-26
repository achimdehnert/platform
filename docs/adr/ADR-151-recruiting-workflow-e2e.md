# ADR-151: End-to-End Recruiting-Workflow — LinkedIn Recruiter × Hunter CRM × Recruiting Hub

| Attribut       | Wert                                    |
|----------------|-----------------------------------------|
| **Status**     | Proposed                                |
| **Scope**      | Workflow / Integration                  |
| **Repo**       | recruiting-hub                          |
| **Erstellt**   | 2026-03-26                              |
| **Autor**      | Achim Dehnert                           |
| **Reviewer**   | —                                       |
| **Supersedes** | –                                       |
| **Relates to** | ADR-148 (Recruiting Hub Architecture), ADR-137 (Tenant-Lifecycle), ADR-093 (aifw), ADR-045 (Secrets) |
| **implementation_status** | not_started                   |

---

## 1. Kontext

### 1.1 Ausgangslage

Der operative Recruiting-Workflow des Kunden (Personalberatung) nutzt drei Systeme:

| System | Rolle | Betreiber |
|--------|-------|-----------|
| **LinkedIn Recruiter** | Sourcing: Suchen, Kandidaten identifizieren, Anschreiben | LinkedIn (SaaS) |
| **Hunter CRM** (hunter-software.de) | CRM: Kandidaten-Stammdaten, Kommunikation, Langzeitpflege | Hunter Software (SaaS) |
| **Recruiting Hub** (hr.iil.pet) | Pipeline: Approval-Workflow, Dublettencheck, LLM-Scoring, Reporting | IIL Platform (Self-hosted) |

### 1.2 Ist-Prozess (manuell)

Aktuell läuft der gesamte Prozess manuell, ohne Automatisierung oder
Systemübergaben zwischen den drei Tools:

```
1. Sophia erstellt Suchprojekt (Kopf / Notizen)
2. Sophia führt Suche in LinkedIn Recruiter durch
3. Sophia scrollt durch Profile, bewertet im Kopf
4. Sophia kopiert Profildaten manuell in Hunter CRM
5. Sophia prüft manuell auf Dubletten in Hunter
6. Sophia schreibt Kandidaten über LinkedIn an
7. Sophia pflegt Rückmeldungen manuell in Hunter CRM
8. Sophia erstellt manuell Reports für den Kunden
```

**Probleme:**
- Kein Dublettencheck → gleiche Kandidaten werden mehrfach kontaktiert
- Keine Pipeline-Übersicht → Wo steht welcher Kandidat?
- Kein Scoring → Subjektive Bewertung, nicht nachvollziehbar
- Keine Metriken → Response-Rate, Conversion unbekannt
- Zeitfressend → 70% der Zeit für Datenübertragung statt Kandidatenbewertung

### 1.3 Soll-Prozess (Zielarchitektur)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ LinkedIn         │    │  Recruiting Hub   │    │   Hunter CRM    │
│ Recruiter        │    │  (hr.iil.pet)     │    │   (hunter-sw)   │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│                  │    │                  │    │                 │
│ 1. Suche anlegen │◄──│ Suchstrings (LLM)│    │                 │
│                  │    │                  │    │                 │
│ 2. Profile       │──►│ CSV-Import       │    │                 │
│    exportieren   │    │ + Duplettencheck │    │                 │
│                  │    │                  │    │                 │
│                  │    │ 3. Pipeline:     │    │                 │
│                  │    │    Sourced       │    │                 │
│                  │    │    → Reviewed    │    │                 │
│                  │    │    → Approved ───│───►│ 4. Import +     │
│                  │    │                  │    │    Duplettencheck│
│                  │    │                  │    │                 │
│ 5. Anschreiben   │◄──│ Vorlagen (LLM)  │    │                 │
│    via LinkedIn   │    │                  │    │                 │
│                  │    │                  │    │                 │
│ 6. Rückmeldung  │──►│ Status-Update    │──►│ Datenpflege      │
│                  │    │ Pipeline:        │    │ Kommunikations-  │
│                  │    │ Replied/         │    │ historie         │
│                  │    │ Interview/       │    │                 │
│                  │    │ Placed           │    │                 │
│                  │    │                  │    │                 │
│                  │    │ 7. Reporting     │    │                 │
│                  │    │    KPIs, Funnel  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 2. Entscheidung

### 2.1 Workflow-Schritte mit System-Zuordnung

Der End-to-End-Workflow wird in 7 Schritte unterteilt. Jeder Schritt hat
ein **führendes System** und definierte **Übergabepunkte**:

| # | Schritt | Führendes System | Input | Output | Human-in-the-Loop |
|---|---------|-----------------|-------|--------|-------------------|
| 1 | **Suche anlegen** | LinkedIn Recruiter | Suchprojekt aus Recruiting Hub | Boolean Search String | Nein (LLM-Vorschlag) |
| 2 | **Kandidaten identifizieren** | LinkedIn Recruiter → Recruiting Hub | LinkedIn-Profile | Kandidaten in Pipeline (Stage: Sourced) | Nein |
| 3 | **Freigabe** (Human-in-the-Loop) | Recruiting Hub | Sourced-Kandidaten + LLM-Score | Approved-Kandidaten | **Ja — Sophia Paul** |
| 4 | **Export nach Hunter CRM** | Recruiting Hub → Hunter CRM | Approved-Kandidaten | Leads in Hunter CRM (mit Duplettencheck) | Nein |
| 5 | **Anschreiben** | LinkedIn Recruiter | Nachrichtenvorlage aus Recruiting Hub | InMail/Nachricht gesendet | Ja (Vorlage prüfen) |
| 6 | **Rückmeldungen pflegen** | LinkedIn → Recruiting Hub → Hunter CRM | Antworten/Status | Status-Updates in beiden Systemen | Nein |
| 7 | **Reporting** | Recruiting Hub | Pipeline-Daten | KPIs, Funnel, Conversion-Raten | Nein |

### 2.2 Detaillierter Ablauf pro Schritt

#### Schritt 1: Suche anlegen (LinkedIn Recruiter Backend)

**Akteur**: Recruiter (z.B. Sophia Paul)
**System**: LinkedIn Recruiter + Recruiting Hub

```
Recruiting Hub                          LinkedIn Recruiter
┌─────────────────────┐                ┌─────────────────────┐
│ 1. Suchprojekt      │                │                     │
│    erstellen         │                │                     │
│    (Titel, Firma,    │                │                     │
│     Anforderungen)   │                │                     │
│                      │                │                     │
│ 2. LLM generiert     │                │                     │
│    Boolean Search    │──── copy ────►│ 3. Suche einfügen   │
│    String            │                │    und ausführen     │
│                      │                │                     │
│ (Phase 2: via aifw)  │                │ 4. Ergebnisse       │
│                      │                │    reviewen          │
└─────────────────────┘                └─────────────────────┘
```

**Phase 1**: Recruiter erstellt Suchprojekt im Hub, schreibt Suchstring manuell.
**Phase 2**: LLM generiert Boolean Search String aus Stellenbeschreibung (iil-aifw).

**Datenmodell**:
```python
class SearchProject(TenantModel):
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    requirements = models.TextField()
    boolean_search_string = models.TextField(blank=True)  # LLM-generiert oder manuell
    target_count = models.PositiveIntegerField(default=10)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```

#### Schritt 2: Kandidaten identifizieren (LinkedIn → Recruiting Hub)

**Akteur**: Recruiter
**Übergabe**: LinkedIn Recruiter → CSV-Export → Recruiting Hub Import

```
LinkedIn Recruiter                      Recruiting Hub
┌─────────────────────┐                ┌─────────────────────┐
│ 1. Suche ausführen   │                │                     │
│                      │                │                     │
│ 2. Profile markieren │                │                     │
│                      │                │                     │
│ 3. CSV-Export        │──── upload ──►│ 4. CSV-Import       │
│    (Name, Firma,     │                │    + Parsing        │
│     Titel, URL)      │                │                     │
│                      │                │ 5. Dublettencheck   │
│                      │                │    (E-Mail, URL,    │
│                      │                │     Fuzzy-Name)     │
│                      │                │                     │
│                      │                │ 6. Stage: "Sourced" │
│                      │                │    pro Projekt      │
└─────────────────────┘                └─────────────────────┘
```

**CSV-Import-Felder** (LinkedIn Recruiter Export):

| Feld | Pflicht | Beispiel |
|------|---------|---------|
| First Name | ✅ | Max |
| Last Name | ✅ | Mustermann |
| LinkedIn URL | ✅ | https://linkedin.com/in/max-mustermann |
| Company | ❌ | Example AG |
| Title | ❌ | Senior Developer |
| Email | ❌ | max@example.com |
| Location | ❌ | München |

**Dublettencheck-Logik** (Reihenfolge):
1. **Exakte LinkedIn-URL** → `duplicate` (wird nicht importiert)
2. **Exakte E-Mail** → `duplicate` (wird nicht importiert)
3. **Fuzzy Name + Firma** (pg_trgm, Schwelle 0.8) → `possible_duplicate` (Warnung)
4. Kein Match → `unique` (wird importiert)

#### Schritt 3: Freigabe — Human-in-the-Loop

**Akteur**: Sophia Paul (oder anderer Entscheider)
**System**: Recruiting Hub — Approval-Queue

```
Recruiting Hub Pipeline Board
┌─────────────────────────────────────────────────┐
│  Sourced (12)  │  Reviewed (5)  │  Approved (3) │
│ ┌───────────┐  │ ┌───────────┐  │ ┌───────────┐ │
│ │ Kandidat A │  │ │ Kandidat D│  │ │ Kandidat G│ │
│ │ Score: 8.2 │  │ │ Score: 7.5│  │ │ Score: 9.1│ │
│ │ [Review →] │  │ │ [✓] [✗]  │  │ │ [Export]  │ │
│ └───────────┘  │ └───────────┘  │ └───────────┘ │
│ ┌───────────┐  │ ┌───────────┐  │               │
│ │ Kandidat B │  │ │ Kandidat E│  │               │
│ │ Score: 6.1 │  │ │ Score: 4.2│  │               │
│ │ [Review →] │  │ │ [✓] [✗]  │  │               │
│ └───────────┘  │ └───────────┘  │               │
└─────────────────────────────────────────────────┘
```

**Regeln**:
- `Sourced → Reviewed`: Automatisch nach LLM-Scoring (Phase 2) oder manuell
- `Reviewed → Approved`: **Nur mit manueller Freigabe** (Human-in-the-Loop)
- Freigabe wird mit User + Timestamp geloggt (Audit-Trail)
- Abgelehnte Kandidaten: Stage `Rejected` mit Begründung

**Datenmodell**:
```python
class ApprovalDecision(TenantModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    project = models.ForeignKey(SearchProject, on_delete=models.CASCADE)
    decision = models.CharField(choices=[("approved", "Approved"), ("rejected", "Rejected")])
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)
```

#### Schritt 4: Export nach Hunter CRM (inkl. Dublettencheck)

**System**: Recruiting Hub → Hunter CRM
**Trigger**: Kandidat wird auf "Approved" gesetzt

```
Recruiting Hub                          Hunter CRM
┌─────────────────────┐                ┌─────────────────────┐
│ Kandidat: Approved   │                │                     │
│                      │                │                     │
│ Phase 1:             │                │                     │
│ [CSV-Export-Button]  │── download ──►│ Manueller Import    │
│                      │                │ + Duplettenprüfung  │
│                      │                │                     │
│ Phase 2 (API):       │                │                     │
│ [Auto-Export]        │── API-Call ──►│ Automatischer Import│
│                      │◄── Response ──│ + Duplettencheck    │
│                      │                │ + Kandidaten-ID     │
│                      │                │                     │
│ Hunter-Ref speichern │                │                     │
│ (für Status-Sync)    │                │                     │
└─────────────────────┘                └─────────────────────┘
```

**Export-Daten**:
- Name, E-Mail, Telefon, LinkedIn-URL
- Firma, Position, Standort
- Projekt-Referenz (Suchprojekt-Name)
- Quelle: "LinkedIn Recruiter via Recruiting Hub"

**Datenmodell**:
```python
class HunterCRMExport(TenantModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    project = models.ForeignKey(SearchProject, on_delete=models.CASCADE)
    export_method = models.CharField(choices=[("csv", "CSV"), ("api", "API")])
    hunter_candidate_id = models.CharField(max_length=100, blank=True)  # ID in Hunter CRM
    exported_at = models.DateTimeField(auto_now_add=True)
    exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(choices=[
        ("pending", "Pending"),
        ("exported", "Exported"),
        ("duplicate_in_hunter", "Duplicate in Hunter"),
        ("failed", "Failed"),
    ])
```

#### Schritt 5: Anschreiben (LinkedIn Recruiter Backend)

**Akteur**: Recruiter
**System**: Recruiting Hub (Vorlagen) + LinkedIn Recruiter (Versand)

```
Recruiting Hub                          LinkedIn Recruiter
┌─────────────────────┐                ┌─────────────────────┐
│ 1. Nachrichtenvorlage│                │                     │
│    generieren (LLM)  │                │                     │
│    oder manuell      │                │                     │
│                      │                │                     │
│ 2. Vorlage anzeigen  │                │                     │
│    [Kopieren]        │── copy/paste ─►│ 3. InMail senden   │
│                      │                │    oder Nachricht   │
│                      │                │                     │
│ 4. Stage →           │                │                     │
│    "Contacted"       │                │                     │
│    (manuell setzen)  │                │                     │
└─────────────────────┘                └─────────────────────┘
```

**Nachrichtenvorlagen** (Recruiting Hub verwaltet):

| Vorlage | Sprache | Trigger |
|---------|---------|---------|
| Erstansprache | DE/EN | Kandidat approved |
| Follow-up (7 Tage) | DE/EN | Keine Antwort nach 7 Tagen |
| Absage (höflich) | DE/EN | Kandidat rejected |
| Interview-Einladung | DE/EN | Positive Rückmeldung |

**Phase 2**: LLM personalisiert Vorlagen pro Kandidat (Name, Firma, Projekt-Match).

**Datenmodell**:
```python
class MessageTemplate(TenantModel):
    name = models.CharField(max_length=255)
    template_type = models.CharField(choices=[
        ("initial_outreach", "Erstansprache"),
        ("follow_up", "Follow-up"),
        ("rejection", "Absage"),
        ("interview_invite", "Interview-Einladung"),
    ])
    subject = models.CharField(max_length=255, blank=True)
    body_template = models.TextField()  # Jinja2/Django-Template-Syntax
    language = models.CharField(max_length=5, default="de")
    is_active = models.BooleanField(default=True)
```

#### Schritt 6: Rückmeldungen pflegen (LinkedIn ↔ Hunter CRM)

**Akteur**: Recruiter (manuell, Phase 1) / System (automatisch, Phase 3)
**Datenstrom**: LinkedIn → Recruiting Hub → Hunter CRM

```
LinkedIn Recruiter          Recruiting Hub              Hunter CRM
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│ Antwort      │── manual──►│ Status-Update│── sync ──►│ Kommunikation│
│ erhalten     │           │ Pipeline:    │           │ aktualisieren│
│              │           │ "Replied"    │           │              │
│ Interview    │── manual──►│ "Interview"  │── sync ──►│ Status       │
│ vereinbart   │           │              │           │ aktualisieren│
│              │           │              │           │              │
│ Absage       │── manual──►│ "Rejected"   │── sync ──►│ Absage       │
│ erhalten     │           │              │           │ vermerken    │
└──────────────┘           └──────────────┘           └──────────────┘
```

**Phase 1**: Recruiter setzt Status manuell im Recruiting Hub → CSV-Export-Update.
**Phase 2**: API-basierter Sync zu Hunter CRM bei Status-Änderung (Celery-Task).
**Phase 3**: Bidirektionaler Sync — Hunter CRM meldet zurück an Recruiting Hub.

**Datenmodell**:
```python
class CandidateActivity(TenantModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    project = models.ForeignKey(SearchProject, on_delete=models.CASCADE)
    activity_type = models.CharField(choices=[
        ("contacted", "Angeschrieben"),
        ("replied", "Geantwortet"),
        ("no_reply", "Keine Antwort"),
        ("interview_scheduled", "Interview vereinbart"),
        ("interview_done", "Interview durchgeführt"),
        ("offer_sent", "Angebot gesendet"),
        ("placed", "Platziert"),
        ("rejected_by_candidate", "Absage durch Kandidat"),
        ("rejected_by_client", "Absage durch Auftraggeber"),
    ])
    note = models.TextField(blank=True)
    source_system = models.CharField(choices=[
        ("linkedin", "LinkedIn"),
        ("hunter_crm", "Hunter CRM"),
        ("recruiting_hub", "Recruiting Hub"),
        ("manual", "Manuell"),
    ])
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recorded_at = models.DateTimeField(auto_now_add=True)
    synced_to_hunter = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
```

#### Schritt 7: Reporting (Recruiting Hub)

**System**: Recruiting Hub — Dashboard + Export

| KPI | Berechnung | Ziel |
|-----|-----------|------|
| **Pipeline-Füllstand** | Kandidaten pro Stage | Visualisierung |
| **Response-Rate** | Replied / Contacted | > 15% |
| **Interview-Rate** | Interview / Replied | > 30% |
| **Placement-Rate** | Placed / Interview | > 20% |
| **Time-to-Fill** | Projekt-Start → Placement | < 60 Tage |
| **Sourcing-Effizienz** | Placed / Sourced | Benchmark |

---

## 3. Implementation Plan

### Phase 1: Operativer Kern (sofort umsetzbar, kein API-Zugang nötig)

| # | Feature | Schritt | Aufwand |
|---|---------|---------|---------|
| 1.1 | Suchprojekt-CRUD mit Anforderungsprofil | 1 | ✅ Vorhanden |
| 1.2 | CSV-Import (LinkedIn-Format) mit Dublettencheck | 2 | 3-5 Tage |
| 1.3 | Pipeline-Board mit Approval-Queue | 3 | ✅ Grundstruktur da, Approval fehlt |
| 1.4 | CSV/Excel-Export im Hunter-CRM-Format | 4 | 2-3 Tage |
| 1.5 | Nachrichtenvorlagen (manuell, ohne LLM) | 5 | 2-3 Tage |
| 1.6 | Aktivitäts-Log (Rückmeldungen manuell tracken) | 6 | 2-3 Tage |
| 1.7 | Basis-KPIs auf Dashboard | 7 | 2-3 Tage |

**Gesamt Phase 1**: ~2-3 Wochen

### Phase 2: Intelligente Unterstützung (LLM via iil-aifw)

| # | Feature | Schritt | Abhängigkeit |
|---|---------|---------|-------------|
| 2.1 | Boolean Search String Generator (LLM) | 1 | iil-aifw |
| 2.2 | Kandidaten-Scoring (LLM vs. Anforderungsprofil) | 3 | iil-aifw |
| 2.3 | Personalisierte Nachrichtenvorlagen (LLM) | 5 | iil-aifw |
| 2.4 | Hunter CRM API-Integration (OP-10 klären) | 4, 6 | API-Zugang |

**Gesamt Phase 2**: ~3-4 Wochen

### Phase 3: Automatisierung (API-Zugang vorausgesetzt)

| # | Feature | Schritt | Abhängigkeit |
|---|---------|---------|-------------|
| 3.1 | Automatischer Export nach Hunter CRM (API) | 4 | Hunter CRM API |
| 3.2 | Bidirektionaler Status-Sync (Celery-Beat) | 6 | Hunter CRM API |
| 3.3 | Follow-up-Erinnerungen (Celery-Tasks) | 5 | Phase 1 |
| 3.4 | Erweiterte Funnel-Visualisierung | 7 | Phase 1 |
| 3.5 | Shortlist-PDF-Export für Auftraggeber | 7 | Phase 2 |

**Gesamt Phase 3**: ~2-3 Wochen

---

## 4. Risiken

| Risiko | W | I | Mitigation |
|--------|---|---|-----------|
| Hunter CRM hat keine offene API | Mittel | Hoch | Stufe 1 (CSV-Export) funktioniert immer, API-Klärung als OP-10 |
| LinkedIn ändert CSV-Export-Format | Niedrig | Mittel | CSV-Parser konfigurierbar, Mapping pro Tenant |
| Recruiter akzeptiert Tool nicht | Mittel | Hoch | UX-Test mit Sophia Paul nach Phase 1, Feedback-Loop |
| LLM-Scoring nicht aussagekräftig | Mittel | Mittel | Human-Override immer möglich, LLM-Score als Empfehlung |
| Doppelte Datenhaltung (Hub + Hunter) | Hoch | Mittel | Klare Master-Zuordnung: Hunter = Stamm, Hub = Pipeline |

---

## 5. Offene Punkte

| # | Punkt | Owner | Status |
|---|-------|-------|--------|
| OP-10 | Hunter CRM API-Verfügbarkeit klären | Achim | ⬜ Pre-Phase 2 |
| OP-11 | LinkedIn Recruiter CSV-Export-Format dokumentieren (Felder, Encoding) | Sophia | ⬜ Phase 1 |
| OP-12 | Hunter CRM Import-Format dokumentieren (Felder, Pflichtfelder) | Sophia | ⬜ Phase 1 |
| OP-13 | Approval-Berechtigungen: Wer darf freigeben? Nur Sophia oder mehrere? | Achim | ⬜ Phase 1 |
| OP-14 | Nachrichtenvorlagen: Standard-Set definieren (DE/EN) | Sophia | ⬜ Phase 1 |

---

## 6. Validation Criteria

### Phase 1 — Minimal Viable Workflow

- [ ] Suchprojekt anlegen mit Anforderungsprofil
- [ ] CSV-Import: LinkedIn-Export hochladen → Kandidaten in Pipeline (Stage: Sourced)
- [ ] Dublettencheck: Bereits bekannter Kandidat wird erkannt (E-Mail oder LinkedIn-URL)
- [ ] Pipeline-Board: Drag & Drop oder Button für Stage-Wechsel
- [ ] Approval-Queue: Reviewed → Approved nur mit Freigabe-Button + Logged User
- [ ] CSV-Export: Approved-Kandidaten im Hunter-CRM-Format downloadbar
- [ ] Aktivitäts-Log: Status-Änderung (Contacted, Replied, etc.) manuell erfassbar
- [ ] Basis-KPIs: Pipeline-Füllstand + Response-Rate auf Dashboard

### Phase 2 — Intelligenz

- [ ] Boolean Search String aus Anforderungsprofil generiert (LLM)
- [ ] Kandidaten-Score pro Projekt berechnet (LLM)
- [ ] Personalisierte Nachrichtenvorlage generiert (LLM)

### Phase 3 — Automatisierung

- [ ] Kandidat wird nach Approval automatisch nach Hunter CRM exportiert (API)
- [ ] Status-Änderung in Recruiting Hub wird nach Hunter CRM synchronisiert
- [ ] Follow-up-Erinnerung nach 7 Tagen ohne Antwort

---

## 7. Referenzen

- **ADR-148**: Recruiting Hub Architecture (Basis-Architektur, Apps, Deployment)
- **ADR-137**: Tenant-Lifecycle, RLS
- **ADR-093**: iil-aifw (LLM-Integration)
- **ADR-045**: Secrets & Environment Management
- **ADR-041**: Django Component Pattern (Service-Layer)
- **Hunter CRM**: https://www.hunter-software.de/
- **LinkedIn Recruiter**: https://business.linkedin.com/talent-solutions/recruiter

---

## 8. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-26 | Achim Dehnert | Initial draft — 7-Schritte-Workflow mit System-Zuordnung |
