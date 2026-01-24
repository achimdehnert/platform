📘 KI-Media-Hub – Technische Unterlagen (MVP → Produktionsbetrieb)

Version: 1.0
Status: MVP-konform, produktionsfähig erweiterbar
Zielgruppe: IT-Architektur, Entwicklung, Audit, Security
Stack: PostgreSQL · Django · HTMX · ComfyUI · Worker

1. Systemziel & Leitplanken
1.1 Ziel

Aufbau eines datenbankgetriebenen KI-Medienhubs zur Erzeugung von:

Illustrationen

Comics (Panels & Seiten)

Hörbüchern (Kapitel)

mit klarer Perspektive auf:

Serienproduktion

Mandantenfähigkeit

späteren Kundenzugriff

Auditierbarkeit & Reproduzierbarkeit

1.2 Architektur-Prinzipien (verbindlich)
Prinzip	Umsetzung
Postgres = Single Source of Truth	Alle Parameter, Presets, Jobs, Artefakte in DB
No Hardcoding	Keine festen Prompts, Modelle, Parameter im Code
Trennung Engine / Orchestrierung	ComfyUI ohne Geschäftslogik
Reproduzierbarkeit	Jeder Renderlauf vollständig rekonstruierbar
Auditfähigkeit	Input-Snapshot, Versionen, Logs
Mandantenfähig	Alles org-gebunden
2. Gesamtarchitektur (logisch)
[ Django + HTMX ]
   |
   |  (CRUD, UI, Permissions)
   v
[ PostgreSQL ]
   |
   |  (RenderJob + InputSnapshot)
   v
[ Worker / Orchestrator ]
   |
   |  (Workflow + Parameter Injection)
   v
[ ComfyUI ]
   |
   |  (Render Output)
   v
[ Storage + Asset DB ]


Wichtig:
ComfyUI kennt keine Benutzer, keine Projekte, keine Kunden.

3. Datenmodell (Kern)
3.1 Organisations- & Rollenmodell
Org
 ├─ Membership (User ↔ Role)
 ├─ Project
 │   ├─ Content (Scene, Panel, Chapter, Character)
 │   ├─ RenderJob
 │   └─ Asset


Rollen (MVP):

admin – System, Modelle, Workflows

producer – Jobs, Qualität, Freigabe

creator – Content-Erstellung

client – (später) nur Briefing & Download

4. Job-Typen (MVP – verbindlich)
Job Type	Zweck
ILLUSTRATION	Einzelbild / Serienbild
COMIC_PANEL	Charakterkonsistentes Panel
AUDIO_CHAPTER	Hörbuch-Kapitel

Diese Job-Typen sind logische Verträge und dürfen nicht ad hoc erweitert werden.

5. Workflow-Registry (ComfyUI)
5.1 WorkflowDefinition (DB)
{
  "key": "illustration_v1",
  "version": 1,
  "sha256": "<hash>",
  "comfy_json": { "...": "full comfy workflow graph" },
  "is_active": true
}


Audit-Anforderung:

Jeder Workflow ist versioniert

Hash stellt Integrität sicher

Änderungen → neue Version

5.2 WorkflowBinding
job_type	workflow_key
ILLUSTRATION	illustration_v1
COMIC_PANEL	comic_panel_v1
AUDIO_CHAPTER	audiobook_chapter_v1
6. Preset-Seed-Daten (DB-Fixtures)
6.1 StylePresets (style_preset)
[
  {
    "key": "illustration_cinematic_v1",
    "prompt_style": "cinematic illustration, high detail, dramatic lighting, coherent anatomy",
    "prompt_negative": "low quality, blurry, watermark, text, deformed anatomy",
    "defaults": {
      "steps": 30,
      "cfg": 6.5,
      "sampler": "dpmpp_2m",
      "scheduler": "karras"
    },
    "is_approved": true
  },
  {
    "key": "comic_realistic_v1",
    "prompt_style": "realistic comic style, clean ink lines, consistent characters",
    "prompt_negative": "messy lines, sketchy, distorted face, extra fingers",
    "defaults": {
      "steps": 35,
      "cfg": 6.0
    },
    "is_approved": true
  }
]

6.2 FormatPresets (format_preset)
[
  {
    "key": "square_1_1",
    "width": 1024,
    "height": 1024,
    "meta": { "dpi": 72 }
  },
  {
    "key": "comic_panel_landscape",
    "width": 1216,
    "height": 832,
    "meta": { "dpi": 72 }
  }
]

6.3 QualityPresets (quality_preset)
[
  {
    "key": "draft",
    "settings": { "steps": 20, "upscale": false }
  },
  {
    "key": "final",
    "settings": { "steps": 40, "upscale": true, "upscale_factor": 2 }
  }
]

6.4 VoicePresets (voice_preset)
[
  {
    "key": "male_deep_de_v1",
    "engine": "xtts",
    "voice_id": "male_deep_01",
    "defaults": { "speed": 1.0, "pitch": -1 },
    "is_approved": true
  }
]

7. ParameterMapping (DB-getrieben, auditfähig)
7.1 Illustration – Mapping
Source	Target	Transform
scene.location	prompt.scene_location	template
scene.mood	prompt.scene_mood	template
style.prompt_style	prompt.style	passthrough
style.prompt_negative	prompt.negative	passthrough
format.width	render.width	int
format.height	render.height	int
quality.steps	sampler.steps	override
style.defaults.cfg	sampler.cfg	default
7.2 Comic Panel – Mapping
Source	Target
panel.description	prompt.panel_description
panel.dialogue	prompt.dialogue
scene.location	prompt.scene_location
characters[].description	prompt.character_block[]
panel.camera	prompt.camera
panel.composition	prompt.composition
7.3 Audio Chapter – Mapping
Source	Target
chapter.narration	tts.narration
chapter.dialogues	tts.dialogues
voice.voice_id	tts.voice_id
voice.defaults.speed	tts.speed
8. RenderJob & Input-Snapshot (Audit-Kern!)
8.1 RenderJob
{
  "job_type": "COMIC_PANEL",
  "ref_table": "panel",
  "ref_id": 42,
  "style_preset": "comic_realistic_v1",
  "format_preset": "comic_panel_landscape",
  "quality_preset": "final",
  "status": "queued"
}

8.2 Input-Snapshot (unveränderlich!)
{
  "prompt": {
    "positive": "realistic comic style ... Alex stands in the forest ...",
    "negative": "messy lines, distorted face"
  },
  "render": {
    "width": 1216,
    "height": 832
  },
  "sampler": {
    "steps": 40,
    "cfg": 6.0,
    "sampler": "dpmpp_2m",
    "scheduler": "karras",
    "seed": 123456789
  },
  "output": {
    "path": "/assets/project_alpha/panels/",
    "filename": "project_alpha__scene01__panel03__v1.png"
  }
}


Audit-Vorteil:

Jeder Output ist 100 % rekonstruierbar

Kein implizites Wissen im Code

9. Django + HTMX – UI-Konzept (MVP)
9.1 Screens

Projekt-Dashboard

Szenen / Panels / Kapitel

Status & letzte Version

Panel-Detail

Beschreibung, Dialog, Charaktere

Dropdowns: Style / Format / Quality

HTMX-Button: „Render“

Asset-Browser

Filterbar

Preview & Download

10. Sicherheits- & Governance-Aspekte
10.1 Zugriffssteuerung

Django Permissions pro Rolle

Presets nur auswählbar, wenn is_approved = true

10.2 Mandantenfähigkeit

Alle Tabellen org-gebunden

Vorbereitung für PostgreSQL RLS

10.3 Change-Management

Workflow-Änderung = neue Version

Preset-Änderung nachvollziehbar

Assets bleiben unverändert

11. Erweiterbarkeit (nach MVP)

Video-Jobs (Frame → Clip)

Mehrsprachige Audio-Pipelines

Kundenportal (UI nur auf Presets)

Batch-Jobs / Serien

Freigabe-Workflows

12. Zusammenfassung (für IT-Architektur-Review)

✔ Postgres-first, kein Hardcoding
✔ Saubere Trennung von Engine & Business
✔ Reproduzierbar & auditfähig
✔ Mandanten- & kundenfähig vorbereitet
✔ MVP-fähig, ohne spätere Sackgassen