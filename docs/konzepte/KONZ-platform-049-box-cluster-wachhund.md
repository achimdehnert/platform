---
concept_id: KONZ-platform-049
title: "Box-Cluster-Wachhund — die GPU-Box verhaltensbasiert ueberwachen"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "kein ADR — Melder nach Befund-Journal-Muster; Architektur (Lease-Arbiter) liegt bereits in ADR-296"
review_by: 2026-11-19
kill_criteria: >
  Wenn die Box vom Dev-Host in weniger als 95 Prozent der Laeufe technisch
  erreichbar ist (Tunnel flappt), misst der Melder das Netz statt die Box —
  dann zuerst den Tunnel stabilisieren oder das Konzept verwerfen, statt
  Alarm-Rauschen zu erzeugen.
---

# KONZ-platform-049: Box-Cluster-Wachhund

**Status:** Entwurf · **Datum:** 2026-08-19 · **Anlass:** LLM-Readiness-Audit —
drei Repos teilen eine unueberwachte physische GPU-Box · **Groesse:** T2

## Das Problem

Drei aktive Repos haengen an **einer physischen Windows-Box** (RTX 4090):

| Dienst | Port | gehoert zu | Zweck |
|---|---|---|---|
| ACE-Step (v1/1.5) | box-lokal | music-lab | Song-Generierung |
| MOSS-TTS | box-lokal | music-lab | Sprachsynthese |
| ComfyUI | 8000 | illustration-hub | Bild-Rendering (Primaer-Provider!) |
| Ollama | 11434 | writing-hub | lokale Textmodelle (qwen 27b) |
| Fernbedienungs-Dienst | box-lokal | music-lab | Remote-Steuerung |

Die Box ist damit faktisch ein **Prod-System** (illustration-hub rendert
primaer ueber ComfyUI; faellt sie aus, faellt der Dienst still auf den
**bezahlten** fal.ai-Pfad zurueck — genau der Vorfall, der im
illustration-hub-CHANGELOG dokumentiert ist). Ueberwacht wird sie aber nur
**pull-basiert und manuell**: `scripts/box/gpu-wachhund.sh` (music-lab)
laeuft, wenn jemand eine Sitzung beginnt. Zwischen zwei Sitzungen ist die
Box blind.

## Der Praezedenzfall

wedding-hub war **6–7 Tage tot**, waehrend Registry und Tunnel-Route
uebereinstimmten — wer Deklarationen vergleicht, sieht einen konsistenten
Zustand ([#2058](https://github.com/achimdehnert/platform/issues/2058),
Punkt 3; Wurzel KONZ-015). Die Box ist derselbe Fall eine Ebene tiefer:
liegengebliebene Song-Laeufe halten real 12,4 GB VRAM (gemessener
music-lab-Befund), und kein Deklarations-Check der Welt sieht das.

## Der Kernsatz

> Der Wachhund fragt einmal taeglich das **Verhalten** ab — echte Endpoints,
> echter VRAM — nicht die Deklaration. Er ist read-only und repariert nichts.

## Mechanik (Minimalschnitt)

Zeitgesteuerter Lauf auf dem Dev-Host (systemd-Timer; WireGuard-Route
existiert), ein Skript, vier Fragen:

1. **Erreichbarkeit je Dienst:** Ollama `GET /api/tags`, ComfyUI
   `GET /system_stats`, ACE-Step/TTS/Fernbedienung per TCP-Probe auf die
   bekannten Ports (Portliste aus music-lab `box-setup/`, kuenftig aus der
   Registry — music-lab ist seit PR #2109 eingetragen).
2. **VRAM-Anomalie:** > 8 GB belegt ohne laufenden bekannten Job
   (Schwelle und Logik aus `gpu-wachhund.sh` uebernehmen — das Skript
   existiert und ist gut, es fehlt nur der Timer und der Leser).
3. **Liegengebliebene Laeufe:** Song-/Render-Prozesse aelter als N Stunden.
4. **Zustandswechsel-Erkennung:** Alarm (orchestrator `discord_notify`)
   **nur** bei Wechsel gruen→rot oder rot→gruen, sonst nur Journal-Zeile —
   kein taegliches Rauschen.

Ausgabe ins Befund-Journal (mit Alter, wie ueblich); der session-start-Runner
zeigt den letzten Stand als eigene Zeile.

## Verhaeltnis zu #2058 Punkt 3 (WICHTIG — kein stilles Absorbieren)

#2058 Punkt 3 (Verhaltens-Melder fuer **Tunnel-Ziele**, Owner-Freigabe liegt
vor, eigene Sitzung vorgesehen) ist das **Schwester-Konzept mit derselben
Bauart**: taeglich anfragen statt Deklarationen vergleichen. Vorschlag:
**eine** Implementierung mit zwei Ziel-Sets (Cloudflare-Tunnel-Ziele +
Box-Dienste), damit nicht zwei Melder mit zwei Journalen entstehen. Die
Entscheidung, ob #2058-P3 und dieses Konzept zusammen oder getrennt gebaut
werden, ist ausdruecklich **offen und Owner-Sache** — dieses Konzept nimmt
die #2058-Freigabe nicht in Anspruch.

## Was der Wachhund NICHT tut

- **Kein Auto-Fix** (kein Modell entladen, kein Prozess killen, kein
  Neustart) — Cloud-/Cron-Routinen bleiben read-only; Eingriff ist
  Sitzungs-Arbeit mit Mensch.
- **Kein Ersatz** fuer den ADR-296-Lease-Arbiter (der koordiniert Zugriffe,
  der Wachhund beobachtet Zustand).
- **Keine Windows-seitige Installation** im ersten Schnitt — alles vom
  Dev-Host aus ueber die bestehenden Endpoints; erst wenn das nicht reicht,
  ueber einen Box-seitigen Exporter nachdenken.

## Offene Fragen an den Owner

1. Zusammenlegen mit #2058 Punkt 3 (ein Melder, zwei Ziel-Sets) — ja/nein?
2. Alarm-Kanal: Discord (existiert im Orchestrator) oder Mail-Draft?
3. Wo lebt das Skript: music-lab (nah an gpu-wachhund.sh) oder platform
   (fleet-Sicht, ein Journal)? (Vorschlag: platform, Logik-Import aus dem
   erprobten gpu-wachhund.sh.)
