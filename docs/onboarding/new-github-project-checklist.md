# New GitHub Project — Verifikations-Checkliste & Referenzen

> Ausgelagert aus `.windsurf/workflows/new-github-project.md` (2026-04-29)
> Wird am Ende des `/new-github-project` Workflows konsultiert

---

## Aktualisierte Verifikations-Checkliste

```
✅ GitHub-Infra Checkliste für [REPO] — komplett

Issue Templates:
  [ ] .github/ISSUE_TEMPLATE/bug_report.yml
  [ ] .github/ISSUE_TEMPLATE/feature_request.yml
  [ ] .github/ISSUE_TEMPLATE/task.yml
  [ ] .github/ISSUE_TEMPLATE/use_case.yml
  [ ] .github/PULL_REQUEST_TEMPLATE.md
  [ ] .github/scripts/bootstrap_labels.py (Labels gebootstrappt)

GitHub Actions:
  [ ] .github/workflows/issue-triage.yml
  [ ] Repo-Variable PROJECT_NUMBER gesetzt
  [ ] Repo-Variable PLATFORM_PROJECT_NUMBER gesetzt
  [ ] Repo-Secret PROJECT_PAT gesetzt

GitHub Projects:
  [ ] Repo-eigenes Project angelegt (Board: Backlog/In Progress/In Review/Done)
  [ ] 3 Automationen aktiv (auto-add, item-closed, pr-merged)
  [ ] Custom Fields: Priority + Type
  [ ] Platform-Überblick-Project verknüpft (achimdehnert/platform)

Dokumentation:
  [ ] docs/CORE_CONTEXT.md
  [ ] docs/AGENT_HANDOVER.md
  [ ] docs/adr/ (Template + erster ADR + README)
  [ ] docs/use-cases/ (Template + README)
  [ ] docs/PERFECT_PROMPT.md
  [ ] docs/konzept/05_project_governance.md
```

---

## Referenz: 137-hub als Musterbeispiel

Das Repo `achimdehnert/137-hub` hat diese Infrastruktur vollständig implementiert:
- `.github/ISSUE_TEMPLATE/` — 4 YAML-Formulare
- `docs/CORE_CONTEXT.md` + `docs/AGENT_HANDOVER.md`
- `docs/adr/` + `docs/use-cases/` mit Templates und Index
- `docs/PERFECT_PROMPT.md` mit 5 Varianten
- `docs/konzept/05_project_governance.md`
