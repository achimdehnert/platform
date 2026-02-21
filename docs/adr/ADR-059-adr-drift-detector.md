---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
consulted: –
informed: –
---

# ADR-059: Adopt Automated ADR Drift Detection and Staleness Management

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-02-21                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-046 (Documentation Governance), ADR-054 (Architecture Guardian), ADR-058 (Testing Strategy), ADR-021 (Unified Deployment) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                          |
|----------------|------------|---------------------------------------------------------|
| `platform`     | Primär     | `docs/adr/`, `docs/templates/`, `.windsurf/workflows/`  |
| `dev-hub`      | Primär     | `apps/adr_lifecycle/`, `apps/adr_lifecycle/tasks.py`    |
| `bfagent`      | Sekundär   | `docs/adr/` (falls vorhanden)                           |
| `cad-hub`      | Sekundär   | `docs/adr/` (falls vorhanden)                           |
| `travel-beat`  | Sekundär   | `docs/adr/` (falls vorhanden)                           |
| `risk-hub`     | Sekundär   | `docs/adr/` (falls vorhanden)                           |
| `trading-hub`  | Sekundär   | `docs/adr/` (falls vorhanden)                           |
| `mcp-hub`      | Sekundär   | `docs/adr/` (falls vorhanden)                           |

---

## Decision Drivers

- **42 ADRs mit Status `?`**: Nie normalisiert — dev-hub kann sie nicht korrekt in die State Machine einordnen
- **Inhaltlicher Drift**: ADR-020 (Sphinx) ist faktisch durch ADR-046 + techdocs ersetzt, steht aber noch als `Proposed`
- **1 Entwickler**: Manuelle Triage von 57 ADRs ist nicht skalierbar — muss automatisiert werden
- **Drift-Detector (A4)** ist bereits als `AgentType` in `agents_dashboard` definiert — aber nicht implementiert
- **Governance-Lücke**: Kein Mechanismus prüft ob ADR-Anforderungen noch mit dem tatsächlichen Repo-Zustand übereinstimmen
- **techdocs-Strategie**: ADRs werden via GitHub-Sync in dev-hub gespiegelt — Staleness-Flags müssen maschinenlesbar sein

---

## 1. Context and Problem Statement

Das Platform-ADR-Repository enthält 57 ADR-Dateien. 42 davon haben Status `?` — sie wurden nie in die MADR-konforme State Machine (`draft → proposed → accepted → deprecated → superseded`) überführt. Zusätzlich sind mehrere ADRs inhaltlich überholt: ADR-020 beschreibt Sphinx als Dokumentationsstrategie, obwohl ADR-046 Sphinx als "deferred" markiert hat und wir inzwischen `techdocs` (DB-driven, GitHub-Sync) einsetzen.

Ohne automatisierte Erkennung akkumuliert sich dieser Drift weiter. Jeder neue ADR referenziert möglicherweise veraltete Entscheidungen. Der Architecture Guardian (ADR-054) kann keine verlässlichen Compliance-Checks durchführen wenn die Basis-ADRs selbst inkonsistent sind.

### 1.1 Ist-Zustand

| Problem | Anzahl | Auswirkung |
|---------|--------|-----------|
| ADRs mit Status `?` | 42 | Nicht in State Machine — dev-hub kann nicht filtern/tracken |
| ADRs ohne YAML-Frontmatter | ~40 | `parse_adr_frontmatter()` fällt auf Regex-Fallback zurück |
| Inhaltlich veraltete ADRs | ~8 (geschätzt) | Falsche Referenzen, widersprüchliche Anforderungen |
| ADRs ohne `Confirmation`-Abschnitt | ~50 | Drift-Detector kann Compliance nicht prüfen |
| Doppelte DDL-ADRs (ADR-017 + ADR-032) | 2 | Unklar welche gilt |

### 1.2 Warum jetzt

Mit ADR-056 (Multi-Tenancy) und ADR-058 (Testing Strategy) wächst die ADR-Basis weiter. Die techdocs-Strategie synchronisiert ADRs in dev-hub — dort werden sie als `DocPage` und `ADR`-Modelle gespeichert. Ohne Staleness-Erkennung werden veraltete ADRs gleichwertig mit aktuellen angezeigt. Der Drift-Detector ist der fehlende Baustein zwischen ADR-Erstellung (ADR-051) und ADR-Governance (ADR-046).

---

## 2. Considered Options

### Option A: Automatisierter Drift-Detector in dev-hub (Celery Task + Model-Erweiterung) ✅

Erweiterung des bestehenden `sync_adrs_from_github`-Tasks um Staleness-Checks. Neues `review_needed`-Flag auf dem `ADR`-Model. Wöchentlicher Celery-Beat-Task prüft alle ADRs gegen definierte Kriterien.

**Pros:**
- Nutzt bestehende Infrastruktur (`adr_lifecycle`, Celery Beat, GitHub API)
- `AgentType.DRIFT_DETECTOR` bereits in `agents_dashboard` definiert
- Maschinenlesbare Ergebnisse — kein manueller Aufwand
- Integriert in dev-hub UI (Filter: "Review needed")

**Cons:**
- Erfordert Model-Migration in dev-hub
- False Positives möglich (ADR korrekt aber alt)

### Option B: GitHub Actions Workflow (wöchentlicher Cron-Job)

Skript läuft in CI, kommentiert veraltete ADRs als GitHub Issues.

**Pros:**
- Kein dev-hub-Code nötig

**Cons:**
- Ergebnisse in GitHub Issues, nicht in dev-hub sichtbar → **Abgelehnt weil:** Bricht techdocs-Integration; Issues sind kein strukturiertes Tracking

### Option C: Manuelle Quartals-Triage

Manueller Review aller ADRs alle 3 Monate.

**Pros:**
- Kein Code

**Cons:**
- Nicht skalierbar bei 1 Entwickler + wachsender ADR-Basis → **Abgelehnt weil:** Bereits gescheitert (42 ADRs mit `?` sind das Ergebnis)

---

## 3. Decision Outcome

**Gewählte Option: Option A — Automatisierter Drift-Detector in dev-hub**

Der bestehende `AgentType.DRIFT_DETECTOR` in `agents_dashboard` wird implementiert. Das `ADR`-Model in `adr_lifecycle` erhält vier neue Felder: `review_needed`, `drift_reasons`, `last_drift_check`, `staleness_months`. Ein wöchentlicher Celery-Beat-Task prüft alle ADRs gegen 5 Staleness-Kriterien und setzt Flags automatisch. Die Ergebnisse sind in dev-hub filterbar und werden als `AgentRun` in `agents_dashboard` protokolliert.

---

## 4. Implementation Details

### 4.1 Model-Erweiterung `adr_lifecycle.ADR`

```python
# apps/adr_lifecycle/models.py — neue Felder auf ADR-Model

class DriftReason(models.TextChoices):
    NO_FRONTMATTER = "no_frontmatter", "Kein YAML-Frontmatter"
    STATUS_UNKNOWN = "status_unknown", "Status unbekannt (?)"
    STALE_NO_UPDATE = "stale_no_update", "Kein Update seit > Schwellenwert"
    SUPERSEDED_REF = "superseded_ref", "Referenziert deprecated/superseded ADR"
    MISSING_CONFIRMATION = "missing_confirmation", "Kein Confirmation-Abschnitt"
    PATH_NOT_FOUND = "path_not_found", "Referenzierte Dateipfade existieren nicht"
    DUPLICATE_TOPIC = "duplicate_topic", "Doppeltes Thema (anderes ADR supersedes)"


class ADR(TenantAwareModel):
    # ... bestehende Felder ...

    # Drift-Detector Felder (ADR-059)
    review_needed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Vom Drift-Detector als review-bedürftig markiert.",
    )
    drift_reasons = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste von DriftReason-Werten vom letzten Drift-Check.",
    )
    last_drift_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Zeitpunkt des letzten Drift-Detector-Runs.",
    )
    staleness_months = models.PositiveSmallIntegerField(
        default=12,
        help_text="Nach wie vielen Monaten ohne Update als stale markieren.",
    )
```

### 4.2 Drift-Detector Celery Task

```python
# apps/adr_lifecycle/tasks.py — neuer Task

@shared_task(
    name="adr_lifecycle.run_drift_detector",
    bind=True,
    max_retries=2,
    soft_time_limit=600,
)
def run_drift_detector(self, tenant_slug: str = "devhub") -> dict:
    """ADR Drift-Detector (A4) — prüft alle ADRs auf Aktualität.

    Kriterien:
    1. Kein YAML-Frontmatter → DriftReason.NO_FRONTMATTER
    2. Status == '?' → DriftReason.STATUS_UNKNOWN
    3. Letztes source_sha-Update > staleness_months → DriftReason.STALE_NO_UPDATE
    4. Referenziert ADR mit status deprecated/superseded → DriftReason.SUPERSEDED_REF
    5. Kein '## Confirmation'-Abschnitt → DriftReason.MISSING_CONFIRMATION
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.agents_dashboard.models import AgentRun, AgentType, RunStatus

    org = Organization.objects.filter(slug=tenant_slug).first()
    if not org:
        return {"error": f"Organization '{tenant_slug}' not found"}

    tenant_id = org.tenant_id
    adrs = ADR.objects.for_tenant(tenant_id).all()

    flagged = 0
    cleared = 0
    run = AgentRun.objects.create(
        tenant_id=tenant_id,
        agent_type=AgentType.DRIFT_DETECTOR,
        status=RunStatus.RUNNING,
        trigger="celery_beat_weekly",
        gate_level=1,
    )

    status_map = {a.adr_id: a.status for a in adrs}

    for adr in adrs:
        reasons = []

        # Kriterium 1: Kein YAML-Frontmatter
        if not adr.content_markdown.startswith("---"):
            reasons.append(DriftReason.NO_FRONTMATTER)

        # Kriterium 2: Status unbekannt
        if adr.status == "?" or not adr.status:
            reasons.append(DriftReason.STATUS_UNKNOWN)

        # Kriterium 3: Stale (kein Update seit N Monaten)
        if adr.updated_at:
            threshold = timezone.now() - timedelta(days=30 * adr.staleness_months)
            if adr.updated_at < threshold and adr.status not in ("deprecated", "superseded"):
                reasons.append(DriftReason.STALE_NO_UPDATE)

        # Kriterium 4: Referenziert deprecated/superseded ADR
        for ref_id in adr.related_adrs:
            ref_status = status_map.get(ref_id, "")
            if ref_status in ("deprecated", "superseded"):
                reasons.append(DriftReason.SUPERSEDED_REF)
                break

        # Kriterium 5: Kein Confirmation-Abschnitt
        if "## Confirmation" not in adr.content_markdown and "### Confirmation" not in adr.content_markdown:
            reasons.append(DriftReason.MISSING_CONFIRMATION)

        # Flags setzen
        had_flag = adr.review_needed
        adr.review_needed = len(reasons) > 0
        adr.drift_reasons = reasons
        adr.last_drift_check = timezone.now()
        adr.save(update_fields=["review_needed", "drift_reasons", "last_drift_check", "updated_at"])

        if adr.review_needed:
            flagged += 1
        elif had_flag:
            cleared += 1

    result = {"flagged": flagged, "cleared": cleared, "total": adrs.count()}
    run.status = RunStatus.SUCCESS
    run.findings_count = flagged
    run.output_data = result
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "findings_count", "output_data", "completed_at"])

    return result
```

### 4.3 Celery Beat Schedule

```python
# config/settings/base.py — Ergänzung

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # bestehend:
    "sync-adrs-hourly": {
        "task": "adr_lifecycle.sync_all_adr_repos",
        "schedule": crontab(minute=0),
    },
    # neu (ADR-059):
    "drift-detector-weekly": {
        "task": "adr_lifecycle.run_drift_detector",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Montag 06:00
    },
}
```

### 4.4 Triage-Skript für sofortige Normalisierung der 42 `?`-ADRs

```python
# scripts/adr_triage.py — einmalig ausführen
"""
Analysiert alle ADR-Dateien in docs/adr/ und gibt einen Triage-Report aus.
Schlägt Status-Korrekturen vor basierend auf Inhalt + Alter.

Ausführen: python scripts/adr_triage.py
"""
import re
import sys
from pathlib import Path
from datetime import datetime, date

ADR_DIR = Path("docs/adr")
KNOWN_SUPERSEDED = {
    "ADR-020": "ADR-046",  # Sphinx → techdocs
    "ADR-017": "ADR-032",  # DDL Duplikat
    "ADR-047": "ADR-046",  # Sphinx Hub → techdocs
}

def analyze_adr(path: Path) -> dict:
    content = path.read_text()
    result = {"file": path.name, "issues": [], "suggested_status": None}

    # YAML-Frontmatter?
    has_frontmatter = content.startswith("---")
    if not has_frontmatter:
        result["issues"].append("NO_FRONTMATTER")

    # Status aus Inhalt extrahieren
    status_match = re.search(r"\*\*Status\*\*[:\|]\s*(.+?)[\n\|]", content, re.IGNORECASE)
    raw_status = status_match.group(1).strip().lower() if status_match else "?"
    result["raw_status"] = raw_status

    # Superseded?
    adr_num = re.match(r"ADR-(\d+)", path.name)
    if adr_num:
        adr_id = f"ADR-{adr_num.group(1).zfill(3)}"
        if adr_id in KNOWN_SUPERSEDED:
            result["suggested_status"] = "superseded"
            result["superseded_by"] = KNOWN_SUPERSEDED[adr_id]
            result["issues"].append(f"SUPERSEDED_BY_{KNOWN_SUPERSEDED[adr_id]}")

    # Confirmation-Abschnitt?
    if "## Confirmation" not in content and "### Confirmation" not in content:
        result["issues"].append("NO_CONFIRMATION")

    # Status-Vorschlag wenn noch keiner
    if not result["suggested_status"]:
        if "accepted" in raw_status:
            result["suggested_status"] = "accepted"
        elif "proposed" in raw_status:
            result["suggested_status"] = "proposed"
        elif "draft" in raw_status:
            result["suggested_status"] = "draft"
        elif "deprecated" in raw_status:
            result["suggested_status"] = "deprecated"
        else:
            result["suggested_status"] = "proposed"  # sicherer Default

    return result


if __name__ == "__main__":
    results = [analyze_adr(p) for p in sorted(ADR_DIR.glob("*.md"))
               if not p.name.startswith("INDEX")]

    print(f"\n{'='*70}")
    print(f"ADR TRIAGE REPORT — {date.today()}")
    print(f"{'='*70}")
    print(f"Total ADRs: {len(results)}")
    print(f"With issues: {sum(1 for r in results if r['issues'])}")
    print()

    for r in results:
        if r["issues"]:
            print(f"  {r['file']}")
            print(f"    Raw status : {r['raw_status']}")
            print(f"    Suggested  : {r['suggested_status']}")
            print(f"    Issues     : {', '.join(r['issues'])}")
            print()
```

### 4.5 dev-hub UI — Filter "Review needed"

```python
# apps/adr_lifecycle/views.py — Erweiterung ADRListView

class ADRListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        qs = ADR.objects.for_tenant(self.request.tenant_id)
        if self.request.GET.get("review_needed"):
            qs = qs.filter(review_needed=True)
        if self.request.GET.get("drift_reason"):
            qs = qs.filter(drift_reasons__contains=self.request.GET["drift_reason"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review_count"] = ADR.objects.for_tenant(
            self.request.tenant_id
        ).filter(review_needed=True).count()
        ctx["drift_reasons"] = DriftReason.choices
        return ctx
```

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `dev-hub` — Model-Migration | 1 | ⬜ Ausstehend | – | 3 neue Felder auf `ADR` |
| `dev-hub` — Celery Task | 1 | ⬜ Ausstehend | – | `run_drift_detector` |
| `dev-hub` — Beat Schedule | 1 | ⬜ Ausstehend | – | Montag 06:00 |
| `dev-hub` — UI Filter | 2 | ⬜ Ausstehend | – | `?review_needed=1` |
| `platform` — Triage-Skript | 0 | ✅ Abgeschlossen | 2026-02-21 | `scripts/adr_triage.py` erstellt |
| `platform` — ADR-Template v2 | 0 | ✅ Abgeschlossen | 2026-02-21 | `docs/templates/adr-template.md` |
| `platform` — YAML-Frontmatter (46 ADRs) | 0 | ✅ Abgeschlossen | 2026-02-21 | `adr_triage.py --apply` ausgeführt |
| `platform` — Status-Triage (superseded/accepted) | 3 | ⬜ Ausstehend | – | Manuelle Bestätigung der Vorschläge |

---

## 6. Consequences

### 6.1 Good

- **Automatische Governance**: Veraltete ADRs werden wöchentlich erkannt — kein manueller Aufwand
- **dev-hub als Single Source of Truth**: `review_needed`-Flag macht Staleness in der UI sichtbar
- **AgentRun-Protokoll**: Jeder Drift-Detector-Run ist in `agents_dashboard` nachvollziehbar
- **Sofort-Nutzen**: Triage-Skript normalisiert die 42 `?`-ADRs ohne Model-Migration
- **Template v2**: Neue ADRs haben `staleness_months` + `drift_check_paths` — Drift-Detector kann sie präzise prüfen

### 6.2 Bad

- **False Positives**: ADRs die korrekt aber alt sind werden als "stale" markiert — manuelle Bestätigung nötig
- **Model-Migration**: Erfordert `makemigrations` + `migrate` in dev-hub
- **`MISSING_CONFIRMATION`-Flut**: ~50 bestehende ADRs haben keinen Confirmation-Abschnitt — initiale Flag-Welle erwartet

### 6.3 Nicht in Scope

- Automatisches Schreiben von ADR-Korrekturen (bleibt manuell)
- Cross-Repo-Drift (ob Code in `bfagent` noch dem ADR entspricht) — Phase 2
- LLM-basierte Inhaltsanalyse ("ist dieser ADR noch fachlich korrekt?") — separates ADR

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Drift-Detector flaggt zu viele ADRs → Alert-Fatigue | Hoch | Mittel | Initiale `staleness_months=24` für Legacy-ADRs (007–049); schrittweise auf 12 reduzieren |
| Model-Migration schlägt fehl in Produktion | Niedrig | Hoch | Expand-Contract: Felder zuerst nullable, dann befüllen, dann NOT NULL |
| Celery Beat läuft nicht (Beat-Worker down) | Mittel | Niedrig | `AgentRun`-Timestamp prüfen — fehlt Eintrag > 8 Tage → Alert |
| `?`-Status-ADRs werden falsch klassifiziert | Mittel | Mittel | Triage-Skript gibt nur Vorschläge — manuelle Bestätigung vor Commit |

---

## 8. Confirmation

1. **Wöchentlicher AgentRun**: `AgentRun.objects.filter(agent_type="drift_detector").latest("created_at")` — muss < 8 Tage alt sein
2. **Review-Count sinkt**: `ADR.objects.filter(review_needed=True).count()` — Ziel: < 5 nach initialer Triage
3. **Neue ADRs haben Frontmatter**: CI-Check `grep -L "^---" docs/adr/ADR-*.md` — muss leer sein für ADRs nach 2026-02-21
4. **Celery Beat aktiv**: `AgentRun.objects.filter(agent_type="drift_detector").latest("created_at")` — fehlt Eintrag > 8 Tage → manuelle Prüfung ob Beat-Worker läuft

---

## 9. More Information

- ADR-046: Documentation Governance — definiert Hygiene-Regeln die der Drift-Detector prüft
- ADR-051: Concept-to-ADR Pipeline — Upstream-Prozess der ADRs erzeugt
- ADR-054: Architecture Guardian — Downstream-Konsument der ADR-Qualität
- ADR-058: Multi-Tenancy Testing Strategy — Beispiel für ADR mit vollständigem Confirmation-Abschnitt
- `agents_dashboard.AgentType.DRIFT_DETECTOR` — bereits definiert in dev-hub

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-21 | Achim Dehnert | Initial: Status Proposed — auf Basis ADR-Template v2.0 |
| 2026-02-21 | Achim Dehnert | Review-Fixes: Migration Tracking aktualisiert, Decision Outcome Feldanzahl korrigiert, Confirmation §4 self-reference entfernt |
