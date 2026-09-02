---
concept_id: KONZ-platform-056
title: Klickdummy e2e — ein Ziel-KD je Repo, ein Host, ein Vorgehen von Scout bis Konsolidierung
pipeline_status: draft
tier: T2
owner: Achim Dehnert
spec_refs: []
adr_threshold: org-weiter ADR (Revision von ADR-211, Ergänzung ADR-246/ADR-251)
review_by: 2026-10-15
kill_criteria: "Am 2026-11-30 gilt: (1) in jedem Repo mit >1 Klickdummy-Ordner gibt es genau einen Ziel-KD und eine Abdeckungsmatrix, die das Gate prüft; (2) kd.iil.pet liefert keinen Inhalt mehr, nur Umleitungen; (3) /kd-review läuft in mindestens drei Repos als CI-Job, nicht als Handaufruf. Verfehlt (1) in zwei von drei KD-Repos, war die Konsolidierung eine Einzelaktion für meiki-hub und dieses Konzept wird auf ein Repo-Runbook zurückgestuft."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "meiki-hub/docs/01-architektur/mockups/ (11 Ordner, 3 lauffähig, 6 Spec, 1 frozen)", commit_or_pr: "meiki-hub#199", opened_in_session: true}
  - {claim_id: C2, source_path: "Prod-Host 88.198.191.108 · /var/www/kd/meiki-hub (mtime 2026-07-02) · /etc/nginx/sites-enabled/kd.iil.pet.conf (location = / → 302)", commit_or_pr: "Messung 2026-09-02", opened_in_session: true}
  - {claim_id: C3, source_path: "iil-pet-portal#38, #39 (Ablösung entschieden 2026-08-23, Host-Schritte nie ausgeführt)", commit_or_pr: "iilgmbh/iil-pet-portal#39", opened_in_session: true}
  - {claim_id: C4, source_path: "~/.claude/commands/kd-scout.md:64-70 (Entscheid je Flow/Route), klickdummy.md:36-42, kd-review.md:33-38, kd-sitemap.md:14", commit_or_pr: "lokal 2026-09-02", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-251 §2 Festlegung 4 (Freigabe-Nachweis) — kein Skill schreibt/liest ihn", commit_or_pr: "lokal 2026-09-02", opened_in_session: true}
  - {claim_id: C6, source_path: "meiki-hub/scripts/check-klickdummy-manifest.py Regel 14 + specs/abdeckung.json (33 Screens: 9 gebaut, 5 teilweise, 19 offen)", commit_or_pr: "meiki-hub#200", opened_in_session: true}
  - {claim_id: C7, source_path: "meiki-hub#150 / #195 / #198: zwei Laufzeitfehler bei grünem statischem Gate (TDZ im Single-File-Build; Zuweisung ohne Persistenz)", commit_or_pr: "meiki-hub#196", opened_in_session: true}
  - {claim_id: C8, source_path: "meiki-hub Makefile:14-16 (Registry kennt 3 von 10 Ordnern), klickdummy-check.yml:5-7 (Trigger nur auf klickdummy/**)", commit_or_pr: "lokal 2026-09-02", opened_in_session: true}
created: 2026-09-02
---

# KONZ-platform-056 — Klickdummy e2e: ein Ziel-KD je Repo, ein Host, ein Vorgehen

## Fakt

In meiki-hub lagen elf Klickdummy-Ordner nebeneinander: drei lauffähig, sechs reine
Specs, einer eingefroren. Die Registry kannte drei, eine Sitemap gab es nicht, das
CI-Gate griff nur auf einen (C1, C8). Parallel führte der einprägsame Hostname
`kd.iil.pet` auf eine handkopierte Juli-Fassung eines Einzel-KDs, den der Ziel-KD
längst abgelöst hatte — die Wurzel des Hosts leitete auf genau diesen Stand um (C2).
Die Ablösung war seit dem 23.08. entschieden und nie vollzogen (C3).

Das ist kein meiki-hub-Problem. Das Vorgehen (`/kd-scout` → `/klickdummy` →
`/kd-review` → `/kd-sitemap` → Genesor) kennt nur „einen KD bauen". Es gibt keine
Übergabe zwischen den Schritten, keinen Skill für das UX-Gate aus ADR-251, keine
Antwort auf „mehrere KDs eines Repos", und „brownfield/greenfield" wird je Flow
entschieden — nicht je Modul eines Modul-KD (C4, C5).

## Analyse

Drei Ursachen, jede für sich harmlos, zusammen die Drift:

1. **Jede Anforderung bekam einen eigenen Ordner**, weil die Kette bei „Spec
   schreiben" begann und nirgends fragte, ob ein Ziel-KD existiert, in den sie gehört.
   Specs neben einem KD sind unsichtbar: niemand sieht, was davon gebaut ist.
2. **Der Bauzustand wurde statisch geprüft.** Zwei Laufzeitfehler bei grünem Gate
   (toter Single-File-Build; Zuweisung, die den Reload nicht überlebte) belegen, dass
   ein Gate, das Struktur prüft, Laufzeit nicht sieht (C7). Das Laufzeit-Werkzeug
   (`/kd-review`) ist ein Handaufruf und wird übersprungen, sobald der Bau-Output
   „I1–I3 grün" meldet.
3. **Zwei Publish-Pfade ohne Verhältnis.** Der manuelle war älter und hatte den besseren
   Namen; der automatische wuchs auf 25 Repos, ohne dass irgendwo auffiel, dass beide
   existieren (C3).

## Lösung

### L1 — Ein Ziel-KD je Repo, Specs darunter

Jedes Repo hat **genau einen** Klickdummy-Container (`klickdummy/`). Anforderungen
liegen als `klickdummy/specs/<modul>/screens-spec.yaml` **darunter**, nie daneben.
Ein zweiter lauffähiger KD im selben Repo ist ein Befund, kein Zustand — er trägt ein
Integrationsdatum oder wandert nach `docs/_archiv/`.

### L2 — Abdeckungsmatrix = brownfield/greenfield je Modul

`klickdummy/specs/abdeckung.json` sagt für jeden spezifizierten Screen, ob er im
Container **gebaut**, **teilweise** gebaut, **offen** (mit Issue) oder **verworfen**
(mit Grund) ist. Das Gate verlangt genau eine Antwort je Screen, prüft Ziel-Screens auf
Existenz und druckt die Matrix bei jedem Lauf (C6). Damit ist der Modul-Stand jederzeit
sichtbar — das, was `/kd-scout` auf Flow-Ebene beantwortet, hier auf Modul-Ebene.

| Ebene | Frage | Werkzeug |
|---|---|---|
| Flow / Route | Gibt es im Code schon eine Route? | `/kd-scout` (unverändert) |
| **Modul im Container** | **Was aus der Spec ist im Ziel-KD gebaut?** | **Abdeckungsmatrix, Gate-Regel** |
| Screen | Ist die Doppelquelle beendet? | ADR-211 I3 (unverändert) |

### L3 — Laufzeit ist Pflicht, nicht Handaufruf

Neben dem statischen Gate läuft je Container ein **Browser-Smoke in CI**
(Chromium, Shell **und** Single-File-Build, Konsole ohne unbekannte Fehler,
Positivkontrolle gegen eine präparierte Kopie). `/kd-review --no-agent` bleibt das
Werkzeug für die vertiefte Prüfung; der Smoke ist das, was jeder PR bekommt. Der
Bau-Output von `/klickdummy` meldet künftig „statisch grün — Laufzeit: Smoke/Review
ausstehend", nie „I1–I4 grün" ohne Zusatz.

### L4 — Das UX-Gate bekommt einen Ort

ADR-251 verlangt einen versionierten Freigabe-Nachweis, aber kein Skill schreibt ihn.
Künftig: `klickdummy/freigabe.json` `{kd_commit, reviewer, status, datum, uc_ids}`,
geschrieben von `/kd-review`, gelesen vom Merge-Check des Repos. Fehlt die Datei oder
zeigt sie auf einen älteren Commit, ist der Merge in den Staging-Code gesperrt.

### L5 — Ein Publish-Pfad

`iil.pet/kd/<repo>/<kd_path>/` ist der einzige Ort, an dem Klickdummies liegen.
`kd.iil.pet` ist seit 2026-09-02 eine **Umleitung** dorthin — kein Spiegel, denn nach
L1 gibt es nichts mehr zu spiegeln. `kd_path` ist überall `klickdummy/`
(meiki-hub#124 schließt die letzte Ausnahme). Handouts und Guides verlinken nur noch
den Portal-Pfad.

### L6 — Übergaben zwischen den Skills

| Von | Nach | Artefakt |
|---|---|---|
| `/kd-scout` | `/klickdummy` | `klickdummy/specs/<modul>/scout.json` (Kandidat, Klasse, Screens, Begründung) |
| `/klickdummy` | Smoke / `/kd-review` | Bau-Output mit „Laufzeit ausstehend" + CI-Job |
| `/kd-review` | Merge-Check | `klickdummy/freigabe.json` (L4) |
| jede Spec | Gate | `abdeckung.json` (L2) — Pflicht, sobald `specs/` existiert |
| jedes Repo mit >1 KD | Portal | `/kd-sitemap` Pflicht, nicht optional |

### Was sich an bestehenden Festlegungen ändert

- **ADR-211**: neue Sektion „Container und Specs" (L1, L2); I-Begriffe bleiben.
- **ADR-246**: `/kd/` als **einziger** Kontrakt; `/genesor/render/…` wird als
  Einzel-Render darunter geführt oder abgekündigt.
- **ADR-251**: Festlegung 4 wird operationalisiert (L4) statt nur gefordert.
- **ADR-216** (`staging-klickdummy.iil.pet`, proposed): zurückziehen — nie gebaut,
  von `kd.iil.pet` überholt, das seinerseits abgelöst ist.
- Skills: `klickdummy.md` (Output-Text L3, Übergabe L6), `kd-review.md`
  (`--no-agent` Default, schreibt `freigabe.json`), `kd-sitemap.md` (Pflicht ab >1 KD),
  `kd-scout.md` (schreibt `scout.json`; verweist für Modul-Ebene auf L2).

## Nicht in diesem Konzept

- Die inhaltliche Migration der Einzel-KDs in meiki-hub (Phase 2 in meiki-hub#199).
- Rückbau von `/var/www/kd` und `~/kd-serve/kd-publish.sh` (iil-pet-portal#38) —
  erst, wenn die Umleitung 30 Tage ohne Befund gelaufen ist.
- Ob `klickdummy-browser` aus dem pip-Paket neben `/kd-sitemap` bestehen bleibt.

## Kill-Kriterium

Siehe Frontmatter. Der Test ist die Flotte, nicht meiki-hub: greift L1/L2 in zwei von
drei KD-Repos nicht, war das eine Einzelaktion und kein Vorgehen.
