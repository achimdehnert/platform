# Runbook — einen Loopback-Dienst hinter Cloudflare Access veröffentlichen

**Stand 2026-07-30 · Erstanwendung** `mail.iil.pet` (Mail-Link-Dienst)
**Verwandt** `docs.iil.pet` (Paperless, platform#1528) — dort dasselbe Muster, aber
mit `HTTP_REMOTE_USER`-Durchreichung; hier ohne, weil der Dienst keine Nutzer kennt.

## Wann nutzen

Ein Dienst lauscht bewusst nur auf `127.0.0.1` und soll trotzdem vom Browser aus
erreichbar sein — ohne offenen Port, ohne SSH-Tunnel auf dem Endgerät.

**Wann nicht:** wenn der Dienst selbst Nutzer und Rechte kennt. Dann ist Access
eine zweite Tür, nicht die Tür, und die Frage ist eine andere.

## Voraussetzungen

- `~/.secrets/cloudflare_write_token` — kann DNS, Tunnel **und** Access.
  `cloudflare_api_token` reicht **nicht**: DNS gibt dort 403. Und
  `/user/tokens/verify` ist der falsche Test, konto-gebundene Token antworten
  dort immer 401 — funktional gegen `/zones` bzw. `/accounts/<id>/access/apps` prüfen.
- `cloudflared` auf der Maschine, auf der der Dienst läuft.
- Klarheit darüber, **was hinter der Tür liegt**: wer Access besteht, kann alles,
  was der Dienst kann. Bei `mail.iil.pet` ist das Lesezugriff auf ein ganzes Postfach.

## Reihenfolge — und warum sie genau so ist

```
1. Access-Anwendung + Richtlinie anlegen
2. Tunnel anlegen + DNS-CNAME setzen        (Tunnel läuft noch NICHT)
3. Warten, bis Access nachweislich abweist  ← der Schritt, der beim ersten Mal fehlte
4. Tunnel starten, dann gegenprüfen
```

**Schritt 3 ist nicht Vorsicht, sondern Erfahrung.** Am 2026-07-30 war die
Access-Anwendung angelegt, der Tunnel aber schon gestartet — und der Host
antwortete mit **HTTP 200 ohne Anmeldung**. Die Anwendung existierte, ihre
Durchsetzung war noch nicht propagiert (Fenster rund 20 Sekunden).

> **Access angelegt ist nicht Access durchgesetzt.**

Solange kein Tunnel läuft, gibt es keinen Ursprung: eine 200 in Schritt 3 kann
dann nur bedeuten, dass etwas anderes auf dem Namen antwortet — Abbruch, nicht
weitermachen. Und eine 302 in Schritt 3 beweist die Durchsetzung, bevor überhaupt
etwas zu holen wäre.

## Skript

`tools/cf_access/veroeffentlichen.sh` (dieses Repo) macht 1–4 in dieser Reihenfolge
und bricht ab, statt einen offenen Host stehen zu lassen. Parameter über Umgebung:
`HOST`, `UNIT`, `PORT`.

## Access-Richtlinie — die Identitäts-Falle

Das Zero-Trust-Konto hat genau **einen** Identitäts-Anbieter: GitHub. Einmal-PIN
ist **nicht** eingerichtet. Cloudflare reicht deshalb die E-Mail des GitHub-Kontos
weiter — und das ist `admin@wir-digital.de`, nicht `achim.dehnert@iil.gmbh`.

**Eine Richtlinie ohne `admin@wir-digital.de` sperrt den Owner aus.** Die zweite
Adresse gehört trotzdem hinein, für den Fall, dass die primäre GitHub-Adresse
umgestellt wird (das wirkt dann auf **alle** Access-Anwendungen — vorher deren
Richtlinien durchsehen).

Der Endpunkt `access/identity_providers` ist nur mit dem Write-Token lesbar; mit
dem kleineren Token kommt ein Berechtigungsfehler, der wie eine **leere Liste**
aussieht. Fehlschlag ≠ leere Liste.

## Eigener Tunnel, nicht der Prod-Tunnel

`bf-platform` bedient rund 40 Hostnamen aus einer root-Config. Ein Tippfehler dort
nimmt alles mit. Für einen zusätzlichen Dienst darum ein **eigener** Tunnel im
User-Kontext, mit eigener Unit neben dem Dienst:

```yaml
tunnel: <id>
credentials-file: ~/.cloudflared/<name>.json   # 0600
ingress:
  - hostname: <host>
    service: http://127.0.0.1:<port>
  - service: http_status:404                     # alles andere prallt ab
```

Die Unit-Härtung bleibt **sparsam**: `PrivateTmp`, `ProtectKernelTunables` und
`ProtectControlGroups` remounten `/proc` und haben in dieser Unit-Familie schon
einmal die Port-Diagnose blind gemacht (platform#1538). `NoNewPrivileges` und
`RestrictSUIDSGID` sind geprüft und genügen.

## Bekannte Fehler

| Symptom | Ursache | Fix |
|---|---|---|
| 200 ohne Anmeldung, kurz nach dem Anlegen | Durchsetzung noch nicht propagiert | Tunnel stoppen, warten bis 302, dann starten |
| 200 ohne Anmeldung, dauerhaft | Richtlinie fehlt oder Anwendung auf falschem Namen | `access/apps` auflisten, `domain` gegen den Hostnamen prüfen |
| 403 beim DNS-Schreiben | falsches Token | `cloudflare_write_token` nehmen |
| 530 | DNS zeigt auf den Tunnel, der Tunnel läuft nicht | Unit starten |
| Anmeldung führt ins Leere | Owner-Adresse nicht in der Richtlinie | `admin@wir-digital.de` ergänzen |

## Rückweg

`systemctl --user stop <unit>` nimmt den Host binnen Sekunden vom Netz — der
Dienst selbst läuft weiter und ist über Loopback/SSH-Tunnel unverändert erreichbar.
Das ist der schnellste Rückweg und braucht keinen API-Zugriff. Danach in Ruhe:
DNS-Eintrag löschen, Access-Anwendung löschen, Tunnel löschen.

## Variante: der Dienst läuft auf einer **anderen** Maschine (Gegenstelle)

**Erstanwendung** `gpu.iil.pet` (ollama auf der GPU-Box, 2026-09-02, platform#2486
Punkt 2).

Der Normalfall oben setzt voraus, dass Dienst und Tunnel auf derselben Maschine
liegen. Das trifft nicht zu, wenn der Dienst auf einem Gerät läuft, das selbst
keinen Ingress haben soll oder darf — eine Box im Heimnetz, ein Knoten hinter
wg0, ein Gerät, das nur auf Zuruf läuft. Dann läuft der Tunnel auf dem **Gateway**
(prod) und zeigt über das private Netz auf den Dienst.

```bash
HOST=gpu.iil.pet PORT=11434 ORIGIN=10.99.0.2:11434 TUNNEL_NAME=gpu \
  python3 tools/cf_access/tunnel_anlegen.py
```

`ORIGIN` ist seit diesem Lauf ein Parameter; ohne ihn bleibt es bei
`127.0.0.1:PORT`. Die erzeugte Config wird auf das Gateway kopiert, dort mit dem
Pfad der Zugangsdatei **dieser** Maschine, und als **System**-Unit betrieben —
`systemctl --user` aus dem Skript passt nur für den lokalen Fall:

```
/root/.cloudflared/<name>.json    # Zugangsdatei, Modus 0600, nie ausgeben
/root/.cloudflared/<name>.yml     # credentials-file zeigt auf DIESEN Pfad
/etc/systemd/system/cloudflared-<name>.service
```

**Drei Dinge, die diese Variante anders macht:**

1. **Der Schritt-3-Beweis bleibt gültig, der Schritt-4-Beweis nicht ganz.** Die
   Abweisung (302) misst man wie immer von außen. Dass der *Ursprung* erreichbar
   ist, misst man dagegen **auf dem Gateway** (`curl http://<origin>/`) — von
   außen kommt man an Access nicht vorbei und sieht deshalb nie, ob dahinter
   überhaupt jemand antwortet. Ein 502 nach erfolgreicher Anmeldung ist der
   späte, teure Weg, das herauszufinden.
2. **Ein schlafendes Gerät ist kein Ausfall.** Läuft die Maschine nur auf Zuruf,
   braucht der Eintrag in `infra/ports.yaml` einen `betriebsstatus` mit Grund,
   sonst meldet Phase `0.7.11 erreichbarkeit` den Namen in jeder Sitzung als tot.
3. **Die Auflage des Ziel-Knotens gilt weiter.** Trägt er
   `oeffentlicher_ingress: false`, ist der veröffentlichte Name eine
   **Ausnahme** im Sinne von `docs/runbooks/neuer-knoten.md` und braucht `grund`,
   `entschieden` und `bis` — auch dann, wenn der offene Port formal auf dem
   Gateway liegt und nicht auf dem Gerät.

**Was die Variante nicht leistet:** Sie schützt den Weg von außen, nicht den Weg
innen. Wer im privaten Netz steht, erreicht den Dienst weiterhin direkt und ohne
Anmeldung. Wenn auch das zugehen soll, gehört die Anmeldung an den Dienst selbst
oder ein Proxy auf das Gerät — das ist eine andere Entscheidung mit anderen
Kosten, und sie gehört benannt statt stillschweigend mitgemeint.
