# 🤖 ADR Review Action - BF Agent Platform

## Komplettes Paket für automatische ADR-Architektur-Reviews

---

## 📦 Inhalt dieses Pakets

```
adr-review-complete-package/
├── .github/
│   └── workflows/
│       └── adr-review.yml     ← PFLICHT: Diese Datei ins Repo kopieren
├── README.md                   ← Diese Datei (Anleitung)
├── FEATURES.md                 ← Dokumentation der Features
└── EXAMPLE-OUTPUT.md           ← Beispiel wie Reviews aussehen
```

---

## 🚀 Setup in 2 Minuten

### Schritt 1: API Key als GitHub Secret anlegen

**Option A: Via GitHub CLI**
```bash
gh secret set ANTHROPIC_API_KEY --repo achimdehnert/platform
# Dann Key eingeben (beginnt mit sk-ant-...)
```

**Option B: Via Web UI**
1. Gehe zu: https://github.com/achimdehnert/platform/settings/secrets/actions
2. Klick: **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: Dein Anthropic API Key
5. Klick: **Add secret**

### Schritt 2: Workflow-Datei kopieren

```bash
# Im platform Repository
cp -r .github/ /pfad/zu/achimdehnert/platform/

# Oder manuell:
# Kopiere .github/workflows/adr-review.yml in dein Repo
```

### Schritt 3: Commit & Push

```bash
cd /pfad/zu/achimdehnert/platform
git add .github/workflows/adr-review.yml
git commit -m "feat: Add automatic ADR architecture review with auto-fixes"
git push
```

### Schritt 4: Fertig! 🎉

Ab jetzt wird bei jedem PR mit ADR-Dateien automatisch eine Review durchgeführt.

---

## ✅ Was passiert automatisch?

Bei jedem PR der diese Dateien ändert:
- `docs/adr/**`
- `adr/**`
- `**/ADR-*.md`
- `concepts/**/*.md`

Wird automatisch:

1. **AI-Review** durchgeführt (Scoring, Gaps, Platform-Prinzipien)
2. **Fix-Vorschläge** generiert (copy-paste-fertig)
3. **Verwandte ADRs** identifiziert
4. **Label** gesetzt (passed/concerns/failed)
5. **PR-Kommentar** gepostet

---

## 📊 Beispiel-Output

```
## 🤖 Erweiterte ADR-Architektur-Review

### ✅ `docs/adr/ADR-009-deployment.md` — Score: 8/10

#### Scoring Matrix
| Kategorie | Score |
|-----------|-------|
| Problemdefinition | 9/10 |
| Platform-Prinzipien | 8/10 |
| Rollback-Strategie | 5/10 |
| **Gesamt** | **8/10** |

#### 🔧 Fix-Vorschläge
- Fix #1: Related ADRs verlinken
- Fix #2: Rollback-Strategie ergänzen

#### 🔗 Verwandte ADRs
- ADR-008: Infrastructure Services
```

---

## 🏷️ Automatische Labels

| Label | Bedeutung |
|-------|-----------|
| `adr-review-passed` 🟢 | Score ≥7 - Ready to merge |
| `adr-review-concerns` 🟡 | Score 5-6 - Verbesserungen nötig |
| `adr-review-failed` 🔴 | Score <5 - Überarbeitung nötig |

---

## ⚙️ Optionale Konfiguration

### Slack Notifications aktivieren

```bash
# Secret anlegen
gh secret set SLACK_WEBHOOK_URL --repo achimdehnert/platform

# Variable setzen
gh variable set SLACK_ENABLED --body "true" --repo achimdehnert/platform
```

### Manueller Trigger

```bash
# Für bestehende PRs
gh workflow run "📋 ADR Architecture Review (Extended)" \
  --repo achimdehnert/platform \
  -f pr_number=123
```

---

## 💰 Kosten

| Reviews/Monat | Kosten |
|---------------|--------|
| 50 | ~$2 |
| 100 | ~$4 |
| 200 | ~$8 |

---

## 🔧 Troubleshooting

### "API Key invalid"
→ Prüfe Secret `ANTHROPIC_API_KEY` (muss mit `sk-ant-` beginnen)

### "No ADR files found"
→ Dateiname muss `ADR-*.md` Pattern matchen

### Labels werden nicht gesetzt
→ Labels werden beim ersten Run automatisch erstellt

---

## 📚 Weitere Dokumentation

- `FEATURES.md` - Alle Features im Detail
- `EXAMPLE-OUTPUT.md` - Vollständiges Beispiel einer Review

---

## 🎯 Quick Reference

```bash
# Setup (einmalig)
gh secret set ANTHROPIC_API_KEY --repo achimdehnert/platform

# Workflow kopieren
cp .github/workflows/adr-review.yml /path/to/platform/.github/workflows/

# Testen
gh workflow run "📋 ADR Architecture Review (Extended)" -f pr_number=123
```
