---
description: Publish a Python package (iil-aifw, promptfw, authoringfw, ...) to PyPI via OIDC
mode: write
---

# /release — PyPI Publish (OIDC-only, ADR-278)

> **Wann:** Ein `iil-*`-Paket auf PyPI veröffentlichen — Version-Bump, Tag, CI-Publish,
> Beweis am Artefakt.
> **Wann NICHT:** neues Paket aufsetzen (→ `/onboard-repo`) · Flotten-weite
> Governance-/Portfolio-Entscheidungen (→ KONZ-platform-018, ADR-266) · lokales
> `twine upload` oder `~/.pypirc` irgendeines Pakets — **verboten seit ADR-278**,
> siehe Anti-Patterns.

## Verwendung

```
/release <package-name>   # z.B. aifw, promptfw, authoringfw, iil-testkit, iil-codeguard
```

## Step 0: Publish-Klasse des Pakets bestimmen

Jedes `iil-*`-Paket publiziert **ausschließlich über OIDC Trusted Publishing**
(ADR-278) — nie über ein lokales API-Token. Der Aufrufweg unterscheidet sich
nach **wo** der Workflow läuft, nicht nach dem Auth-Mechanismus:

| Klasse | Pakete | Publish-Workflow läuft in | Auslöser |
|---|---|---|---|
| A — repo-eigen (Regelfall) | aifw, promptfw, authoringfw, weltenfw, outlinefw, learnfw, iil-django-commons, nl2cad, iil-testkit (**neu**, s. Sonderfall unten), … | Paket-Repo selbst (`.github/workflows/publish.yml`) | Tag `vX.Y.Z` push **oder** `workflow_dispatch` |
| B — platform-remote (zentral) | iil-codeguard, iil-ingest | `platform`-Repo (`publish-iil-<pkg>.yml`), checkt Paket-Repo per `PROJECT_PAT` aus | nur `workflow_dispatch` |

Quelle für den aktuellen Stand: `registry/pypi-fleet.yaml` bzw. ADR-278
`Umsetzungsstand`. Im Zweifel: `gh workflow list -R achimdehnert/<repo>` prüft,
ob das Paket-Repo ein eigenes `publish.yml` hat (→ Klasse A).

## Step 1: Version-Bump + CHANGELOG + Tag (K3-Invariante)

Der Tag **muss** exakt der `pyproject.toml`-Version entsprechen — sonst laufen
Fleet-Inventar und Guard blind (KONZ-platform-018 K3).

```bash
cd ${GITHUB_DIR:-$HOME/github}/<paket-repo>
# Version in pyproject.toml anheben, CHANGELOG.md ergänzen — dann:
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): <version>"
git tag "v<version>"
git push origin main --follow-tags
```

Für Klasse-B-Pakete (codeguard, ingest) läuft dieser Schritt identisch **im
Paket-Repo** — der Tag/Commit löst dort nichts aus, er ist nur die
Versionsquelle, die der platform-remote-Workflow beim Checkout sieht.

## Step 2: Publish auslösen

**Klasse A (repo-eigen)** — der Tag-Push aus Step 1 löst bereits `publish.yml`
aus. Alternativ ohne Tag:

```bash
gh workflow run publish.yml -R achimdehnert/<paket-repo> -f target=pypi
```

**Klasse B (platform-remote: iil-codeguard, iil-ingest)** — kein Tag-Trigger,
immer per Dispatch aus `platform`:

```bash
gh workflow run publish-iil-codeguard.yml -R achimdehnert/platform
# bzw.
gh workflow run publish-iil-ingest.yml -R achimdehnert/platform
```

```bash
# Lauf verfolgen:
gh run list -R achimdehnert/platform --workflow publish-iil-codeguard.yml -L 1
```

## Step 3: Beweis am Artefakt — PyPI Integrity API (nicht CI-Grün)

Ein grüner Workflow-Lauf beweist nur, dass *ein* Upload passiert ist — nicht,
dass er über OIDC lief. Das einzige belastbare Signal ist die **Attestation am
veröffentlichten Artefakt** (🌀 zwei Token-Uploads trotz grünem OIDC-Workflow,
#1904, 25./26.08.2026):

```bash
# 1. Exakten Wheel-Dateinamen ermitteln
curl -s "https://pypi.org/pypi/<name>/<version>/json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print([u['filename'] for u in d['urls']])"

# 2. Provenance abfragen
curl -s -H "Accept: application/vnd.pypi.integrity.v1+json" \
  "https://pypi.org/integrity/<name>/<version>/<wheel-filename>/provenance" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('attestation_bundles', [])))"
```

- `attestation_bundles` **>= 1** → OIDC Trusted Publishing, wie in ADR-278 verlangt.
- `0`, fehlendes Feld oder HTTP-Fehler → das Release lief per Token — **nicht**
  als erledigt melden; siehe #1904 für den Eskalationspfad (Owner-Entscheid,
  kein automatischer Widerruf).

## Sonderfall iil-testkit (Übergang, KONZ-platform-052 V1)

`iil-testkit` hat seit `iil-testkit#21` ein **eigenes** OIDC-`publish.yml`
(Trusted Publisher auf PyPI gesetzt, Klasse A wie oben). Der **platform-seitige**
`publish-iil-testkit.yml` (Klasse-B-Muster, aber noch mit `TWINE_PASSWORD` +
`twine upload` — der in #1904 gemeldete Verstoß) bleibt bis dahin unangetastet
im Repo stehen und wird **nicht** mehr benutzt:

- Neue Releases: **immer** über das eigene `publish.yml` (Step 2, Klasse A) —
  nie mehr über `publish-iil-testkit.yml` dispatchen.
- `publish-iil-testkit.yml` + Secret `PYPI_API_TOKEN` (platform-Repo) werden
  erst entfernt, **nachdem** Step 3 für das erste Release über den neuen Pfad
  `attestation_bundles >= 1` bestätigt hat (Reihenfolge aus 🌀
  `never_remove_token_without_pypi_binding_proof` — nie Token-Zeile ohne
  Bindungs-Beweis raus).

## Output-Format

```
Paket: <name>  Klasse: A|B  Version: <alt> → <neu>  Tag: v<neu>
Workflow-Run: <URL>  Status: <success|failure>
Integrity-API: attestation_bundles=<n>  → OIDC bestätigt | TOKEN-VERDACHT
```

## Anti-Patterns

- ❌ `~/.pypirc` mit `[pypi]`/`[testpypi]`-Sektion anlegen oder pflegen — jeder
  lokale Upload umgeht Trusted Publishing und wird von PyPI aktiv gemeldet
  (ADR-278, #1904: zwei Meldungen „API token used … despite Trusted Publishing
  enabled" innerhalb von 24h).
- ❌ `TWINE_PASSWORD`/`PYPI_API_TOKEN` lokal exportieren oder `twine upload
  dist/*` von der Dev-Maschine ausführen — für **kein** Paket, auch nicht
  „nur zum Testen".
- ❌ Workflow-Status („CI grün") als Publish-Beweis nehmen — Beweis ist
  ausschließlich Step 3 (Integrity API, Artefakt-Ebene).
- ❌ Tag pushen, dessen Version von `pyproject.toml` abweicht — bricht die
  K3-Invariante und macht das Fleet-Inventar blind (KONZ-platform-018).
- ❌ Für `iil-testkit` weiter `publish-iil-testkit.yml` dispatchen, sobald das
  eigene `publish.yml` existiert — siehe Sonderfall oben.
- ❌ Ohne Owner-Freigabe ein PyPI-Repo-Secret (`PYPI_API_TOKEN` o.ä.) löschen —
  das ist eine Security-Config-Änderung (Gate) und braucht den Bindungs-Beweis
  aus Step 3 zuerst.

## Changelog

- 2026-05-15 (b5d9f6af): Initial. Zwei Pfade: `iil-testkit` autonom per
  Repo-Dispatch (platform-Secret `PYPI_API_TOKEN`), alle anderen Pakete lokal
  über `~/.pypirc` + `scripts/publish-package.sh` (twine).
- 2026-08-27 (ADR-278, KONZ-platform-052 V3, #1904): **OIDC-only-Umbau.**
  Lokaler Token-/`~/.pypirc`-/`twine upload`-Pfad vollständig entfernt.
  Publish läuft jetzt ausschließlich über das jeweilige Repo-eigene
  `publish.yml` (Tag `vX.Y.Z` push oder `workflow_dispatch`) bzw. für die
  zwei zentral aus `platform` publizierten Pakete (iil-codeguard, iil-ingest)
  über `gh workflow run publish-iil-<pkg>.yml -R achimdehnert/platform`.
  Beweis ist jetzt die PyPI-Integrity-API (`attestation_bundles >= 1`) statt
  grüner CI. `iil-testkit` als Übergangsfall dokumentiert (eigenes
  `publish.yml` seit `iil-testkit#21`, platform-seitiger Token-Publisher
  bleibt bis zum ersten bewiesenen Release über den neuen Pfad stehen).
  Anlass: zwei Token-Uploads trotz konfiguriertem Trusted Publisher
  (`iil-aifw` 25.08., `iil-testkit` 26.08. — #1904).
