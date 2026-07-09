# Runbook: Git-History-Rewrite nach Secret-Leak (platform)

> **Status:** vorbereitet, nicht ausgeführt (2026-07-02). Für ein ruhiges Fenster.
> **Kontext:** repo-optimize O-1 — 26 publicly-leaked Secret-Alerts (2026-04-04),
> alle rotiert + als `revoked` geschlossen (2026-07-02). Die Keys sind tot; dieser
> Rewrite ist **History-Hygiene**, kein offenes Sicherheitsloch. Der Live-Fund im
> HEAD wurde separat via PR #823 redigiert.

## Wann ausführen (Vorbedingungen)

- **Wenige/keine offenen PRs** — ein SHA-Rewrite invalidiert JEDEN offenen PR
  (divergiert von der neu geschriebenen `main`). Stand Planung: 16 offen.
- **Keine parallelen Sessions am geteilten Tree** — Stand Planung: 9 Worktrees.
- Force-Push-Fenster mit dem Team abgestimmt (jeder Klon muss danach re-syncen).

## Warum überhaupt (ehrliche Cost/Benefit)

Die Blobs (`apps/bfagent/.Kopie.env`, `.env.backup`, DB-Dump …) bleiben trotz
Rotation in der **öffentlichen** Git-History abrufbar. Der Rewrite tilgt sie —
aber: (a) er bricht alle offenen PRs + Worktrees + Klone auf allen Maschinen,
(b) GitHubs Cache hält unreachable-Blobs auch nach Force-Push noch (nur GitHub
Support purged sie endgültig). Deshalb: **nur bei ruhigem Fenster**, nicht ad hoc.

## Betroffene Pfade (verifiziert 2026-07-02, alle 26 Alert-Locations)

**Gruppe A — komplett aus History tilgen** (nichts davon im HEAD; `apps/bfagent/`
ist vollständig aus HEAD entfernt):

```
apps/bfagent/
.env.backup
docs/adr/inputs/mcp_config_windows.json
docs/REVIEW-ADR-022.md
```

**Gruppe B — Inhalt scrubben, Datei behalten** (im HEAD, via #823 redigiert):

```
docs/adr/reviews/REVIEW-ADR-022.md
```

→ Regex-Ersetzung, damit die Datei im HEAD erhalten bleibt und kein Secret-Wert
angefasst werden muss.

## Ablauf

**0. Backup + Mirror (filter-repo NIE im Arbeitsbaum):**
```bash
cd /tmp && git clone --mirror git@github.com:achimdehnert/platform.git platform-rewrite.git
cd platform-rewrite.git
git bundle create ~/shared/platform-prerewrite-$(date +%Y%m%d).bundle --all
```

**1. Helfer-Dateien** (Inhalt unten, im Mirror-Verzeichnis ablegen):

`paths-to-remove.txt`:
```
apps/bfagent/
.env.backup
docs/adr/inputs/mcp_config_windows.json
docs/REVIEW-ADR-022.md
```

`replacements.txt` (Regex — materialisiert keinen Secret-Wert):
```
regex:ghp_[A-Za-z0-9]{36}==>***REDACTED-GITHUB-PAT***
regex:github_pat_[A-Za-z0-9_]{20,}==>***REDACTED-GITHUB-PAT***
```

**2. Rewrite (zwei Operationen):**
```bash
git filter-repo --invert-paths --paths-from-file paths-to-remove.txt
git filter-repo --replace-text replacements.txt
```

**3. Gegenprüfen (muss leer sein):**
```bash
git log --all --oneline -- apps/bfagent/ .env.backup
git grep -I "ghp_[A-Za-z0-9]" $(git rev-list --all) 2>/dev/null | head
```

**4. Force-Push (Punkt ohne Wiederkehr):**
```bash
git push --force --mirror origin
```

**5. Fleet neu synchronisieren (PFLICHT):** auf JEDER Maschine (WSL, dev-desktop,
Prod-Server) + jedem Worktree:
```bash
git fetch && git reset --hard origin/main   # oder frisch klonen
```
> Alte Klone haben inkompatible SHAs. Wer aus einem alten Klon pusht, bringt die
> Leaks zurück. Offene PRs vorher mergen/schließen oder danach manuell rebasen.

**6. GitHub-Cache purgen:** Force-Push entfernt die Blobs NICHT sofort von
GitHubs Servern. Für echtes Purgen GitHub Support kontaktieren
(„purge cached views / stale blobs after history rewrite"). Bis dahin bleibt
Push-Protection + die erfolgte Rotation die Absicherung.

## Zusatz-Check (nicht Alert-erfasst)

Der eingecheckte DB-Dump `apps/bfagent/.db_backups/20251216125736.sql` enthielt
mind. den OpenAI-Key (#13). Wird durch Gruppe A (`apps/bfagent/`) mit-getilgt —
ABER falls der Dump weitere Zugangsdaten ohne eigenen Alert enthält, VOR dem
Rewrite prüfen (im Mirror, Wert nicht ausgeben), damit auch die rotiert werden.

## Verankerung

- Secret-Rotations-Abschluss: repo-optimize-Report `~/shared/repo-optimize-platform-2026-07-02.md` (Befund S-1).
- Verwandtes Runbook-Muster: `docs/runbooks/iil-migration-breakglass-pypi-token.md`.
