# ADR-090 Review — Critical Assessment

> **Reviewer:** Claude (AI-assisted Architecture Review)
> **Datum:** 2026-02-27
> **Basis:** `docs/templates/adr-review-checklist.md`, ADR-056, ADR-057, ADR-071, ADR-042
> **Bewertung:** 🔴 **Nicht merge-fähig** — 5 kritische, 8 schwere, 6 moderate Befunde

---

## Zusammenfassung

ADR-090 konsolidiert bestehende Pipeline-Patterns aus ADR-056/057/071/054 in eine Hybrid-Matrix-Pipeline. Die Architektur-Entscheidung (Fast Gate → Parallel ②b ‖ ③) ist **solide und gut begründet**. Die Implementierung enthält jedoch **schwerwiegende Abweichungen** von etablierten Platform-Konventionen, Sicherheitslücken und fehlende MADR-4.0-Pflichtabschnitte.

---

## 🔴 KRITISCH (Merge-Blocker)

### K1: `StrictHostKeyChecking=no` — Security Violation

**Befund:** Stage ⑤ Pre-Flight (Zeile 389):
```yaml
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
  root@88.198.191.108 "echo OK"
```

**Risiko:** Man-in-the-Middle-Angriff. Die Review-Checklist (§2.3) verbietet `StrictHostKeyChecking=no` explizit. ADR-042 zeigt das korrekte Pattern mit `ssh-keyscan`.

**Empfehlung:** Ersetzen durch:
```yaml
    - name: Setup SSH
      run: |
        mkdir -p ~/.ssh
        echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_ed25519
        chmod 600 ~/.ssh/id_ed25519
        ssh-keyscan -H ${{ secrets.DEPLOY_HOST }} >> ~/.ssh/known_hosts
```

---

### K2: Server-IP und `root`-User hardcoded — Secrets-Violation

**Befund:** IP `88.198.191.108` und User `root` sind in Stages ⑤, ⑥, ⑦ direkt im YAML hardcoded (Zeilen 390, 441, 450, 462, 467, 473, 505, 511, 520).

**Risiko:** Verstößt gegen Review-Checklist §2.6: „Secrets via `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER` (not hardcoded)". ADR-056 R1 hat genau dieses Problem bereits als Fix dokumentiert. ADR-061 existiert explizit um Hardcoding zu eliminieren.

**Empfehlung:** Alle SSH-Aufrufe auf Secrets umstellen:
```yaml
    - name: Server Pull + Recreate
      run: |
        ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml pull && \
          docker compose -f docker-compose.prod.yml up -d --force-recreate
        "
```

---

### K3: `runs-on: ubuntu-latest` statt Self-Hosted Runner

**Befund:** Alle Jobs verwenden `runs-on: ubuntu-latest`.

**Risiko:** ADR-042 hat einen Self-Hosted Runner auf dem Dev-Server implementiert (Status: ✅ Done). ADR-056 §2.2 Template verwendet `runs-on: self-hosted`. Die Nutzung von `ubuntu-latest` widerspricht der getroffenen Architektur-Entscheidung und verbraucht GitHub Actions Minuten, die durch den Self-Hosted Runner eingespart werden sollten (~3.300 Min/Monat lt. ADR-042 Appendix A).

**Empfehlung:** Mindestens Deploy-Jobs auf Self-Hosted umstellen. Dann entfällt auch der SSH-Setup (Runner läuft direkt auf dem Server):
```yaml
deploy-verify:
  runs-on: [self-hosted, hetzner, dev]
  needs: deploy-build
```

---

### K4: `permissions:` Block fehlt — GHCR-Push wird fehlschlagen

**Befund:** Kein `permissions:` Block im Workflow definiert (Review-Checklist §2.5).

**Risiko:** Ohne `packages: write` Permission wird `docker push` zu GHCR fehlschlagen. ADR-056 §2.2 Inline-Template enthält den Block explizit.

**Empfehlung:** Am Workflow-Top-Level ergänzen:
```yaml
permissions:
  contents: read
  packages: write
```

---

### K5: Coverage-Merge ist technisch kaputt

**Befund:** Stage ④ (Zeile 348):
```bash
coverage combine *.xml || true
TOTAL=$(coverage report --format=total 2>/dev/null || echo "0")
```

**Risiko:** `coverage combine` arbeitet mit `.coverage`-Dateien (SQLite), nicht mit XML-Reports. Die Pipeline lädt XML-Artefakte hoch (`--cov-report=xml`), versucht dann aber `coverage combine *.xml` — das ist ein Silent Fail (durch `|| true` maskiert). Der Coverage-Gate wird **immer** `0` melden und **immer** fehlschlagen — oder schlimmer, es wird ein einziger XML-Report genommen und als „gesamt" ausgegeben.

**Empfehlung:** Entweder `.coverage`-Dateien als Artifacts hochladen ODER `coverage xml` → `coverage-threshold` Action nutzen. ADR-057 §2.10 zeigt das korrekte Pattern:
```yaml
    - name: Merge + Check Threshold
      run: |
        pip install coverage
        # Beide .coverage-Dateien müssen als Artifacts hochgeladen werden
        coverage combine coverage-python/.coverage coverage-postgres/.coverage
        coverage report --fail-under=80
        coverage xml -o coverage-merged.xml
```

Dafür müssen ②b und ③ `--cov-report=` (leer = .coverage Datei) statt `--cov-report=xml` nutzen.

---

## 🟠 SCHWER (Muss vor Merge behoben werden)

### S1: MADR 4.0 Pflichtabschnitte fehlen

**Befund:** Gegen `docs/templates/adr-template.md` geprüft:

| MADR-Pflichtabschnitt | Status | Hinweis |
|----------------------|--------|---------|
| `## Decision Drivers` | ❌ fehlt | Nur implizit in §1.1 |
| `## Considered Options` (≥3) | ⚠️ unvollständig | Nur 2 Optionen in §1.3 (linear, parallel), kein dritter |
| `## Pros and Cons of the Options` | ❌ fehlt | |
| `## Consequences` (Good/Bad) | ❌ fehlt | |
| `### Confirmation` | ❌ fehlt | Wie wird Compliance verifiziert? |
| `## Repo-Zugehörigkeit` | ❌ fehlt | Template-Pflichtfeld |
| `## More Information` | ❌ fehlt | |

**Risiko:** ADR-059 (Drift Detector) wird diesen ADR als non-compliant flaggen.

**Empfehlung:** Fehlende Sections ergänzen. Insbesondere `Confirmation` mit konkreten Prüfungen wie:
```markdown
### Confirmation
1. `ruff check . && ruff format --check .` läuft in ②a und blockt bei Fehler
2. `python manage.py migrate --check` in ③ erkennt pending Migrations
3. `/livez/` Health Check in ⑥ verifiziert laufende Applikation
4. Coverage ≥ 80% wird in ④ als Gate enforced
```

---

### S2: Pre-Commit Config weicht von ADR-071 Kanonischem Template ab

**Befund:** Stage ① verwendet `commitizen` für Commit-Messages:
```yaml
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.0.0
    hooks:
      - id: commitizen    # Conventional commits
```

**Risiko:** ADR-071 §4.B hat Conventional Commits (`feat:`, `fix:`) **explizit abgelehnt** zugunsten des `[TAG] module: description` Formats. Das kanonische Template in `inputs/.pre-commit-config.yaml` verwendet einen lokalen Hook `bf-commit-msg` mit `scripts/check-commit-msg.sh`. Commitizen erzwingt ein anderes Format und ist **inkompatibel** mit der Platform-Konvention.

Zusätzlich fehlen: `gitleaks`, `check-yaml`, `check-toml`, `check-json`, `check-ast`, `debug-statements`, `no-commit-to-branch`, `validate-pyproject`.

**Empfehlung:** Kanonisches Template aus `platform/docs/adr/inputs/.pre-commit-config.yaml` 1:1 übernehmen. Ruff-Version auf `v0.15.0` aktualisieren (ADR verwendet `v0.8.0`, Platform-Standard ist `v0.15.0`).

---

### S3: Ruff-Version veraltet

**Befund:** `v0.8.0` in der Pre-Commit Config (Zeile 105).

**Risiko:** ADR-071 §6 definiert `v0.15.0` als Platform-Standard. Version `v0.8.0` ist fast ein Jahr alt und hat andere Default-Rules. CI und Local laufen mit unterschiedlichen Ruff-Versionen → False Positives/Negatives.

**Empfehlung:** Auf `v0.15.0` aktualisieren.

---

### S4: Rollback-Mechanismus ist nicht idempotent

**Befund:** Stage ⑦ (Zeilen 511-514):
```yaml
    - name: Rollback to Previous Image
      run: |
        ssh root@88.198.191.108 "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml down && \
          docker compose -f docker-compose.prod.yml up -d
        "
```

**Risiko:** `docker compose down` + `up -d` startet das **gleiche** (fehlerhafte) Image neu, weil `docker compose pull` das neue Image bereits gepullt hat und `latest` überschrieben wurde. Es gibt keinen Mechanismus, um zum vorherigen Image-Tag zurückzukehren. ADR-056 R2 hat dieses Problem bereits adressiert: SHA-Tags neben `latest` werden genau dafür gebraucht.

**Empfehlung:** Vorherigen SHA-Tag speichern und im Rollback verwenden:
```yaml
    - name: Save current image tag before deploy
      id: pre_deploy
      run: |
        CURRENT_SHA=$(ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
          "docker inspect --format='{{index .Config.Labels \"org.opencontainers.image.revision\"}}' \
          ${{ env.CONTAINER }}" 2>/dev/null || echo "unknown")
        echo "previous_sha=${CURRENT_SHA}" >> "$GITHUB_OUTPUT"

    # In Rollback-Job:
    - name: Rollback to Previous Image
      run: |
        PREV_TAG="${{ needs.deploy-verify.outputs.previous_sha }}"
        if [ "$PREV_TAG" = "unknown" ]; then
          echo "WARN: No previous tag found, cannot rollback"
          exit 1
        fi
        ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
          cd ${{ env.SERVER_PATH }} && \
          sed -i 's|:latest|:${PREV_TAG}|g' docker-compose.prod.yml && \
          docker compose -f docker-compose.prod.yml pull && \
          docker compose -f docker-compose.prod.yml up -d --force-recreate
        "
```

---

### S5: Keine `set -euo pipefail` in Bash-Blöcken

**Befund:** Kein einziger `run:`-Block in der gesamten Pipeline beginnt mit `set -euo pipefail`.

**Risiko:** Qualitätskriterium „Robuste Error Handling (set -euo pipefail), klare Exit Codes" wird verletzt. Stille Fehler können durchrutschen — besonders gefährlich in Stages ⑥/⑦ wo SSH-Commands auf dem Produktionsserver laufen.

**Empfehlung:** In jedem mehrzeiligen `run:` Block als erste Zeile:
```yaml
    - name: Any step
      run: |
        set -euo pipefail
        # ... commands
```

---

### S6: Migration-Reihenfolge in Stage ⑥ ist riskant

**Befund:** Stage ⑥ startet Container (`up -d`), dann Health-Check, dann erst Migrations:
```
1. docker compose up -d --force-recreate
2. Health Check (manage.py check --deploy)
3. Run Migrations  ← Django-App läuft bereits mit altem Schema!
4. Smoke Tests
```

**Risiko:** Zwischen Schritt 1 und 3 läuft die neue Django-App gegen das alte DB-Schema. Wenn die neue Version Models hat, die neue Spalten erwarten → 500er für alle Requests in diesem Zeitfenster. ADR-056 §2.2 Template führt Migrations **vor** dem Health-Check aus.

**Empfehlung:** Migrations vor dem ersten Request ausführen. Entweder im Container-Entrypoint oder als separater Compose-Service:
```yaml
    - name: Run Migrations (before app starts)
      run: |
        set -euo pipefail
        ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml run --rm web \
            ${{ env.MIGRATE_CMD }}
        "

    - name: Start App
      run: |
        set -euo pipefail
        ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml up -d --force-recreate
        "
```

---

### S7: Wheel-Install-Syntax falsch

**Befund:** Zeile 190 und 257:
```bash
pip install requirements/wheels/*.whl
```

**Risiko:** Glob-Expansion bei `pip install` kann fehlschlagen wenn keine `.whl` Dateien vorhanden sind (kein `set -euo pipefail` → stiller Fehler). Zudem installiert `pip install *.whl` alle Wheels auf einmal ohne Dependency-Resolution — Reihenfolge ist undefiniert.

**Empfehlung:**
```bash
if ls requirements/wheels/*.whl 1>/dev/null 2>&1; then
  pip install requirements/wheels/*.whl
else
  echo "INFO: No wheels found in requirements/wheels/ — skipping"
fi
```

---

### S8: `on:` Trigger und Workflow-Struktur fehlen

**Befund:** Der ADR zeigt einzelne Job-Blöcke, aber nie den vollständigen Workflow mit `on:` Trigger, `permissions:`, und `env:` Block.

**Risiko:** Nicht klar ob die Pipeline bei `push` auf `main`, bei PRs, oder bei `workflow_dispatch` triggern soll. ADR-056 §2.2 Template zeigt das vollständige Pattern. Ohne vollständigen Workflow ist die Datei nicht direkt nutzbar (Qualitätskriterium: „Outputs als vollständige Dateien").

**Empfehlung:** Vollständigen Workflow am Ende als `ci-cd.yml` Template einfügen, analog zu ADR-056 §2.2.

---

## 🟡 MODERAT (Sollte vor Merge behoben werden)

### M1: Python-Matrix (3.11 + 3.12) ist unnötig

**Befund:** Stage ②b testet gegen Python 3.11 und 3.12 (Zeilen 178-179).

**Risiko:** Alle Platform-Docker-Images verwenden Python 3.12 (ADR-071 `target-version = py312`). Die 3.11-Matrix verdoppelt die Test-Zeit ohne Produktionsrelevanz. Widerspricht dem Ziel „CI-Minuten sparen".

**Empfehlung:** Matrix auf `["3.12"]` reduzieren oder explizit begründen warum 3.11 getestet wird (z.B. Library-Kompatibilität).

---

### M2: `ruff check .` ohne `--output-format=github`

**Befund:** Stage ②a (Zeile 155): `ruff check .`

**Risiko:** Ohne `--output-format=github` werden Lint-Fehler nicht als GitHub Annotations angezeigt. ADR-071 §2.4 und `_ci-quality.yml` verwenden explizit `--output-format=github`.

**Empfehlung:**
```yaml
    - name: Lint
      run: ruff check . --output-format=github
```

---

### M3: Keine Slack-/Notification-Integration in ⑦

**Befund:** Zeile 526: `# Future: Slack/Discord webhook notification`

**Risiko:** ADR-008 definiert Slack-Notifications als Teil der Pipeline. Ohne Benachrichtigung bei Rollback erfährt niemand von einem gescheiterten Deployment bis jemand manuell prüft.

**Empfehlung:** Mindestens einen `curl` zu einem Webhook ergänzen:
```yaml
    - name: Notify Slack
      if: always()
      run: |
        curl -X POST "${{ secrets.SLACK_WEBHOOK_URL }}" \
          -H 'Content-Type: application/json' \
          -d "{\"text\":\"🔴 Deployment FAILED: ${{ vars.DEPLOY_APP_NAME }} — Rollback executed. <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|Logs>\"}"
```

---

### M4: Health-Endpoint nur `/livez/` — `/healthz/` fehlt

**Befund:** Stage ⑥ prüft nur `/livez/` (Liveness).

**Risiko:** Review-Checklist §2.8 erwartet **beide**: `/livez/` (Liveness) + `/healthz/` (Readiness). Liveness sagt nur „Prozess antwortet". Readiness prüft auch DB-Verbindung und kritische Services.

**Empfehlung:** Readiness-Check nach Migrations ergänzen:
```yaml
    - name: Readiness Check
      run: |
        HTTP_STATUS=$(ssh ... "curl -s -o /dev/null -w '%{http_code}' http://localhost:${{ env.PORT }}/healthz/")
        [ "$HTTP_STATUS" = "200" ] || { echo "FAIL: /healthz/ returned $HTTP_STATUS"; exit 1; }
```

---

### M5: `pre-commit-hooks` Version veraltet

**Befund:** `rev: v5.0.0` (Zeile 111) vs. Platform-Standard `rev: v6.0.0` (ADR-071 §6).

**Empfehlung:** Auf `v6.0.0` aktualisieren.

---

### M6: `--maxkb=5000` vs. Platform-Standard `--maxkb=500`

**Befund:** Zeile 115: `args: ['--maxkb=5000']` (5 MB) vs. kanonisches Template `--maxkb=500` (500 KB).

**Risiko:** 5 MB Limit erlaubt versehentliches Einchecken großer Dateien (Wheels, DB-Dumps).

**Empfehlung:** Auf `--maxkb=500` reduzieren (Platform-Standard).

---

## ℹ️ HINWEISE (Verbesserungsvorschläge)

### H1: `amends: ADR-056` — Scope unklar

**Befund:** Frontmatter sagt `amends: ADR-056, ADR-057, ADR-071, ADR-054`.

**Frage:** In welcher Weise amended ADR-090 diese vier ADRs? Ein ADR der vier andere amended sollte klarstellen, welche Abschnitte der Vorgänger überschrieben/ergänzt werden. Alternativ: `relates to` statt `amends` verwenden.

### H2: Timing-Schätzung optimistisch

**Befund:** §4 schätzt die Hybrid-Pipeline auf ~10 Minuten. Die Python-Matrix (2 Versionen) und Coverage-Merge sind nicht berücksichtigt.

### H3: Testverzeichnis-Konvention nicht dokumentiert

**Befund:** `tests/unit/` und `tests/integration/` als Pfade verwendet, ADR-057 §2.2 verwendet `pytest-Marker` (`-m 'not integration'`) statt Verzeichnistrennung. Beides ist valide, aber die Kombination sollte explizit begründet werden.

### H4: Contract-Tests fehlen

**Befund:** ADR-057 definiert Contract-Tests mit Schemathesis als Pflicht-Teststufe auf `main`. Stage ③ enthält keinen Contract-Test-Step.

---

## Compliance-Matrix

| Review-Checklist Item | Status | ADR-090 Befund |
|----------------------|--------|----------------|
| §1.1 YAML Frontmatter | ✅ | Vorhanden |
| §1.2 Title = Decision Statement | ⚠️ | „Abstract CI/CD Pipeline" ist Topic, nicht Decision |
| §1.3 Context section | ✅ | §1 vorhanden |
| §1.4 Decision Drivers | ❌ | Fehlt (S1) |
| §1.5 Considered Options ≥3 | ❌ | Nur 2 Optionen (S1) |
| §1.6 Decision Outcome | ✅ | §1.3 „Gewählt: Hybrid Matrix" |
| §1.7 Pros/Cons | ❌ | Fehlt (S1) |
| §1.8 Consequences Good/Bad | ❌ | Fehlt (S1) |
| §1.9 Confirmation | ❌ | Fehlt (S1) |
| §2.1 IP nicht hardcoded | ❌ | 9× hardcoded (K2) |
| §2.2 SSH root documented | ❌ | root ohne Begründung (K2) |
| §2.3 No StrictHostKeyChecking=no | ❌ | Vorhanden (K1) |
| §2.4 GHCR Registry | ✅ | Via `vars.DEPLOY_IMAGE` |
| §2.5 permissions: packages: write | ❌ | Block fehlt (K4) |
| §2.6 Secrets not hardcoded | ❌ | IP + User hardcoded (K2) |
| §2.7 /opt/\<repo\> convention | ✅ | Via Variable |
| §2.8 /livez/ + /healthz/ | ⚠️ | Nur /livez/ (M4) |

---

## Empfohlenes Vorgehen

**Phase 1 (Blocker — vor Merge):**
1. K1–K5 beheben (Security, Secrets, Runner, Permissions, Coverage)
2. S1 ergänzen (MADR Pflichtabschnitte)
3. S2 korrigieren (Pre-Commit Kanonisches Template)
4. S5 ergänzen (`set -euo pipefail`)

**Phase 2 (Zeitnah):**
5. S4 + S6 (Rollback-Mechanismus, Migration-Reihenfolge)
6. S7 + S8 (Wheel-Syntax, vollständiger Workflow)
7. M1–M6 (Moderate Befunde)

**Phase 3 (Verbesserung):**
8. H1–H4 (Hinweise einarbeiten)
9. Vollständiges `ci-cd.yml` Template als Copy-Paste-fähige Referenz
