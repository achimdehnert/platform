# Onboard Repo — Verifikations-Checkliste & Referenzen

> Ausgelagert aus `.windsurf/workflows/onboard-repo.md` (2026-04-29)
> Wird am Ende des `/onboard-repo` Workflows konsultiert (Step 7)

---

## Step 7: Verifikation

### Checkliste (ALLE Punkte müssen grün sein)

```text
✅ Verifikation für [REPO]

Repo-Struktur:
  [ ] docker/app/Dockerfile existiert (KEIN HEALTHCHECK drin — gehört in Compose!)
  [ ] docker/app/entrypoint.sh existiert (chmod +x, mit beat-Case + chown /celerybeat)
  [ ] docker-compose.prod.yml existiert
  [ ] .github/workflows/ci-cd.yml existiert (coverage_threshold: 80)
  [ ] .env.example existiert
  [ ] /livez/ Health-Endpoint existiert (csrf_exempt, require_GET)
  [ ] pyproject.toml mit [tool.pytest.ini_options]
  [ ] README.md mit Quickstart
  [ ] apps/<app>/components/ Verzeichnis existiert (ADR-041)
  [ ] templates/<app>/components/ Verzeichnis existiert

Testing (ADR-058):
  [ ] requirements-test.txt mit platform-context[testing]>=0.3.1
  [ ] tests/__init__.py existiert
  [ ] tests/conftest.py importiert platform_context.testing.fixtures
  [ ] tests/factories.py mit UserFactory
  [ ] config/settings/test.py mit WHITENOISE_MANIFEST_STRICT=False
  [ ] pytest tests/ -v läuft lokal ohne Fehler

Platform-Integration:
  [ ] platform/registry/repos.yaml Eintrag hinzugefügt
  [ ] platform/infra/ports.yaml Port registriert + port_audit.py grün
  [ ] devhub.iil.pet/repos zeigt neues Repo (nach GitHub Action)
  [ ] deploy.md Tabelle aktualisiert
  [ ] backup.md Tabelle aktualisiert
  [ ] Outline Repo-Steckbrief erstellt (Step 6.5, ADR-145)

Docker (KRITISCH):
  [ ] Kein HEALTHCHECK im Dockerfile (gehört pro-Service in Compose!)
  [ ] entrypoint.sh: beat-Case mit chown /celerybeat vor exec
  [ ] Worker/Beat Healthcheck: pidof python3.12 (NICHT curl, NICHT celery inspect ping)
  [ ] Beat-Volume in docker-compose.prod.yml definiert (<REPO_UNDERSCORE>_beatdata)

REFLEX (ADR-165):
  [ ] reflex.yaml existiert im Repo-Root
  [ ] .reflex/baseline.json existiert (Initial-Baseline)
  [ ] iil-reflex>=0.5.0 in requirements-dev.txt oder requirements-test.txt
  [ ] .reflex/ NICHT in .gitignore
  [ ] `reflex review all <repo> --fail-on block` → Exit 0
  [ ] CI: REFLEX Review Job vorhanden (Tier 1) ODER geplant (Tier 2)

Platform-Packages (falls verwendet):
  [ ] vendor/<PACKAGE>/ existiert mit pyproject.toml
  [ ] requirements.txt: `vendor/<PACKAGE>` (KEIN git+https!)
  [ ] Dockerfile: `COPY vendor /app/vendor` VOR `pip install`
  [ ] .gitignore: vendor/ NICHT ausgeschlossen
  [ ] .dockerignore: vendor/ NICHT ausgeschlossen
  [ ] INSTALLED_APPS: Package-App hinzugefügt

Server:
  [ ] /opt/<REPO>/ Verzeichnis existiert
  [ ] .env.prod mit echten Werten
  [ ] docker-compose.prod.yml kopiert
  [ ] Container starten und sind healthy
  [ ] Falls Beat-Volume Permission-Fehler: docker run --rm -v <vol>:/dir busybox chown -R 1000:1000 /dir

Netzwerk:
  [ ] DNS A-Record zeigt auf 88.198.191.108
  [ ] Nginx Config deployed
  [ ] SSL-Zertifikat aktiv
  [ ] https://<DOMAIN>/livez/ gibt "ok"

CI/CD:
  [ ] GitHub Secrets gesetzt (DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY)
  [ ] Push auf main triggert CI (grün)
  [ ] CD deployt auf Server
  [ ] Kein core.sshCommand in .git/config (ADR-060)

Platform-Integration (Step 6.8):
  [ ] Repo in repo-registry.yaml eingetragen
  [ ] .windsurf/workflows/ mit Symlinks vorhanden (≥10 Workflows)
  [ ] .windsurf/rules/project-facts.md vorhanden
  [ ] Nächster session-start synct Workflows automatisch

Branch Protection (Step 6.9 — ADR-174):
  [ ] qm-gate als required status check in main Branch Protection eingetragen
  [ ] "Do not allow bypassing" aktiviert
  [ ] Test: Draft-PR erstellen → qm-gate wird geskippt
  [ ] Test: Echter PR mit ASSUMPTION[unverified] → Merge blockiert
```

### REFLEX Review Gate (PFLICHT — ADR-165)

After manual checklist, run automated verification:

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all <REPO_NAME> --fail-on block
```

**Acceptance criteria:**
- Exit code 0 (no BLOCK findings)
- All WARN findings documented or suppressed in `.reflex/suppressions.yaml`

If BLOCK findings remain, fix them before considering onboarding complete.

For compliance mode — compare against initial diagnostic:

```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all <REPO_NAME>
# Should show 0 new findings vs baseline
```

### Baseline setzen (end of onboarding)

Once all BLOCKs are resolved, save baseline for future delta tracking:

```bash
cd ${GITHUB_DIR:-$HOME/github}/iil-reflex && .venv/bin/python -m reflex review all <REPO_NAME> --init-baseline
```

This ensures future `reflex review` runs only report NEW regressions.

---

## Referenz: Bestehende Repos als Vorlage

| Vorlage für | Bestes Beispiel |
|-------------|----------------|
| CI/CD mit Reusable Workflows | `risk-hub/.github/workflows/` |
| Dockerfile + Entrypoint | `risk-hub/docker/app/` |
| docker-compose.prod.yml | `risk-hub/docker-compose.prod.yml` |
| Test-Infrastruktur (conftest, factories) | `travel-beat/tests/` |
| registry/repos.yaml | `platform/registry/repos.yaml` |
| SSH-Setup | ADR-060 |
| REFLEX Review (Compliance-Check) | `iil-reflex/reflex/review/` |

## Referenz: Compliance-Workflow für bestehende Repos

Kurzfassung des optimierten Flows für existierende Repos:

```text
1. reflex review all <repo>              → Diagnose (was fehlt?)
2. User entscheidet: BLOCKs fixen        → Ja/Nein
3. Relevante Steps aus diesem Workflow    → nur was nötig ist
4. reflex review all <repo> --fail-on block → Verifikation
5. reflex review all <repo> --init-baseline → Baseline setzen
6. Commit + Push                          → CI/CD prüft automatisch
```

**Typische Compliance-Findings bei bestehenden Repos:**

| Finding | Fix-Aufwand | Typischer Fix |
|---------|-------------|---------------|
| `repo.missing_dockerignore` | trivial | Step 1.5 kopieren |
| `compose.healthcheck_in_dockerfile` | simple | HC aus Dockerfile → Compose |
| `compose.no_restart_policy` | trivial | `restart: unless-stopped` |
| `compose.port_all_interfaces` | trivial | `0.0.0.0:PORT` → `127.0.0.1:PORT` |
| `adr.missing_frontmatter_*` | moderate | MADR 4.0 Frontmatter nachrüsten |
| `port.drift_*` | simple | ports.yaml oder Compose anpassen |
