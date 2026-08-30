# Runbook: Einen neuen Knoten in die Flotte aufnehmen

> Stand 2026-08-30 (KONZ-platform-054, E5). Gilt für jede Maschine, die in
> `infra/hosts.yaml` erscheinen soll — Cloud-Server, Owner-Hardware, alles. Der
> erste Knoten nach diesem Runbook ist der **GX10** (KONZ-platform-053).

## Warum es dieses Runbook braucht

Bis heute war jede Aufnahme eine Bastelei, und die Spuren stehen in der SSoT selbst:
ein Runner mit `host: UNKNOWN`, ein `dead_label_refs:`-Block für Workflows, die auf
tote Label zeigten, ein `hostname: TBD` ohne Frist, und Auflagen („keine
Bürgerdaten", „kein Runner"), die als Fließtext im Feld `role:` standen — lesbar für
Menschen, unsichtbar für jedes Werkzeug. Der Audit (`hosts_audit.py`) übersprang
`verified: false` kommentarlos; ein Eintrag durfte unbegrenzt unvermessen bleiben,
während der Check grün meldete.

Ein Knoten ist erst dann Teil der Flotte, wenn die vier Fragen unten maschinell
beantwortet sind. Vorher ist er eine Maschine, die zufällig im selben Netz hängt.

## Die vier Fragen, die ein Knoten beantworten muss

| Frage | Feld in `hosts.yaml` | Wer liest es |
|---|---|---|
| Wie erreiche ich ihn? | `ip`, `ssh` (User@IP), optional `ssh_alias` | `reconcile_registry_live.py`, `speicher_melder.py`, `backup_deckung.py`, `deploy_wirkung.py`, `origin_tls_melder.py` |
| Was darf dort laufen — und was nicht? | `auflage:` (Block, s. u.) | `hosts_audit.py --check auflage`, später der Live-Abgleich |
| Welche Architektur? | `arch:` | `hosts_audit.py` (Runner auf Nicht-amd64 = Befund) |
| Wann wurde er zuletzt gemessen? | `verified: <Datum>` — oder `verified: false` **mit** `verified_bis: <Datum>` | `hosts_audit.py --check staleness` |

## Reihenfolge — nicht umsortieren

Die Reihenfolge ist Absicht: erst die Deklaration, dann der Zugang, dann die
Messung, dann erst Ingress und Runner. Wer den Runner zuerst registriert, hat einen
Knoten in der Flotte, den kein Werkzeug kennt — genau der Zustand, den dieses
Runbook beenden soll.

### 1. Eintrag in `infra/hosts.yaml` anlegen

Pflichtfelder von Anfang an, auch wenn das Gerät noch nicht angeschaltet ist:

```yaml
  <name>:
    hostname: <OS-Hostname oder TBD>
    provider: <Hetzner (nbg1) | netcup | owner-hardware | …>
    server_type: <cpx42 | gx10 | …>
    arch: <amd64 | aarch64>
    os: <…>
    status: geplant                  # nur bis zur ersten Messung
    role: >
      <Was der Knoten TUT — kein Verbot hier hinein, dafür ist `auflage` da>
    auflage:
      datenklassen_verboten: [gov-sozialdaten]   # oder weglassen = erlaubt
      prod_container: false                      # oder weglassen = erlaubt
      app_hubs: false
      runner: false
      oeffentlicher_ingress: false
      nur_dienste: [risk-hub, frist-hub]         # Whitelist, nur wenn Lane G
      grund: "<KONZ-/ADR-Nummer oder Owner-Entscheid mit Datum>"
    hosts_runners: []
    verified: false
    verified_bis: <heute + 30 Tage>
```

Jedes Feld im `auflage:`-Block ist optional; fehlt es, gilt „erlaubt". `grund` ist
Pflicht, sobald der Block existiert. Das Vokabular für `datenklassen_verboten` ist
fest (`gov-sozialdaten`, `personenbezogen`); ein anderer Wert ist ein Schema-Fehler,
kein neuer Begriff.

**Was `auflage` heute prüft und was nicht:** `hosts_audit.py --check auflage`
vergleicht die Auflage mit der **Deklaration** in `ports.yaml` (`prod_host`,
`betriebsstatus`, `datenklasse`). Ob ein Container tatsächlich gegen die Auflage
läuft, sieht nur der Live-Abgleich am Knoten (KONZ-054 E2/E3). Ein grüner
Auflage-Check heißt „die Deklaration widerspricht sich nicht", nicht mehr.

Dann: `python3 infra/scripts/hosts_audit.py --check all --workflows .github/workflows`
— muss grün sein, **bevor** der PR aufgeht. Ein `verified: false` ohne Frist ist
jetzt ein Finding, kein Freifahrtschein.

### 2. Zugang herstellen und hinterlegen

- Schlüssel auf dem Knoten hinterlegen; `ssh` und `ip` in `hosts.yaml` eintragen.
- Knoten hinter `wg0` (GPU-Box, GX10): der Weg führt über den prod-Hop. In
  `hosts.yaml` steht dann `ssh: <user>@<wg0-IP>` **und** ein Satz im `role:`-Feld,
  über welchen Hop. Das Werkzeug muss den Hop kennen, sonst meldet es „unerreichbar"
  und zählt den Knoten stillschweigend nicht (Diabolus-Befund zu KONZ-054: 2 von 8
  Knoten hatten kein `ssh`-Feld).
- Kein `PasswordAuthentication`. Der Befund auf prod-b (50.983 Fehlversuche in 7
  Tagen) ist der Grund.

### 3. Erste Messung — und `verified` setzen

```bash
python3 infra/scripts/server_probe.py --host <ip>
python3 tools/reconcile_registry_live.py        # muss den Knoten erreichen, nicht ueberspringen
python3 tools/speicher_melder.py --nur <name>   # erster Tagespunkt fuer die Zeitreihe
```

Erst wenn alle drei den Knoten **erreicht** haben: `verified: <heute>` setzen,
`verified_bis` und `status: geplant` entfernen. Ein Knoten, den `reconcile` mit
„unerreichbar" quittiert, ist nicht aufgenommen — auch wenn `ssh` von Hand geht.

### 4. Backup und Wiederanlauf entscheiden

Vor dem ersten Workload steht die Antwort auf zwei Fragen in `hosts.yaml` (im
`role:`-Feld) oder in ADR-241:

- Was auf diesem Knoten wird gesichert, wohin, wie oft? „Nichts" ist eine gültige
  Antwort — aber eine ausgesprochene.
- Wie kommt der Knoten von Null wieder hoch? Für Owner-Hardware ohne IaC: welche
  Konfigurationsdateien liegen wo.

Der Anlass: 689 Snapshots im Bestand, keiner sichert `/etc` oder `/opt`.

### 5. Ingress — nur wenn `auflage.oeffentlicher_ingress` nicht `false` ist

Kein Cloudflare-Tunnel, kein öffentlicher vhost auf einen Knoten, dessen Auflage
das ausschließt. Der Fehler von `ollama.iil.pet` (öffentlicher Tunnel auf einen
LAN-Host mit unauthentifiziertem Endpunkt) ist der Grund für das Feld.

Wer Ingress einrichtet, trägt den Namen in `ports.yaml` (`domain_prod` /
`domain_aliases`) ein — sonst kennt der Erreichbarkeits-Melder ihn nicht.

### 6. Runner — nur wenn `auflage.runner` nicht `false` ist, und nie zuerst

- Erst nach Schritt 3. Ein Runner auf einem unvermessenen Knoten ist ein Runner,
  den kein Werkzeug sieht.
- Eintrag unter `runners:` **und** `hosts_runners:` am Host — beides, sonst
  meldet der Schema-Check.
- Auf einem Nicht-amd64-Knoten (`arch: aarch64`) ist ein Runner ein Finding: die
  Flotten-Images sind amd64. Ausnahme nur repo-scoped mit eigenem Label
  (KONZ-053 §6, Phase 2) — und der Grund gehört in den Runner-Eintrag.
- Der Runner-User gehört **nicht** in die Gruppe `docker`, wenn er es nicht
  zwingend braucht (Befund netcup: `github-ci` root-äquivalent auf dem Backup-Host).

### 7. Abnahme

Der Knoten ist aufgenommen, wenn dieses Kommando grün ist **und** der Knoten in
der Ausgabe von `reconcile_registry_live.py` als erreicht erscheint:

```bash
python3 infra/scripts/hosts_audit.py --check all --workflows .github/workflows
```

Brauchte einer der Schritte eine Sonderregel, die hier nicht steht, ist das ein
Befund gegen dieses Runbook — als Issue, nicht als stiller Zusatz im `role:`-Feld.

## Was dieses Runbook nicht regelt

- Ob ein Knoten überhaupt beschafft wird (Owner, ggf. ADR).
- Die AVV-Frage bei Fremdanbietern (netcup: offen, ADR-289).
- Den Live-Abgleich Workload gegen Auflage — das ist KONZ-054 E2/E3.
