# ADR Review Extended Features

## 🆕 Neue Features

### 1. Automatische Fix-Vorschläge 🔧

Die Action generiert **konkrete, copy-paste-fertige Fixes** für identifizierte Probleme.

#### Beispiel-Output:

```markdown
## 🔧 Automatische Fix-Vorschläge

### Fix #1

**Begründung:** Fehlende Rollback-Strategie - kritisch für Production Safety

**Hinzufügen:**
```markdown
## 5.3 Rollback-Strategie

### Automatischer Rollback
Bei fehlgeschlagenem Health Check:
1. Container auf vorherige Version zurücksetzen
2. Notification an Slack senden
3. Incident-Log erstellen

### Manueller Rollback
```bash
# Rollback auf vorherige Version
ssh deploy@server "cd /opt/app && ./rollback.sh"
```

### DB-Migration Rollback
- Expand-Phase: Kein Rollback nötig (backward compatible)
- Contract-Phase: Nur nach Verification ausführen
```

---

### Fix #2

**Begründung:** Related ADR fehlt - ADR-008 behandelt verwandte Infrastructure

**Ersetze:**
```markdown
| **Related** | — |
```

**Mit:**
```markdown
| **Related** | ADR-008 (Infrastructure Services), ADR-007 (Database Strategy) |
```
```

---

### 2. Verwandte ADRs Erkennung 🔗

Die Action analysiert alle existierenden ADRs und identifiziert:

- **Thematisch verwandte ADRs** → Sollten verlinkt werden
- **Potenzielle Konflikte** → Widersprüche zu bestehenden Entscheidungen
- **Supersedes-Kandidaten** → Ersetzt dieses ADR ein bestehendes?

#### Beispiel-Output:

```markdown
## 🔗 Verwandte ADRs

Diese ADRs sollten im `Related`-Feld verlinkt werden:

- **ADR-008**: Infrastructure Services (Status: Accepted)
  → Behandelt die gleiche Infrastruktur-Ebene
  
- **ADR-005**: Database Migration Strategy (Status: Accepted)
  → Definiert das Expand/Contract Pattern das hier referenziert wird
  
- **ADR-003**: CI/CD Pipeline (Status: Deprecated)
  → Wird durch dieses ADR möglicherweise ersetzt (Supersedes?)
```

---

### 3. Platform-Prinzipien Check ✅

Explizite Prüfung gegen die BF Agent Platform Standards:

```markdown
#### Platform-Prinzipien Check

- [x] **Database-First eingehalten?**
  Schema-Änderungen sind vor Code-Änderungen geplant ✓
  
- [ ] **Zero Breaking Changes berücksichtigt?**
  ⚠️ Migration in Phase 2 könnte bestehende APIs brechen
  → Fix #3 vorgeschlagen
  
- [x] **Spec vs. Derived korrekt?**
  Deployment-State wird korrekt als Derived behandelt ✓
  
- [x] **Fail Loud implementiert?**
  Health Checks mit expliziten Fehlermeldungen ✓
```

---

## 📊 Vergleich: Standard vs. Extended

| Feature | Standard | Extended |
|---------|:--------:|:--------:|
| Scoring Matrix | ✅ | ✅ |
| Executive Assessment | ✅ | ✅ |
| Kritische Gaps | ✅ | ✅ |
| Platform-Prinzipien Check | ✅ | ✅ |
| **Auto-Fix Vorschläge** | ❌ | ✅ |
| **Related ADRs Detection** | ❌ | ✅ |
| **Conflict Detection** | ❌ | ✅ |
| **Supersedes Check** | ❌ | ✅ |
| Kosten pro Review | ~$0.02 | ~$0.04 |

---

## 🚀 Setup

### Option A: Extended Action verwenden

```bash
# Ersetze die Standard-Action
cp adr-review-extended.yml .github/workflows/adr-review.yml
```

### Option B: Beide Actions parallel

```yaml
# .github/workflows/adr-review.yml (schnelle Review)
# .github/workflows/adr-review-extended.yml (detaillierte Review)
```

### Manueller Trigger mit Optionen

```bash
# Mit Fix-Vorschlägen
gh workflow run "📋 ADR Architecture Review (Extended)" \
  -f pr_number=123 \
  -f include_fixes=true

# Ohne Fix-Vorschläge (schneller)
gh workflow run "📋 ADR Architecture Review (Extended)" \
  -f pr_number=123 \
  -f include_fixes=false
```

---

## 📁 Workflow-Dateien

| Datei | Beschreibung | Features |
|-------|--------------|----------|
| `adr-review.yml` | Standard Review | Scoring, Gaps, Platform Check |
| `adr-review-extended.yml` | **Extended Review** | + Auto-Fixes, Related ADRs, Conflicts |

---

## 💡 Best Practices

### Fix-Vorschläge anwenden

1. **Review** die vorgeschlagenen Fixes
2. **Copy-Paste** die relevanten Änderungen
3. **Commit** mit Referenz: `fix: Apply ADR review suggestions`

### Related ADRs pflegen

Nach der Review:
1. Öffne das ADR
2. Füge die empfohlenen ADRs zum `Related`-Feld hinzu
3. Prüfe ob bidirektionale Links sinnvoll sind

### Konflikte lösen

Wenn Konflikte erkannt werden:
1. Prüfe das referenzierte ADR
2. Entscheide: **Supersede** oder **Anpassen**
3. Dokumentiere die Entscheidung

---

## 🔧 Konfiguration

### Fix-Vorschläge deaktivieren

```yaml
# In workflow dispatch
inputs:
  include_fixes:
    default: false  # Ändere auf false
```

### Mehr/Weniger ADR-Kontext

Passe `EXISTING_ADRS_CONTEXT` in der Action an um mehr oder weniger Kontext zu laden.

### Custom Platform-Prinzipien

Erweitere `PLATFORM_CONTEXT` um projekt-spezifische Prinzipien:

```python
PLATFORM_CONTEXT = """
...
5. **Custom Principle:** Beschreibung
...
"""
```
