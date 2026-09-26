# Runbook — Outline-Login von authentik auf Cloudflare Access for SaaS umstellen

**Stand 2026-09-23 · Bezug** [platform#3256](https://github.com/achimdehnert/platform/issues/3256),
[ADR-307](../adr/ADR-307-identitaet-cloudflare-access-statt-authentik.md) §3 Klasse 3 („Fremd-Werkzeuge ohne lokales Login“)
**Verwandt** [`loopback-dienst-hinter-cloudflare-access.md`](loopback-dienst-hinter-cloudflare-access.md) (Token, Identitäts-Falle)

## Worum es geht

Outline (`knowledge.iil.pet`, Container `iil_knowledge_outline` auf `hetzner-prod`) kennt
kein lokales Login. Sein einziger Auth-Provider ist `oidc`, heute gegen authentik (`id.iil.pet`).
Ziel: dieselbe OIDC-Schnittstelle, aber Cloudflare Access als Provider („Access for SaaS“).
Danach hängt Outline nicht mehr an authentik.

**Nicht betroffen:** API-Tokens (Outline-MCP, REST). Sie laufen über die
Service-Token-Richtlinie der vorgeschalteten Access-App und Outlines eigene API-Keys,
nicht über den Web-Login.

## Ist-Zustand (gemessen 2026-09-23, nur lesend)

| Punkt | Befund |
|---|---|
| Deployment | Compose-Stack im Verzeichnis aus dem Container-Label `com.docker.compose.project.working_dir` (`/opt/outline`), Datei `docker-compose.yml`, Secrets in `.env` daneben (root, 0600) |
| Woher die OIDC-Werte kommen | `OIDC_AUTH_URI`, `OIDC_TOKEN_URI`, `OIDC_USERINFO_URI`, `OIDC_DISPLAY_NAME`, `OIDC_SCOPES`, `OIDC_USERNAME_CLAIM` stehen **literal in der Compose-Datei**; `OIDC_CLIENT_ID`/`OIDC_CLIENT_SECRET` werden aus `.env` (`OUTLINE_OIDC_CLIENT_ID`, `OUTLINE_OIDC_CLIENT_SECRET`) interpoliert |
| Version | Host läuft `outlinewiki/outline:1.6.0`; die Repo-Kopie (`deployment/stacks/outline/`) nennt `1.10.1` und weicht auch sonst ab (Netz `shared_auth`, Logging). **Host ist maßgeblich**, die Umstellung ändert nur OIDC-Zeilen, keinen Image-Tag |
| OIDC in 1.6.0 | unterstützt `OIDC_ISSUER_URL` (Discovery) und explizite Endpunkte; E-Mail aus `profile.email` oder `id_token` ist Pflicht; Name = `name` → `OIDC_USERNAME_CLAIM` → `username` |
| Callback | `https://knowledge.iil.pet/auth/oidc.callback` |
| Nutzer | 2 Konten, beide aktiv: 1 **admin** (Domain `iil.pet`), 1 member (Domain `dehnert.team`); `inviteRequired=false`, 0 erlaubte Domains |
| Vorgeschaltete Access-App | `knowledge.iil.pet` ist bereits `self_hosted` hinter Access: Owner-Richtlinie (drei E-Mails, Domains `dehnert.team`, `iil.gmbh`, `wir-digital.de`), Service-Token-Richtlinie für den MCP; einziger IdP GitHub |
| Ausgang | Container erreicht `*.cloudflareaccess.com` per HTTPS |

## ⚠️ Vorbedingung: die E-Mail muss passen

Outline ordnet einen neuen OIDC-Login dem bestehenden Konto **über die E-Mail** zu
(`userProvisioner`: `sub` unbekannt → Suche nach E-Mail, case-insensitiv → neue
Authentifizierung am vorhandenen Konto). Findet es keine passende E-Mail, legt es wegen
`inviteRequired=false` und leerer Domain-Liste **ein neues, leeres Konto** mit Standardrolle an.

Gemessen: Das **Admin-Konto (Domain `iil.pet`) steht in keiner Access-Richtlinie**, und der
GitHub-IdP meldet in den Access-Logs Adressen der Domains `iil.gmbh` (6×) und
`wir-digital.de` (1×). Nur das member-Konto (`dehnert.team`) ist wortgleich in der
Owner-Richtlinie. **Ohne Schritt 0 landet der Owner nach der Umstellung nicht im Admin-Konto.**

Schritt 0 — eine der beiden Varianten, Owner-Entscheid:

- **A (empfohlen):** Die E-Mail des Outline-Admin-Kontos auf die Adresse setzen, die
  Cloudflare meldet (GitHub-Login, Domain `iil.gmbh`). Vorher DB-Dump (`backup.sh` bzw.
  `pg_dump`), dann eine einzige `UPDATE users SET email=… WHERE id=…` im Container
  `iil_knowledge_outline_db`. Rückweg: dieselbe Zeile mit der alten Adresse.
- **B:** In der SaaS-App zusätzlich den IdP „Einmal-PIN“ zulassen und die `iil.pet`-Adresse
  in deren Richtlinie aufnehmen. Voraussetzung: Das Postfach dieser Adresse empfängt Mails.

## Schritt 1 — Access-SaaS-App anlegen (erledigt 2026-09-23)

Per API (`~/.secrets/cloudflare_write_token`, wie `tools/cf_access/access_anlegen.py`):

```
POST /accounts/<konto>/access/apps
{ "type": "saas",
  "name": "knowledge.iil.pet — Outline OIDC (SaaS)",
  "allowed_idps": <wie die knowledge.iil.pet-App>,
  "saas_app": { "auth_type": "oidc",
                "redirect_uris": ["https://knowledge.iil.pet/auth/oidc.callback"],
                "grant_types": ["authorization_code"],
                "scopes": ["openid", "email", "profile"] },
  "policies": [ <Owner-Richtlinie der knowledge.iil.pet-App, include kopiert> ] }
```

Das `client_secret` kommt nur in der Antwort auf das Anlegen. Abgelegt in
`~/.secrets/outline_cf_oidc_client_id` und `~/.secrets/outline_cf_oidc_client_secret`
(roher Wert, 0600), nie ausgegeben.

Endpunkte (Discovery geprüft, `issuer` stimmt mit der konstruierten URL überein):

| Variable | Wert |
|---|---|
| Issuer | `https://<team>.cloudflareaccess.com/cdn-cgi/access/sso/oidc/<client_id>` |
| `OIDC_AUTH_URI` | `<issuer>/authorization` |
| `OIDC_TOKEN_URI` | `<issuer>/token` |
| `OIDC_USERINFO_URI` | `<issuer>/userinfo` |

`<team>` = `auth_domain` aus `GET /accounts/<konto>/access/organizations`.

Dashboard-Weg, falls nötig: Zero Trust → Access → Applications → Add → SaaS →
„Generic OIDC“ (Protocol OIDC), Redirect-URL wie oben, Scopes `openid email profile`,
Richtlinie wie bei `knowledge.iil.pet`.

## Schritt 2 — Umstellung (Prod, braucht Schritt 0)

Auf `hetzner-prod`, im Compose-Verzeichnis des Stacks:

1. **Sichern:** `cp -p docker-compose.yml docker-compose.yml.bak-<datum>` und
   `cp -p .env .env.bak-<datum>` (Rechte bleiben 0600).
2. **`.env`:** `OUTLINE_OIDC_CLIENT_ID` und `OUTLINE_OIDC_CLIENT_SECRET` auf die Werte aus
   den beiden neuen Secret-Dateien setzen (per `scp`/Editor, nie per `echo` im Terminal).
3. **`docker-compose.yml`**, nur diese Zeilen:

   | Variable | neu |
   |---|---|
   | `OIDC_AUTH_URI` | `<issuer>/authorization` |
   | `OIDC_TOKEN_URI` | `<issuer>/token` |
   | `OIDC_USERINFO_URI` | `<issuer>/userinfo` |
   | `OIDC_DISPLAY_NAME` | `Cloudflare Login` |
   | `OIDC_USERNAME_CLAIM` | `email` (Cloudflare liefert kein `preferred_username`; `email` ist immer da und reicht als Namens-Rückfall) |

   `OIDC_SCOPES` bleibt `openid profile email`. `extra_hosts: id.iil.pet` und
   `NODE_TLS_REJECT_UNAUTHORIZED` bleiben vorerst stehen (Aufräumen: Schritt 5).
4. **Neu erzeugen:** `docker compose up -d outline` (nur dieser Dienst; DB und Redis bleiben).
5. Warten bis `docker inspect -f '{{.State.Health.Status}}' iil_knowledge_outline` = `healthy`.

Der bestehende Provider-Eintrag (`authentication_providers`, Name `oidc`) wird
weiterverwendet — Outline sucht ihn je Team, nicht je Aussteller.

## Schritt 3 — Abnahme

1. **Privates Fenster**, `https://knowledge.iil.pet` → Cloudflare-Anmeldung → Outline-Startseite
   → „Cloudflare Login“ → der Owner landet im **Admin-Konto** (Einstellungen → Rolle „Admin“,
   vorhandene Sammlungen sichtbar). Die bestehende Session im Hauptfenster bleibt davon unberührt.
2. DB-Gegenprobe: Das Admin-Konto hat jetzt **2** Einträge in `user_authentications`;
   Anzahl `users` ist unverändert **2** (kein Zufallskonto entstanden).
3. API-Token-Gegenprobe: ein Outline-MCP-Aufruf bzw. `POST /api/auth.info` mit dem
   API-Token → 200.
4. Ergebnis als Kommentar in #3256.

## Rollback

Auslöser: Login schlägt fehl, falsches Konto, Container nicht healthy.

```
cp -p docker-compose.yml.bak-<datum> docker-compose.yml
cp -p .env.bak-<datum> .env
docker compose up -d outline
```

authentik läuft bis zur Abnahme weiter, der alte Login ist damit sofort wieder da.
Entstand ein falsches Konto, dieses in Outline sperren (nicht löschen).
Schritt 0 Variante A zurück: alte E-Mail per `UPDATE` wiederherstellen.

## Schritt 4 — danach: authentik stilllegen

Nicht Teil dieses Runbooks, Reihenfolge laut #3256 / ADR-307 §4.1 Schritt 5:
erst wenn **keine** Anwendung mehr auf `id.iil.pet` leitet (offen u.a. dev-hub, writing-hub,
Grafana, doc-hub) → DB-Dump sichern, Container stoppen (nicht löschen), 14 Tage Cooling-off,
dann den Stack `deployment/stacks/authentik` entfernen und `id.iil.pet` aus DNS/`infra/ports.yaml`.

## Schritt 5 — Aufräumen in Outline

- `extra_hosts: id.iil.pet` und `NODE_TLS_REJECT_UNAUTHORIZED=0` entfernen (Letzteres schaltet
  die TLS-Prüfung für **alle** ausgehenden Aufrufe ab; es war nur für authentik über den
  Host-Nginx nötig) — eigener Schritt mit eigener Abnahme.
- Repo-Kopie `deployment/stacks/outline/docker-compose.yml` an den Host angleichen
  (Version, Netze, OIDC-Zeilen) — die Drift ist heute schon da.
