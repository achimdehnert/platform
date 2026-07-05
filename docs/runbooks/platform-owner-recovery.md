# Runbook — platform Owner Recovery & Leaver Process

> **Zweck:** Bus-Faktor-Absicherung der SSoT `platform` für den **Normalfall Owner-Ausfall**
> (nicht nur den PyPI-Break-Glass-Sonderfall). Phase-A-Artefakt aus
> [`KONZ-platform-012`](../konzepte/KONZ-platform-012-platform-org-migration.md); vom
> Maintainer-2028-Adversariat ausdrücklich als „jetzt festschreiben, nicht wenn gebraucht" gefordert.
> **Status:** aktiv · **Owner:** Achim Dehnert · **Review-by:** 2026-09-15

## Ist-Zustand (verifiziert 2026-07-05)

| Fakt | Wert | Beleg |
|---|---|---|
| platform-Owner-Konto | `achimdehnert` (**persönliches User-Konto**, keine Org) | `gh api repos/achimdehnert/platform --jq .owner.type` → User |
| Repo-Collaborators | **nur `achimdehnert`** | `gh api repos/achimdehnert/platform/collaborators` |
| CODEOWNERS | alles `@achimdehnert` (einziger Owner) | `.github/CODEOWNERS` |
| iilgmbh-Org-Owner | 2 (`achimdehnert`, `wirdigital`) | `gh api "orgs/iilgmbh/members?role=admin"` → 2 |
| PyPI-org `iil` 2. Owner | **nicht verifiziert** | keine GitHub-API-Fläche |

**Kern-Lücke:** Solange platform am persönlichen Konto hängt und `achimdehnert` der einzige
Collaborator ist, ist der Bus-Faktor der SSoT **= 1**, obwohl die iilgmbh-Org bereits 2 Owner hat.
Die Org-Owner-Rolle verschafft **keinen** Zugriff auf ein Repo unter dem *persönlichen* Konto.
Dieses Runbook definiert (a) wie Zugriff redundant gemacht wird, (b) wie ein Ausfall überbrückt
wird, (c) wie ein ausscheidender Zugriffsinhaber sauber entzogen wird.

## Rollen & benannte Prinzipale

| Rolle | Prinzipal (2026-07-05) | Kanal | Verantwortung |
|---|---|---|---|
| Primary Owner | Achim Dehnert (`achimdehnert`) | (interner Kontakt) | SSoT-Verwaltung, Merges, Registry/ADR-Schreibrecht |
| Recovery Owner | **TBD → wirdigital**, sobald als Collaborator (write/maintain) hinzugefügt | (interner Kontakt) | Übernahme bei Ausfall Primary; muss firmenkontrolliert + 2FA-aktiv sein |
| Break-Glass (PyPI) | s. [`iil-migration-breakglass-pypi-token.md`](iil-migration-breakglass-pypi-token.md) | — | nur PyPI-Token-Sonderfall |

> **Offen (Voraussetzung, Owner-Entscheid):** wirdigital ist noch **kein** Collaborator auf
> `achimdehnert/platform`. Bis das erfolgt, ist „Recovery Owner" nur nominal — der Bus-Faktor
> bleibt faktisch 1. Schritt R-0 unten schließt das.

## R-0 — Zugriffsredundanz herstellen (Voraussetzung, einmalig)

1. **Recovery Owner als Collaborator hinzufügen** (Owner-Aktion, Gate: Security-Config):
   ```
   gh api -X PUT repos/achimdehnert/platform/collaborators/wirdigital -f permission=maintain
   ```
   `maintain` = Repo verwalten (Settings, Branch-Protection) ohne Owner-Löschrechte; `push` als
   Minimal-Variante, wenn nur Review-Redundanz gewünscht.
2. **CODEOWNERS ergänzen**, sobald Zugriff besteht (sonst ignoriert GitHub die Zeile still):
   ```
   * @achimdehnert @wirdigital
   ```
3. **Branch-Protection „Required Reviewer ≠ Autor"** auf `main` (Ruleset 17621471 erweitern oder
   `required_pull_request_reviews.required_approving_review_count=1` + `require_code_owner_reviews`).
4. **Verifizieren:** `gh api repos/achimdehnert/platform/collaborators/wirdigital` → 204 (Zugriff da).

> Diese vier Schritte sind die reversible **Phase-A-Redundanz** — sie heben den Bus-Faktor auf 2
> **ohne** den irreversiblen Org-Transfer (KONZ-012 §5, Alternative A1). Der Transfer selbst bleibt
> ein separater, gegateter Entscheid (KONZ-012 Phase C).

## R-1 — Ausfall Primary Owner (temporär, z. B. Urlaub/Krankheit/2FA-Verlust)

1. Recovery Owner übernimmt Merges/Registry-/ADR-Pflege über seinen Collaborator-Zugriff (R-0).
2. Kein Secret-Zugriff nötig für Repo-Arbeit — Prod-Secrets liegen in `~/.secrets/` bzw. als
   Repo/Org-Secrets, nicht im Klartext im Repo.
3. Wenn Prod-Deploy nötig: der Runner-Host (`prod-server`) läuft unabhängig vom GitHub-Login;
   Deploy via CI bleibt funktionsfähig, solange die Repo-Secrets gültig sind.

## R-2 — Ausfall Primary Owner (dauerhaft / Konto unerreichbar)

1. **GitHub-Repo:** Ein User-Repo kann nur vom Konto-Eigentümer transferiert werden. Ist
   `achimdehnert` dauerhaft unerreichbar, ist der saubere Weg der **Org-Transfer nach iilgmbh**
   (KONZ-012 Phase C) — dann greift die 2-Owner-Redundanz der Org. **Lehre:** Genau dieser Fall
   ist das stärkste Argument, den Transfer *vor* einem echten Ausfall geplant durchzuführen, nicht
   als Notfall-Aktion.
2. **PyPI:** Break-Glass-Runbook (Link oben) für Token; PyPI-org-Owner-Wechsel braucht den 2.
   `iil`-Owner (offen — Phase A (a)).
3. **Secrets:** aus `~/.secrets/` re-provisionierbar durch den Recovery Owner, sofern er Zugriff
   auf den Secret-Store hat (separater Zugriffspfad, hier nicht im Repo dokumentiert).

## R-3 — Leaver-Prozess (Zugriffsinhaber scheidet aus)

**Auslöser:** Ein Collaborator/Owner verlässt die Firma oder das Projekt.

1. **Sofort:** Collaborator-Zugriff entziehen —
   ```
   gh api -X DELETE repos/achimdehnert/platform/collaborators/<login>
   ```
   bzw. Org-Owner-Rolle: `gh api -X DELETE orgs/iilgmbh/memberships/<login>` (nach Prüfung, dass
   ≥1 anderer Owner bleibt — nie den letzten Owner entfernen).
2. **Secrets rotieren**, auf die der Leaver Zugriff hatte (Repo-/Org-Secrets, `~/.secrets/`-Store,
   PyPI-Token) — Zombie-Zugriff auf die SSoT ist gravierender als bei einem Package-Repo, weil
   hier Governance-Dokumente selbst betroffen sind.
3. **PATs/OIDC prüfen:** vom Leaver ausgestellte Fine-grained-PATs widerrufen; Trusted-Publisher-
   Einträge gegenchecken.
4. **CODEOWNERS + Recovery-Matrix** aktualisieren (Leaver aus diesem Runbook entfernen, Nachfolger
   benennen).

## Review-Kadenz (REC-1-Klausel)

Halbjährlich (nächste: **2026-09-15**, dann rollierend): Owner-/Collaborator-Liste + Trusted-
Publisher-Einträge gegen diesen Runbook prüfen; verwaiste Zugriffe entziehen; Recovery-Owner-
Erreichbarkeit bestätigen. Ohne Pflege verfällt dieses Runbook per `review_by`.

## Verwandt

- [`KONZ-platform-012`](../konzepte/KONZ-platform-012-platform-org-migration.md) — Mutter-Konzept (Phase A/B/C).
- [`ADR-255`](../adr/ADR-255-iilgmbh-org-migration-pypi-family.md) — REC-1 (2 Owner + Recovery + Review-Kadenz), REC-9 (Break-Glass).
- [`iil-migration-breakglass-pypi-token.md`](iil-migration-breakglass-pypi-token.md) — PyPI-Token-Sonderfall.
