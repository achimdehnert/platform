---
description: Repo sicher stilllegen — Identitäts-Verifikation, Lebenszeichen-Checks, verifiziertes Backup, archive-first mit Cooling-off; der irreversible DELETE bleibt IMMER Human-Only
mode: write
---

# /delete-repo — Gated Repo-Stilllegung (archive-first, delete = Human-Only)

> **Zweck:** Ein Repo kontrolliert aus dem Verkehr ziehen, ohne dass ein einziger
> Automatisierungs-Fehler etwas Unwiederbringliches zerstört. Der Skill macht **alles
> außer dem Löschen**: Identität beweisen, Lebenszeichen prüfen, Backup erzeugen und
> verifizieren, archivieren (reversibel), Cooling-off takten, Registry-Cleanup anstoßen.
> Der `DELETE`-API-Call selbst wird **niemals vom Skill ausgeführt** — er wird nach
> Ablauf der Frist als exaktes Kommando für den Menschen ausgegeben (Governance-Entscheid
> platform#1012, Variante c).
>
> **Warum so:** `DELETE /repos/…` hat kein Soft-Delete. Realfall 🌀
> `feedback_repo_identity_not_from_remote_name`: ein Rename-Redirect wurde falsch
> gedeutet und ein **lebendes** Repo archiviert — bei „delete" wäre derselbe Fehler
> endgültig gewesen. Archivieren ist reversibel → darf der Skill nach Gates selbst;
> Löschen ist es nicht → bleibt beim Menschen (autonomy-gates Gate 1).

## Verwendung

```
/delete-repo <owner>/<repo>              # startet Phase 0–4 (bis Archiv + Tombstone)
/delete-repo <owner>/<repo> --checks-only # nur Phase 0–1 (Advisory-Report, read-only)
```

## Phase 0: Identitäts-Beweis (HART — vor allem anderen)

1. **NIE** die Identität aus einem lokalen `git remote` oder Verzeichnisnamen ableiten.
2. `gh api repos/<owner>/<repo>` → aus der Antwort `id`, `full_name`, `created_at`,
   `archived`, `default_branch` festhalten.
3. **Rename-Redirect-Falle:** Antwort-`full_name` ≠ angefragter Name ⇒ **ABBRUCH** mit
   Meldung („angefragt X, API liefert Y — Redirect, Ziel unklar"). Kein Weiterarbeiten.
4. Alle Folge-Calls über die numerische ID (`gh api repositories/<id>/…`), nicht über den
   Namen — die ID überlebt Renames nicht falsch.

## Phase 1: Lebenszeichen-Checks (jeder Fund = Stopp mit Report)

| Check | Kommando (Kern) | Blockierend? |
|---|---|---|
| Letzter Commit < 90 Tage | `gh api repositories/<id>/commits?per_page=1` → Datum | ⛔ ja |
| Offene PRs/Issues (nicht-Bot) | `gh api repositories/<id>/pulls?state=open` + issues | ⛔ ja |
| Prod-Registrierung | grep in `platform/scripts/repo-registry.yaml`, `infra/ports.yaml`, `registry/canonical.yaml` | ⛔ ja (hart, kein Override im Skill) |
| Org-weite Referenzen | `gh search code "<owner>/<repo>" --json path,repository` (uses:, submodule, URLs) | ⛔ ja |
| GHCR-Packages / Release-Assets | `gh api /orgs/<org>/packages?package_type=container` filter | ⚠️ Report |
| Webhooks / Deployments / Environments | `gh api repositories/<id>/hooks` etc. | ⚠️ Report |

`--checks-only` endet hier mit dem Report (read-only, gate-frei — jederzeit erlaubt).

## Phase 2: Backup-Pflicht mit Verifikation (ohne grünes Backup keine Phase 3)

1. Ziel: `~/backups/repo-graveyard/<owner>--<repo>--<YYYY-MM-DD>/`
2. `git clone --mirror` + `git bundle create repo.bundle --all`
3. Metadaten-Export: Issues, PRs, Releases (inkl. Assets), Wiki falls vorhanden —
   via `gh api`-Pagination als JSONL.
4. **Verifikation (Pflicht, nicht optional):**
   - `git --git-dir=<mirror> fsck --strict` ohne Fehler
   - `git --git-dir=<mirror> rev-parse <default_branch>` == API-HEAD-SHA
   - Bundle mit `git bundle verify` geprüft
5. Backup-Pfad + SHAs in den Tombstone (Phase 4) schreiben.

## Phase 3: Human-Gate (Doppel-Bestätigung — generisches „go" reicht NICHT)

Der User muss **wörtlich** antworten mit:
1. dem vollen `owner/repo`-Namen (abgetippt, nicht zitiert), UND
2. dem Wort **ARCHIVIEREN**.

Fehlt eines von beidem → nicht ausführen, einmal präzise nachfragen, dann stoppen.
(Begründung: der Permission-Classifier lässt wörtlich Freigegebenes durch — die
Bestätigung muss deshalb das Ziel benennen, nicht nur zustimmen.)

## Phase 4: Archivieren + Cooling-off (reversibel — darf der Skill)

1. `gh api -X PATCH repositories/<id> -f archived=true`
2. Topic setzen: `scheduled-deletion-<YYYY-MM-DD+30d>` (30 Tage Cooling-off, Default).
3. **Tombstone-Issue** in `platform` anlegen: Repo, ID, Backup-Pfad+SHAs, Frist-Datum,
   Lebenszeichen-Report, Label `repo-graveyard`.
4. Registry-Cleanup als **separate Folge-PRs** vorschlagen (repo-registry.yaml,
   ports.yaml, catalog-info-Referenzen, Nginx) — nicht im selben Atemzug ausführen.

## Phase 5: DELETE — Human-Only, immer

Nach Ablauf der Frist (Tombstone-Issue erinnert) gibt der Skill **nur das Kommando aus**:

```
# Erst delete_repo-Scope ad-hoc erteilen (Token hat ihn im Alltag NICHT):
#   gh auth refresh -h github.com -s delete_repo
gh api -X DELETE repositories/<id>
```

Der Skill führt dieses Kommando unter keinen Umständen selbst aus — auch nicht auf
Aufforderung. Wer löschen will, tippt es selbst (bewusster Mensch-Moment, Audit-Trail
liegt beim User-Token). Danach: Tombstone-Issue schließen, Backup-Retention prüfen
(Default: 12 Monate aufbewahren).

## Anti-Patterns

- ❌ Repo-Identität aus lokalem Remote-Namen/Verzeichnis ableiten (🌀 Realfall — Phase 0).
- ❌ Rename-Redirect stillschweigend folgen.
- ❌ Archivieren oder Löschen ohne **verifiziertes** Backup (fsck + SHA-Abgleich).
- ❌ Ein generisches „go"/„ja" als Phase-3-Bestätigung akzeptieren.
- ❌ Den DELETE-Call skripten, in den Skill zurückholen oder „nur dieses eine Mal"
  automatisieren — das ist die eine Linie, die dieser Skill nie überschreitet.
- ❌ Prod-Registrierungs-Block per Argument/Flag übersteuerbar machen.
- ❌ Registry-Cleanup im selben Durchgang wie das Archivieren mergen (Blast-Radius trennen).

## Tier-Routing (session-routing.md)

Ausführung dieses Skills ist **Sonnet-tauglich** — das Urteil steckt in den Gates, nicht
im Ausführenden. Änderungen AM Skill (Gates lockern, Schwellwerte, Phase-5-Linie) sind
Fable/Opus-Arbeit + Review-Pflicht.

## Changelog

- 2026-07-08: Initial (Fable-5-Design, Session ausschreibungs-hub). Materialisiert
  Variante (c) aus platform#1012, verschärft um archive-first + Cooling-off + Tombstone.
  Offene ADR-Punkte aus #1012 als Defaults gesetzt: Aktivitäts-Schwelle 90d,
  Prod-Check blockierend ohne Override, Backup nach ~/backups/repo-graveyard (12 Monate),
  Ausführungs-Rolle: Owner/Admin. Ratifizierung der Defaults = Review dieses PRs.
