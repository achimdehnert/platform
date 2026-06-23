# Runbook: Break-Glass PyPI-Token bei iil-* Org-Migration

> **Status: FINAL (2026-06-23).** Erfüllt das Phase-0-Gate REC-9 von
> **[ADR-255](../adr/ADR-255-iilgmbh-org-migration-pypi-family.md)**. Entscheidungen
> festgelegt (siehe „Festgelegte Entscheidungen" unten): named principal, secure
> channel und max lifetime sind gesetzt — dieses Runbook ist freigegeben.

**Scope**: Wenn bei einem **per-Repo-Cutover** (`achimdehnert/<repo>` →
`iilgmbh/<repo>`) das **OIDC-Trusted-Publishing unter dem neuen Owner noch nicht
greift** und **dringend** ein Release publiziert werden muss, wird als
**Überbrückung** ein **kurzlebiger, projekt-gescopter** PyPI-API-Token benutzt —
streng nach Lifecycle unten. Das ist der **Ausnahmepfad**, nicht der Normalweg.

**Governance**: ADR-255 REC-9 (dieser Runbook-Pflicht), REC-11 (Recovery-Matrix),
Migration Order Schritt 4–5. Verwandt: [`KONZ-002-s3-repo-transfer.md`](KONZ-002-s3-repo-transfer.md)
(PyPI-Lehre: OIDC ist an `owner/repo` gebunden → neuer Publisher vor Transfer).
Token-Heimat-Konvention: `~/.secrets/` (read-only, nie git/logs;
[[reference_secrets_canonical_location]]).

---

## Zuerst: brauchst du Break-Glass überhaupt? (Eskalations-Reihenfolge)

Break-Glass ist die **letzte** Option. In dieser Reihenfolge prüfen:

1. **Dual-Publisher-Shadow (bevorzugt, ADR-255 Alternative).** Den `iilgmbh`-OIDC-
   Trusted-Publisher **vor** dem Transfer anlegen (Owner-Aktion auf pypi.org, **nicht**
   per API) und den alten behalten, bis der erste Release grün durch den neuen Pfad
   läuft. Dann gibt es **kein** No-Publisher-Fenster → **kein** Break-Glass nötig.
2. **OIDC-Fix.** Greift OIDC nicht, fast immer Konfig: Publisher-Claim
   (`owner`=`iilgmbh`, `repo`, `workflow`=`publish.yml`, `environment`=`pypi`) stimmt
   nicht mit dem signierten Token überein. Erst das prüfen/fixen.
3. **Warten.** Ist der Release nicht zeitkritisch → auf den nächsten
   feature-legitimen Release verschieben (ADR-255 AD-14), kein Token.
4. **Break-Glass-Token** (dieser Runbook) — nur wenn 1–3 ausscheiden und der Release
   *jetzt* muss.

---

## REC-9 Pflicht-Eigenschaften (Gate-Checkliste — alle MÜSSEN zutreffen)

- [ ] **Named principal**: solange REC-1 (≥2 Owner) **nicht** erfüllt ist =
      **achimdehnert**; **nach** dem 2. unabhängigen Owner = dieser 2. Owner bzw.
      eine benannte geteilte Incident-Rolle. Immer eine **benannte Person**, kein
      „Team-Account".
- [ ] **Project-scoped only**: Token-Scope = **genau dieses eine PyPI-Projekt**
      (`iil-<paket>`), **niemals** „Entire account". Account-weite Token sind
      verboten (AD-10).
- [ ] **Created at incident time**: Token wird **im Moment des Vorfalls** erzeugt,
      nicht vorab „auf Vorrat".
- [ ] **Secure channel**: direkt von pypi.org in das GitHub-Repo-Secret via
      `gh secret set` über **stdin**, **ohne** Zwischenspeichern auf Disk/Logs
      (Schritt 2). Keine Disk-Kopie ist der Normalfall.
- [ ] **Max lifetime**: kürzestmöglich, **≤ 24 h** Wand-Zeit; Revoke **direkt nach
      Gebrauch**, nicht „am Ende des Tages".
- [ ] **Server-side revocation immediately after use**: Token auf pypi.org
      **löschen** (nicht nur das GitHub-Secret entfernen — beides).
- [ ] **Stored revocation proof**: Beleg der Revokation ablegen (Screenshot/Audit-
      Zeile/Zeitstempel) im Migrations-Registry-Eintrag (`verification`).

---

## Ablauf (ein Repo, ein Release, dann zu)

> Annahme: Repo bereits `iilgmbh/<repo>` (Transfer = Migration Order Schritt 3 erledigt),
> aber OIDC publiziert nicht. `PKG=iil-<paket>`, `REPO=iilgmbh/<repo>`.

### 0. Incident eröffnen
Kurz festhalten: Paket, warum OIDC nicht greift (1-Zeiler), wer der **named principal**
ist, Startzeit. Das ist der Beginn der „max lifetime"-Uhr.

### 1. Projekt-gescopten Token erzeugen (named principal, auf pypi.org)
`pypi.org` → Account settings → **API tokens** → *Add API token* →
**Scope = „Project: `<PKG>`"** (NICHT „Entire account") → Token kopieren.
> Token erscheint **einmal**. Nicht in Datei/History/Chat einfügen.

### 2. Über den secure channel ins **eine** Repo-Secret (kein Disk/Log)
```bash
# Token NICHT als Argument (landet in History) — über stdin einlesen:
gh secret set PYPI_API_TOKEN --repo "$REPO" --body - <<'PASTE'
<<hier den Token einfügen, dann Zeile mit PASTE>>
PASTE
# Gegenprobe: Secret existiert, Wert ist nicht lesbar (by design)
gh secret list --repo "$REPO" | grep PYPI_API_TOKEN
```
> Falls eine lokale Kopie unvermeidbar ist: nur `~/.secrets/pypi_api_token_breakglass`,
> `chmod 600`, und in Schritt 5 mit `shred -u` löschen. Bevorzugt: gar keine Disk-Kopie.

### 3. Genau einen Release publizieren (build/publish getrennt, REC-7)
Den hardened `publish.yml` mit Token-Fallback triggern (kontrolliertes Release-Event,
kein beliebiger Branch-Push). Nur **dieser eine** Release.

### 4. Verifizieren, dass der Release wirklich landete (claim-before-cheapest-check)
```bash
sleep 30
curl -s "https://pypi.org/pypi/$PKG/json" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['info']['version'], d['urls'][0]['upload_time'] if d['urls'] else 'NO FILES')"
```
> „CI grün" ≠ „Version live". Erst die echte PyPI-Version/Upload-Zeit bestätigen.

### 5. SOFORT revoken (beide Seiten) + scrubben
```bash
# a) GitHub-Secret entfernen
gh secret delete PYPI_API_TOKEN --repo "$REPO"
# b) Token server-seitig auf pypi.org LÖSCHEN (Account settings → API tokens → Remove)
#    -> Screenshot/Zeitstempel als Revocation-Proof sichern
# c) etwaige lokale Kopie vernichten
[ -f ~/.secrets/pypi_api_token_breakglass ] && shred -u ~/.secrets/pypi_api_token_breakglass
```
> Das GitHub-Secret zu löschen reicht **nicht** — der Token bleibt sonst auf PyPI
> gültig (AD-15). Beides, sofort.

### 6. Revocation-Proof ablegen
In `registry/iil-migration.yaml` beim Paket unter `verification` eine Zeile:
`breakglass: "<PKG> v<ver> via Token am <ISO-Zeit>; revoked <ISO-Zeit> (Proof: <ort>)"`.

### 7. Steady State herstellen (der eigentliche Fix)
Token war nur die Brücke. Jetzt **OIDC unter `iilgmbh` reparieren/anlegen** und den
**nächsten** Release tokenlos durch den finalen Publisher beweisen (ADR-255 Schritt 5).
Erst dann ist das Paket `done`.

---

## Recovery-Matrix für diesen Pfad (REC-11 — was bleibt, was nicht)

| Aktion | Rückgängig machbar? | Hinweis |
|---|---|---|
| GitHub-Secret gesetzt | ja | `gh secret delete` |
| Token auf PyPI erstellt | ja | server-seitig löschen = vollständig entwertet |
| **Release publiziert** | **NEIN** | PyPI erlaubt **kein** Re-Upload derselben Version; ein zurückgezogener Release-File macht die Versionsnummer dauerhaft verbrannt → bei Fehler **forward-fix** mit neuer Version, nicht „rückgängig" |
| Token-Leak (falls Kanal verletzt) | teilweise | sofort revoken; Annahme: bis Revoke konnte **nur dieses Projekt** publiziert werden (deshalb project-scoped) |

---

## Anti-Patterns (was dieses Runbook verhindert)

- ❌ Den **stehenden** `~/.secrets/pypi_api_token` als Break-Glass missbrauchen (ist
  nicht incident-scoped, oft account-weit, keine definierte Lifetime).
- ❌ **Account-weiter** Token „weil schneller".
- ❌ Token **vorab** anlegen und „bereithalten".
- ❌ Nur das GitHub-Secret löschen und den PyPI-Token leben lassen.
- ❌ „Publish lief grün" ohne die echte PyPI-Version zu prüfen.
- ❌ Break-Glass als Dauerlösung — es ist die Brücke zu OIDC, nicht der Ersatz.

---

## Festgelegte Entscheidungen (2026-06-23)

1. **Named principal** = **achimdehnert**, solange `iilgmbh` nur einen Owner hat;
   **nach** dem 2. unabhängigen Owner (REC-1) geht die Rolle auf diesen über.
   Caveat bleibt: bis dahin löst Break-Glass den Bus-Factor *nicht* — bevorzugt
   also erst nach REC-1 in Break-Glass-Lagen gehen.
2. **Secure channel** = **stdin → `gh secret set`, keine Disk-Kopie** (Schritt 2).
3. **Max lifetime** = **≤ 24 h**, Revoke direkt nach Gebrauch.
