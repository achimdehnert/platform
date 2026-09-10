# Dienst-Inventar (platform#3011, Kriterium 1)

Repos geprueft: 63 · fehlt (nicht ausgecheckt): — · archiviert (nicht gescannt): adr-doctor, bfagent, onboarding-hub, recruiting-hub, testkit, wedding-hub · Funde: 1575 · Schutzbegriffe: maskiert (4 Felder)

| Repo | toolkit | mgmt | mcp | service | modell | Summe |
|---|---|---|---|---|---|---|
| 137-hub | 0 | 5 | 0 | 11 | 0 | 16 |
| aifw | 0 | 8 | 0 | 0 | 0 | 8 |
| apo-hub | 0 | 4 | 0 | 13 | 0 | 17 |
| ausschreibungs-hub | 0 | 19 | 0 | 67 | 0 | 86 |
| bahn-hub | 0 | 0 | 0 | 6 | 0 | 6 |
| billing-hub | 0 | 3 | 0 | 19 | 0 | 22 |
| cad-hub | 1 | 4 | 0 | 52 | 0 | 57 |
| coach-hub | 0 | 6 | 0 | 77 | 0 | 83 |
| dev-hub | 0 | 36 | 0 | 127 | 0 | 163 |
| django-lms-lite | 0 | 0 | 0 | 7 | 0 | 7 |
| dms-hub | 0 | 1 | 0 | 15 | 0 | 16 |
| frist-hub | 0 | 2 | 0 | 11 | 0 | 13 |
| ifc-mcp | 0 | 0 | 0 | 4 | 0 | 4 |
| iil-adrfw | 0 | 0 | 12 | 0 | 0 | 12 |
| iil-assist-core | 0 | 0 | 0 | 0 | 3 | 3 |
| iil-codeguard | 0 | 0 | 3 | 0 | 0 | 3 |
| iil-doc-templates | 0 | 0 | 0 | 13 | 0 | 13 |
| iil-voice-agent | 0 | 0 | 8 | 0 | 0 | 8 |
| illustration-hub | 0 | 28 | 0 | 18 | 0 | 46 |
| learn-hub | 0 | 6 | 0 | 0 | 0 | 6 |
| learnfw | 0 | 1 | 0 | 17 | 0 | 18 |
| mcp-hub | 0 | 0 | 33 | 18 | 0 | 51 |
| meiki-dms | 0 | 5 | 0 | 4 | 0 | 9 |
| news-hub | 0 | 2 | 0 | 17 | 0 | 19 |
| odoo-hub | 0 | 3 | 0 | 7 | 0 | 10 |
| pptx-hub | 0 | 1 | 0 | 0 | 0 | 1 |
| promptfw | 0 | 3 | 0 | 0 | 0 | 3 |
| research-hub | 0 | 2 | 0 | 7 | 0 | 9 |
| risk-hub | 0 | 55 | 0 | 209 | 0 | 264 |
| robo-lab | 0 | 0 | 7 | 0 | 0 | 7 |
| tax-hub | 0 | 9 | 0 | 25 | 0 | 34 |
| trading-hub | 0 | 21 | 0 | 65 | 0 | 86 |
| travel-beat | 2 | 12 | 0 | 75 | 0 | 89 |
| ttz-hub | 0 | 1 | 0 | 6 | 0 | 7 |
| weltenhub | 0 | 5 | 0 | 15 | 0 | 20 |
| writing-hub | 0 | 73 | 0 | 286 | 0 | 359 |

## Toolkits, MCP-Werkzeuge, Modelle (vollstaendig)

| Repo | Quelle | Name | Fundstelle | Hinweis |
|---|---|---|---|---|
| cad-hub | toolkit | `CADToolkit` | `apps/ifc/toolkit.py:162` | DomainToolkit |
| iil-adrfw | mcp | `adr_check` | `src/iil_adrfw/server.py:169` |  |
| iil-adrfw | mcp | `adr_explain` | `src/iil_adrfw/server.py:175` |  |
| iil-adrfw | mcp | `adr_validate_cross_repo` | `src/iil_adrfw/server.py:181` |  |
| iil-adrfw | mcp | `adr_query` | `src/iil_adrfw/server.py:196` |  |
| iil-adrfw | mcp | `adr_audit` | `src/iil_adrfw/server.py:208` |  |
| iil-adrfw | mcp | `adr_propose` | `src/iil_adrfw/server.py:220` |  |
| iil-adrfw | mcp | `adr_diff` | `src/iil_adrfw/server.py:239` |  |
| iil-adrfw | mcp | `adr_narrate` | `src/iil_adrfw/server.py:257` |  |
| iil-adrfw | mcp | `adr_validate` | `src/iil_adrfw/server.py:280` |  |
| iil-adrfw | mcp | `adr_staleness` | `src/iil_adrfw/server.py:286` |  |
| iil-adrfw | mcp | `adr_impact` | `src/iil_adrfw/server.py:293` |  |
| iil-adrfw | mcp | `adr_freshness` | `src/iil_adrfw/server.py:299` |  |
| iil-assist-core | modell | `MandantEinstellung` | `assist_core/models.py:59` | Haus-spezifische Praxis-Einstellungen eines Mandanten (LRA). |
| iil-assist-core | modell | `Regelfreigabe` | `assist_core/models.py:145` | Governance-Hülle einer Regel-Zelle (Konzept § 8.1, §14 Punkt 3). |
| iil-assist-core | modell | `RegelAuditEintrag` | `assist_core/models.py:385` | Append-only Audit-Trail zu einer `Regelfreigabe` (Konzept §14 Punkt 3/7). |
| iil-codeguard | mcp | `?` | `src/iil_codeguard/mcp_server/server.py:77` |  |
| iil-codeguard | mcp | `?` | `src/iil_codeguard/mcp_server/server.py:115` |  |
| iil-codeguard | mcp | `?` | `src/iil_codeguard/mcp_server/server.py:140` |  |
| iil-voice-agent | mcp | `mail_overview` | `src/voice_agent/mcp_mail/server.py:64` |  |
| iil-voice-agent | mcp | `mail_read_thread` | `src/voice_agent/mcp_mail/server.py:80` |  |
| iil-voice-agent | mcp | `mail_draft_reply` | `src/voice_agent/mcp_mail/server.py:91` |  |
| iil-voice-agent | mcp | `mail_draft_new` | `src/voice_agent/mcp_mail/server.py:111` |  |
| iil-voice-agent | mcp | `mail_delete_thread` | `src/voice_agent/mcp_mail/server.py:124` |  |
| iil-voice-agent | mcp | `mail_search` | `src/voice_agent/mcp_mail/server.py:143` |  |
| iil-voice-agent | mcp | `mail_organize_plan` | `src/voice_agent/mcp_mail/server.py:155` |  |
| iil-voice-agent | mcp | `mail_organize_apply` | `src/voice_agent/mcp_mail/server.py:184` |  |
| mcp-hub | mcp | `tool_generate_image` | `illustration_mcp/src/illustration_mcp/server.py:17` |  |
| mcp-hub | mcp | `tool_add_speech_bubble` | `illustration_mcp/src/illustration_mcp/server.py:50` |  |
| mcp-hub | mcp | `tool_create_comic_page` | `illustration_mcp/src/illustration_mcp/server.py:98` |  |
| mcp-hub | mcp | `search_knowledge` | `outline_mcp/server.py:109` |  |
| mcp-hub | mcp | `get_document` | `outline_mcp/server.py:153` |  |
| mcp-hub | mcp | `create_runbook` | `outline_mcp/server.py:182` |  |
| mcp-hub | mcp | `create_concept` | `outline_mcp/server.py:206` |  |
| mcp-hub | mcp | `create_lesson` | `outline_mcp/server.py:230` |  |
| mcp-hub | mcp | `update_document` | `outline_mcp/server.py:255` |  |
| mcp-hub | mcp | `list_recent` | `outline_mcp/server.py:292` |  |
| mcp-hub | mcp | `list_collections` | `outline_mcp/server.py:332` |  |
| mcp-hub | mcp | `get_document_by_url` | `outline_mcp/server.py:358` |  |
| mcp-hub | mcp | `delete_document` | `outline_mcp/server.py:448` |  |
| mcp-hub | mcp | `search_airports` | `travel_mcp/src/travel_mcp/server.py:80` |  |
| mcp-hub | mcp | `get_airline_info` | `travel_mcp/src/travel_mcp/server.py:89` |  |
| mcp-hub | mcp | `find_nearby_airports` | `travel_mcp/src/travel_mcp/server.py:95` |  |
| mcp-hub | mcp | `search_flights` | `travel_mcp/src/travel_mcp/server.py:103` |  |
| mcp-hub | mcp | `get_flight_inspiration` | `travel_mcp/src/travel_mcp/server.py:147` |  |
| mcp-hub | mcp | `get_cheapest_dates` | `travel_mcp/src/travel_mcp/server.py:156` |  |
| mcp-hub | mcp | `list_hotels_by_city` | `travel_mcp/src/travel_mcp/server.py:167` |  |
| mcp-hub | mcp | `list_hotels_by_location` | `travel_mcp/src/travel_mcp/server.py:176` |  |
| mcp-hub | mcp | `get_hotel_details` | `travel_mcp/src/travel_mcp/server.py:187` |  |
| mcp-hub | mcp | `search_hotels` | `travel_mcp/src/travel_mcp/server.py:193` |  |
| mcp-hub | mcp | `get_hotel_rating` | `travel_mcp/src/travel_mcp/server.py:245` |  |
| mcp-hub | mcp | `get_amenity_list` | `travel_mcp/src/travel_mcp/server.py:251` |  |
| mcp-hub | mcp | `list_providers` | `travel_mcp/src/travel_mcp/server.py:262` |  |
| mcp-hub | mcp | `plan_trip` | `travel_mcp/src/travel_mcp/server.py:282` |  |
| mcp-hub | mcp | `compare_packages` | `travel_mcp/src/travel_mcp/server.py:334` |  |
| mcp-hub | mcp | `fetch_page` | `web_intelligence_mcp/src/web_intelligence_mcp/server.py:41` |  |
| mcp-hub | mcp | `wikipedia_search` | `web_intelligence_mcp/src/web_intelligence_mcp/server.py:93` |  |
| mcp-hub | mcp | `extract_links` | `web_intelligence_mcp/src/web_intelligence_mcp/server.py:109` |  |
| mcp-hub | mcp | `fetch_multiple` | `web_intelligence_mcp/src/web_intelligence_mcp/server.py:151` |  |
| mcp-hub | mcp | `extract_content` | `web_intelligence_mcp/src/web_intelligence_mcp/server.py:180` |  |
| robo-lab | mcp | `start_sim` | `twin_mcp/server.py:61` |  |
| robo-lab | mcp | `walk` | `twin_mcp/server.py:75` |  |
| robo-lab | mcp | `stop` | `twin_mcp/server.py:82` |  |
| robo-lab | mcp | `state` | `twin_mcp/server.py:88` |  |
| robo-lab | mcp | `health` | `twin_mcp/server.py:94` |  |
| robo-lab | mcp | `inject_fault` | `twin_mcp/server.py:101` |  |
| robo-lab | mcp | `stop_sim` | `twin_mcp/server.py:109` |  |
| travel-beat | toolkit | `StoryToolkit` | `apps/stories/agent/toolkit.py:489` | DomainToolkit |
| travel-beat | toolkit | `TravelBeatToolkit` | `apps/trips/agent/toolkit.py:20` | DomainToolkit |

## Management-Commands (vollstaendig)

| Repo | Name | Hilfe |
|---|---|---|
| 137-hub | `decay_scores` |  |
| 137-hub | `seed_dashboard` | Create test contacts, activities, transmissions |
| 137-hub | `send_drip_emails` | Send due welcome-sequence drip emails. |
| 137-hub | `update_segments` | Display contact segment counts |
| 137-hub | `seed_action_types` | Seed aifw LLM providers, models and action types (idempotent) |
| aifw | `check_aifw_config` | Verify that all aifw action codes have an active catch-all row. |
| aifw | `init_aifw_config` | Seed default aifw LLM providers, models and the nl2sql action type |
| aifw | `promote_feedback` | Promoted korrigierte NL2SQLFeedback-Einträge zu NL2SQLExample |
| aifw | `seed_nl2sql_examples` | Seed NL2SQLExample mit verifizierten Q→SQL-Paaren für Few-Shot-Prompting |
| aifw | `validate_schema` | Validiert Schema-XML gegen tatsächliche DB-Struktur |
| aifw | `promote_feedback` | Promoted korrigierte NL2SQLFeedback-Einträge zu NL2SQLExample |
| aifw | `seed_nl2sql_examples` | Seed NL2SQLExample mit verifizierten Q→SQL-Paaren für Few-Shot-Prompting |
| aifw | `validate_schema` | Validiert Schema-XML gegen tatsächliche DB-Struktur |
| apo-hub | `etl_apocenna` | ETL apocenna MySQL → apo-hub (ADR-001 §10). |
| apo-hub | `seed_plz` | PLZ-Zentroide aus CSV laden (idempotent). |
| apo-hub | `backfill_geo` | Geo-Punkte aus kanonischen Decimal-Koordinaten (re)materialisieren (ADR-001 §2.3). |
| apo-hub | `send_test_email` | Test-E-Mail mit den aktuellen EMAIL_*-Settings senden (SMTP-Check). |
| ausschreibungs-hub | `ingest_vergabe_document` | Ingest lokale Vergabe-Dateien (PDF) in VergabeDocument des aktuellen Schemas. |
| ausschreibungs-hub | `run_vergabe_analyse` | Startet die LLM-Extraktion (VergabeAnalyse) für eine Ausschreibung im aktuellen Schema. |
| ausschreibungs-hub | `seed_pilot_documents` | Seed: Tenant + Ausschreibung + 3 Beispiel-Vergabe-PDFs (klassifiziert, kein LLM). |
| ausschreibungs-hub | `seed_vergabe_action_codes` | Seed Vergabe-Action-Codes (vergabe.extract_*) in aifw.AIActionType. |
| ausschreibungs-hub | `seed_public_tenant` | Public-Tenant (schema  |
| ausschreibungs-hub | `bestand_aufraeumen` | Blendet aktive Ausschreibungen ohne Suchprofil-Treffer und ohne Bid-Entscheidung aus (#208). |
| ausschreibungs-hub | `doe_suchlauf` | Suchlauf: DOE-OpenData-Tagesexporte gegen ein Suchprofil, Treffer in die DB. |
| ausschreibungs-hub | `dubletten_aufraeumen` | Fuehrt dieselbe Vergabe aus mehreren Quellen auf einen aktiven Eintrag zusammen (#207). |
| ausschreibungs-hub | `ketten_check` | Prueft Invarianten am Datenbestand eines Tenants (Ketten-Melder). |
| ausschreibungs-hub | `seed_suchprofil_ki` | Seed: Suchprofil  |
| ausschreibungs-hub | `tenant_nutzer_anlegen` | Legt einen Nutzer an und ordnet ihn einem Mandanten zu (kein Passwort in argv). |
| ausschreibungs-hub | `fetch_vergabeunterlagen` | Holt Vergabeunterlagen von e-Vergabe und legt sie als VergabeDocument ab. |
| ausschreibungs-hub | `ingest_vergabe_document` | Ingest lokale Vergabe-Dateien (PDF) in VergabeDocument des aktuellen Schemas. |
| ausschreibungs-hub | `run_vergabe_analyse` | Startet die LLM-Extraktion (VergabeAnalyse) für eine Ausschreibung im aktuellen Schema. |
| ausschreibungs-hub | `seed_pilot_documents` | Seed: Tenant + Ausschreibung + 3 Beispiel-Vergabe-PDFs (klassifiziert, kein LLM). |
| ausschreibungs-hub | `seed_vergabe_action_codes` | Seed Vergabe-Action-Codes (vergabe.extract_*) in aifw.AIActionType. |
| ausschreibungs-hub | `bringup_check` | Prueft, ob jede Domain auf ein Schema zeigt, das sie bedienen kann (Bring-up-Melder). |
| ausschreibungs-hub | `seed_dev_tenant` | Entwicklungs-Mandanten anlegen und die Dev-Domain(s) darauf zeigen lassen (idempotent) |
| ausschreibungs-hub | `seed_public_tenant` | Public-Tenant (schema  |
| billing-hub | `seed_platforms` | Seed initial platform registrations |
| billing-hub | `seed_catalog_products` | Seed catalog Products with activate/deactivate URLs (ADR-118) |
| billing-hub | `seed_plans` | Seed ProductPlans for all platforms (idempotent) |
| cad-hub | `bootstrap_github_labels` | Bootstrap GitHub Issue-Triage-Labels für cad-hub (ADR-085). Idempotent. |
| cad-hub | `seed_aifw_config` | Seed aifw providers, models, and cad_nlp action type for cad-hub |
| cad-hub | `diff_room_detection` | Vergleicht FloorPlanAnalyzer (alt) vs. nl2cad DXFParser (neu) Raumerkennung. |
| cad-hub | `import_registry_seed` | Importiert nl2cad modules.json + profiles.json als DB-Seed (idempotent) |
| coach-hub | `cleanup_expired_data` | Löscht abgelaufene Daten gemäß DSGVO-Retention-Policies (ADR-082) |
| coach-hub | `seed_book_redirects` | Seed BookRedirect entries for QR codes |
| coach-hub | `migrate_to_learnfw` | Migrate coach-hub data to iil_learnfw tables (ADR-150 Phase 2) |
| coach-hub | `seed_lernmodule` | Seed/update KI ohne Risiko micro-lessons in coach-hub |
| coach-hub | `quickcheck_seed` | Befüllt QuickCheck-Konfiguration aus questions.py (idempotent) |
| coach-hub | `quickcheck_stats` | Zeigt QuickCheck-Statistiken und Lead-Übersicht |
| dev-hub | `import_adrs` | Import ADRs from a GitHub repository (SHA-aware: skips unchanged files) |
| dev-hub | `import_llms` | Import LLMs from Control Center JSON export |
| dev-hub | `seed_ai_config` | Seed AI configuration: LLM providers, agent configs, prompt templates. |
| dev-hub | `check_platform_packages` | Check platform package versions and upgrade readiness |
| dev-hub | `frische_vergleich` | Vergleicht den Katalog (Kopie) mit catalog-info.yaml je Registry-Repo (Quelle). |
| dev-hub | `populate_catalog` | Populate catalog with platform hub data |
| dev-hub | `beat_aufraeumen` | Loescht PeriodicTask-Zeilen mit totem Task; --auch NAME loescht einen Altnamen. |
| dev-hub | `migrate_tiered` |  |
| dev-hub | `seed_all` | Run all seed commands in order. |
| dev-hub | `seed_organization` | Create the default Organization (tenant) for dev-hub. |
| dev-hub | `seed_health_checks` | Seed health check endpoints for all platform hubs. |
| dev-hub | `setup_health_checks` | Health Checks für alle Platform-Hubs registrieren |
| dev-hub | `mail_anhang` | Anhänge auflisten und herausgeben — liest nur die Datenbank. |
| dev-hub | `mail_dossier` | Dossier mit Evidenz je Zeile und Ausgabezustand (ADR-288 §4.6/§4.7). |
| dev-hub | `mail_gegenueber` | Gegenüber anlegen und einordnen — die Feinarbeit hinter der Zweiseitigkeit. |
| dev-hub | `mail_graph_pruefen` | Graph-Zugang stufenweise prüfen (Datei → Token → Berechtigung → Postfach). |
| dev-hub | `mail_ingest` | Kopfzeilen eines Postfachs in den Index uebernehmen (read-only am Postfach). |
| dev-hub | `mail_kennung_pruefen` | Nachrichten ohne natürlichen Schlüssel auflisten (kollidierend vs. identitätslos). |
| dev-hub | `mail_kette` | Die vollstaendige Kette zu einer Sache (ADR-288 §4.7 Stufe 4). |
| dev-hub | `mail_schluessel_wechseln` | Wrapped-DEKs der persistierten Bodys auf den aktiven Schluessel umschluesseln. |
| dev-hub | `mail_suche` | Den Mail-Index abfragen (ADR-288 §4.7 Stufe 1+2) — liest nur, kein Postfach-Zugriff. |
| dev-hub | `mail_volltext` | Volltext + Anhänge holen — je Vorgang oder für den ganzen Umfang (ADR-293). |
| dev-hub | `mail_vorgang` | Vorgänge verwalten (ADR-288 §4.1) — durable Kuration über dem Index. |
| dev-hub | `mail_wartet` | Wer schuldet wem eine Antwort — deterministische Baseline ohne KI (KONZ-043 REC-2). |
| dev-hub | `seed_mail_agent_demo` | Seed Mail Agent demo data (student thread + knowledge base). Idempotent. |
| dev-hub | `seed_servers` | Seed platform servers (hetzner-dev, hetzner-prod, hetzner-odoo) |
| dev-hub | `load_audience_config` | Importiert audience.yaml-Dateien in die AudienceConfig-DB-Modelle (idempotent). |
| dev-hub | `seed_doc_metrics` | Seed default DocHealthMetric weights (ADR-158 D-3). |
| dev-hub | `seed_hubs` | Seed PlatformHub data for iil.pet portal |
| dev-hub | `dispatch_issue` | Dispatch a GitHub issue to a headless_run agent (Stage B: manual). |
| dev-hub | `quality_check` | Render the quality-check prompt for a hub (Phase 1: print only). |
| dev-hub | `repo_health_import` | Import a pre-rendered repo-health Markdown report into techdocs. |
| dev-hub | `repo_health_report` | Scan local repos under REPO_BASE_DIR and produce a health report. |
| dev-hub | `seed_platform_templates` | Seed platform ADR + documentation templates into sw_templates. |
| dev-hub | `seed_techdocs` | Seed DocSite entries for all platform hubs (real GitHub repos). |
| dev-hub | `sync_techdocs` | Sync documentation from GitHub repositories into TechDocs. |
| dms-hub | `seed_demo_connection` | Create a demo DmsConnection + CategoryMappings for PoC testing |
| frist-hub | `seed_regelkatalog` | Fristenkatalog-Entwürfe (YAML) als Regelfreigabe im Status  |
| frist-hub | `ueberwache_fristen` | UC-14: Fristen bewerten (Ampel Kap. 7) und rote Klasse-A/-E-Fristen eskalieren. |
| illustration-hub | `anime_export_lora_dataset` | Exportiert Bilder + Bildunterschriften einer Figur als LoRA-Trainingsdatensatz. |
| illustration-hub | `anime_lora_variants` | Erzeugt zusaetzliche Trainingsbilder einer Figur aus ihrem Reference-Sheet. |
| illustration-hub | `anime_produce_episode` | Baut aus einer Anime-Episode ein Comic-Projekt (Seiten, Panels, Sprechblasen). |
| illustration-hub | `anime_reference_sheets` | Erzeugt die Reference-Sheets aller Figuren einer Anime-Serie. |
| illustration-hub | `anime_render_episode` | Rendert (und lettert) alle Panels einer Anime-Episode. |
| illustration-hub | `anime_serie_importieren` | Pfad zur Serien-Datei (s. apps/anime/serien/*.yaml). Die Datei ist die  |
| illustration-hub | `figur_lora_registrieren` | Dateiname der LoRA auf der Box, mit {ENDUNG} -- kein Pfad |
| illustration-hub | `kanon_setzen` | Ohne dieses Flag wird NICHTS geschrieben -- nur gezeigt, was passieren wuerde. |
| illustration-hub | `kanon_zeigen` | Zeigt Ref, Name und Kanon-Text der Figuren einer Serie. Rein lesend. |
| illustration-hub | `lora_nachziehen` | Kopiert SeriesCharacter.lora_datei in ProjectCast und PanelCharacter (#252). |
| illustration-hub | `seed_anime_pilot` | Legt den Anime-Piloten  |
| illustration-hub | `seed_anime_reise` | Seedet die Reise-Serie  |
| illustration-hub | `stil_nachziehen` | Kopiert den Serien-Look in ComicProject.style_prompt bestehender Projekte (#225). |
| illustration-hub | `bild_inventar` | Zaehlt Bilder je Kanal/Rolle und Comic-Projekte je world_ref (read-only). |
| illustration-hub | `bild_renderweg` | Zeigt Provider, Rueckfall und Prompt einzelner Bilder (read-only). |
| illustration-hub | `seed_demo_user` | Legt den dev-only Demo-Test-User idempotent an (Default demo.iil.pet/demo12345). Nur bei DEBUG=True. |
| illustration-hub | `check_comfyui` | ComfyUI-Basis-URL (Default: settings.COMFYUI_URL). |
| illustration-hub | `comfyui_bakeoff` | Rendert dieselben Motive durch mehrere Modellprofile und legt die Bilder ab. |
| illustration-hub | `comfyui_capabilities` | Prueft, welche Operationen der Panel-Kette eine ComfyUI-Instanz tragen kann. |
| illustration-hub | `comfyui_cutout` | Stellt ein Bild ueber ComfyUI frei und prueft die Maskenpolaritaet am Ergebnis. |
| illustration-hub | `comfyui_relight` | Leuchtet ein Bild per img2img auf der ComfyUI-Instanz um. |
| illustration-hub | `comfyui_upscale` | Vergroessert ein Bild ueber ein Upscale-Modell auf der ComfyUI-Instanz. |
| illustration-hub | `cutout_bakeoff` | Vergleicht den lokalen Freisteller mit fal-ai/birefnet/v2 an einem Bild. |
| illustration-hub | `figur_nulllinie` | Wieviele der N Bilder als dieselbe Figur gelten muessen (Default 10). |
| illustration-hub | `graph_export` | Schreibt den ComfyUI-Graphen (API-Form) heraus, ohne zu rendern. |
| illustration-hub | `medien_zeigen` | Zeigt die Medienvorgaben (Seitenverhaeltnis, Textfreiheit, Druckziel). Rein lesend. |
| illustration-hub | `smoke_render` | Nur aufräumen: löscht alle Smoke-Projekte und rendert nichts. |
| illustration-hub | `songs_einlesen` | Liest Songs (WAV + MP3 + JSON) aus dem Musik-Volume in die Bibliothek ein. |
| learn-hub | `_kurs_data` |  |
| learn-hub | `_kurs_kap1_5` |  |
| learn-hub | `_kurs_kap6_9` |  |
| learn-hub | `seed_kurse` | Seed den vollständigen KI-ohne-Risiko-Kurs |
| learn-hub | `import_lecture_module` | Projiziert ein writing-hub modul.json (lecture-module/v1) in learnfw. |
| learn-hub | `seed_lernmodule` | Seed KI ohne Risiko™ learning modules (3 chapters, 9 lessons, 27 quiz questions) |
| learnfw | `assessment_seed` | Importiert Assessment-Seed-Daten (idempotent, multi-tenant-sicher). |
| meiki-dms | `seed_demo_connection` | Create a demo DmsConnection + CategoryMappings for PoC testing |
| meiki-dms | `export_buergerportal` | Bestätigte Personen als buergerportal-konformes JSON exportieren (KONZ-meiki-003 D2) |
| meiki-dms | `materialize_candidates` | Synthetik-Kandidaten erzeugen + in DB persistieren (KONZ-meiki-003 Stufe 2) |
| meiki-dms | `seed_dvelop` | Synthetik-Seed in echte iil.d-velop.cloud (Variante 2, KONZ-meiki-003) |
| meiki-dms | `seed_synthetic` | Synthetik-Seed → Extraktion → Az-Clustering → Kill-Gate-Report (KONZ-meiki-003) |
| news-hub | `digest_bauen` | Baut einen Hot-Topics-Digest aus dem uebergebenen Umfang. |
| news-hub | `digest_taeglich` | Baut den Digest fuer die letzten N Tage und speichert ihn. |
| odoo-hub | `init_odoo_schema` | Initialisiert AIActionType(nl2sql) + SchemaSource(odoo_mfg) für Odoo MFG |
| odoo-hub | `sync_odoo_schema` | Sync Schema-XML aus Odoo ir.model.fields (direkte DB-Abfrage via DATABASES[ |
| odoo-hub | `validate_schema` | Validate NL2SQL Schema-XML against actual DB schema (drift detection) |
| pptx-hub | `seed_aifw_actions` | Seed aifw ActionType rows for pptx-hub action_codes (ADR-003). |
| promptfw | `export_prompts` | Export prompt templates from the database to YAML files. |
| promptfw | `seed_prompts` | Import prompt templates from .jinja2 files or YAML into the database. |
| promptfw | `validate_prompts` | Validate all prompt templates in the database (CI gate). |
| research-hub | `sync_paperless` | Sync documents from Paperless-ngx into DocumentMetadata |
| research-hub | `seed_aifw` | Seed aifw providers, models, and action types. |
| risk-hub | `enable_rls` | Enable/disable PostgreSQL RLS on tenant tables (ADR-137). |
| risk-hub | `setup_rls_roles` | Setup PostgreSQL roles for RLS (ADR-137). |
| risk-hub | `seed_action_types` | Seed aifw LLM providers, models and action types for risk-hub |
| risk-hub | `debug_dashboard` | Debug dashboard 500 — simulate get_compliance_kpis for first org |
| risk-hub | `import_paperless_scans` | Übernimmt mit einem Tag markierte Paperless-Scans in den Dokumentbestand |
| risk-hub | `assign_tom_categories` | TOM ohne Kategorie den Kontrollzielen nach §9 BDSG / Art. 32 DSGVO zuordnen. |
| risk-hub | `create_deletion_request` | Legt einen Löschantrag (Art. 17 DSGVO) an — headless, wie die UI. |
| risk-hub | `delete_mandate` | Leeres Mandat löschen (#562) — Trockenlauf ohne --apply |
| risk-hub | `dsb_doku_completeness` | Vollstaendigkeit der Mandanten-Doku auswerten (nur Zahlen und Sektionsnamen) |
| risk-hub | `dsb_durchklick_routen` | Konkrete URL je dsb-Route ausgeben (JSON) — Grundlage des Durchklick-Belegs. |
| risk-hub | `dsb_tom_titel_bereinigen` | TOM-Titel von Import-Artefakten befreien (#504) — Trockenlauf ohne --apply |
| risk-hub | `import_dsb_docs` | Importiert DSB-Unterlagen in die Fachtabellen (TOM, VVT-Struktur). |
| risk-hub | `import_vvt` | Importiert ein Verfahrensverzeichnis (XLSX) in das DSB-Modul (#28). |
| risk-hub | `seed_[mandant]_org` | Slug der Ziel-Organization (default: {ORG_SLUG}) |
| risk-hub | `seed_[mandant]_vvt_branchen` |  |
| risk-hub | `seed_dsb_demo` | Seed a DSB-enabled org+user+mandate for local walkthroughs. |
| risk-hub | `seed_muster_org` | Seed SYNTHETISCHES Muster-Organigramm: Sites + Departments + Mandate.appointees. Idempotent. |
| risk-hub | `seed_muster_vvt` | Seed SYNTHETISCHE Muster-VVTs (Bewegungsdaten-Platzhalter) + Lookups. Idempotent. |
| risk-hub | `seed_nis2_grundschutz_demo` | Seed Grundschutz-Nachweise (NIS2) für lokale Walkthroughs + Renderer-#2-Parity. |
| risk-hub | `seed_standard_retention` |  |
| risk-hub | `seed_tom_categories` | Seed der Standard-TOM-Kategorien nach BDSG / Art. 32 DSGVO (idempotent). |
| risk-hub | `seed_tom_templates` | Seed Best-Practice-TOM-Vorlagen je Gruppe (idempotent). |
| risk-hub | `assign_auto_projects` | ADR-044 Phase 7: Konzepte ohne Project-FK einem Auto-Projekt zuweisen |
| risk-hub | `audit_orphan_concepts` | Read-only-Audit verwaister Ex-Konzepte (project=NULL) + Kill-Gate (KONZ-003 MVC-4). |
| risk-hub | `seed_ex_demo` | Seed Ex-Schutz preconditions (Site->Area->Concept) for local/demo. |
| risk-hub | `seed_ex_doc_template` | Seed Standard-Explosionsschutzdokument-Template (GefStoffV § 6 Abs. 9, idempotent) |
| risk-hub | `seed_explosionsschutz` | Seed globale Explosionsschutz-Stammdaten (idempotent) |
| risk-hub | `seed_all_gbu` | Führt alle GBU-Seed-Commands in korrekter Reihenfolge aus (idempotent) |
| risk-hub | `seed_exposure_risk_matrix` |  |
| risk-hub | `seed_h_code_mappings` | Annotationen bestehender Mappings überschreiben |
| risk-hub | `seed_hazard_categories` | Seed GBU Gefährdungskategorien — idempotent via update_or_create(code) |
| risk-hub | `seed_measure_templates` |  |
| risk-hub | `sds_check_deadlines` | Nur zählen, keine Änderungen durchführen. |
| risk-hub | `sds_overlap_report` | Maximale Anzahl Beispiele in der Ausgabe (default: 10) |
| risk-hub | `seed_property_definitions` | Seed SDS Property Definitions (idempotent, ADR-017 §5.3) |
| risk-hub | `seed_sds_review_demo` | Organization-Slug, dessen Tenant die Revisionen besitzt (Default: demo). |
| risk-hub | `create_api_key` | Create an API key for a user |
| risk-hub | `create_initial_users` | Create initial admin (superuser) and achim (staff) users |
| risk-hub | `seed_test_user` | Create testuser@test.local / test1234 for local dev and Playwright tests (DEBUG only). |
| risk-hub | `intake_annahmequote` | Annahmequote der Intake-Kandidaten auswerten (KONZ-risk-hub-007 Kill-Gate) |
| risk-hub | `seed_module_demo` | Seed demo tenants with different module bookings (click-dummy). |
| risk-hub | `load_permissions` | Load default permissions and system roles (ADR-003) |
| risk-hub | `import_substances` | Importiert Gefahrstoffe aus JSON-Datendateien für einen bestimmten Tenant |
| risk-hub | `load_ghs_data` | Lädt H-Sätze, P-Sätze und GHS-Piktogramme in die Datenbank |
| risk-hub | `audit_module_subscriptions` | Modul-Abos gegen die Registry prüfen; unbekannte und wirkungslose ausweisen. |
| risk-hub | `create_test_user` | Create a test user with all modules (business plan) for an organization. |
| risk-hub | `delete_tenant` | Leeren Tenant löschen (#562) — Trockenlauf ohne --apply |
| risk-hub | `hole_mandanten_logos` | Logos der Mandanten von ihren Websites holen (#655). |
| risk-hub | `merge_tenant` | Zwei Tenants zusammenführen (#562) — Trockenlauf ohne --apply |
| risk-hub | `onboard_tenant` | Ordner mit TOM/VVT/AVV-CSVs (*.csv), werden auto-detected importiert |
| risk-hub | `provision_user_access` | Username to provision (must already exist) |
| risk-hub | `reconcile_assets` | ADR-054 Slice 0: classify legacy location-scopings (read-only). |
| risk-hub | `seed_demo` | Seed demo data for development |
| risk-hub | `seed_risk_demo` | Seed an all-modules org+user for local risk-hub walkthroughs. |
| risk-hub | `seed_staging_demo` |  |
| tax-hub | `seed_aifw_actions` | Zeigt, was geschrieben würde, ohne DB-Änderung. |
| tax-hub | `embed_chunks` | Bettet noch nicht eingebettete Korpus-Chunks als Vektoren ein. |
| tax-hub | `goldset_report` | Misst Recall@5/@10 und MRR der Recherche-Suche gegen das Gold-Set. |
| tax-hub | `ingest_dip` | DIP nach Drucksachen mit Volltext durchsuchen und ingestieren. |
| tax-hub | `ingest_gii` | GII-Katalog durchsuchen und Treffer als versionierte Dokumente ingestieren. |
| tax-hub | `ingest_rii` | Präfix des Gerichts-Feldes, z. B. BFH,  |
| tax-hub | `korpus_gesundheit` | Misst Vektor-Abdeckung, Quellen-Aktualitaet, Recall und Suchmodi. |
| tax-hub | `seed_dehnert` | Erstellt den Kunden  |
| tax-hub | `seed_public_tenant` | Public-Tenant (schema  |
| trading-hub | `activate_paper` | Paper-Trading scharf/aus schalten (nur mode=PAPER; LIVE wird verweigert) |
| trading-hub | `backtest_news` | Run News Momentum A/B backtest (ADR-408 Phase 2) |
| trading-hub | `backtest_options` | Backtest options strategies to generate ML training data |
| trading-hub | `backtest_orb` | Run ORB Breakout backtest with A/B comparison (pure vs +sentiment) |
| trading-hub | `collect_greeks` | Collect Greeks and IV snapshots for ML training |
| trading-hub | `collect_market_data` | Fetch historical OHLCV data via yfinance into MarketData table |
| trading-hub | `divergence` | Backtest↔Paper-Divergenz-Gate je Scalping-Strategie (read-only) |
| trading-hub | `promote_strategy` | Promotion eines (Account, Strategie)-Tracks (KONZ-005 REC-4) |
| trading-hub | `run_options_bot` | Run the autonomous options trading bot (Covered Call / CSP / Wheel) |
| trading-hub | `run_paper_simulator` | Run accelerated paper trading with ML data collection |
| trading-hub | `scalping_tick` | Run a single scalping engine tick (ADR-408) |
| trading-hub | `scan_options_candidates` | Scan for options candidates (IB Scanner + Watchlist + Filter Pipeline) |
| trading-hub | `scorecard` | Per-Track Performance-Scorecard (KONZ-005 REC-5, read-only) |
| trading-hub | `seed_action_types` | Seed aifw LLM providers, models and action types (idempotent) |
| trading-hub | `seed_options_strategies` | Seed options strategies, LYNX paper account, and trading pairs |
| trading-hub | `setup_lynx_paper` | Set up LYNX Paper Trading: account, portfolio, strategy, and trading pairs |
| trading-hub | `shadow_evidence` | Shadow-Evidenz auswerten: Screener-A/B + Initial-Edge-Gate (read-only) |
| trading-hub | `start_trading` | Start the trading loop (paper or live mode) with IB Gateway |
| trading-hub | `sync_market_events` | Sync market events: earnings, ex-div (yfinance), FOMC/CPI/NFP/ECB/OpEx (static) |
| trading-hub | `test_ib_connection` | Test connection to IB Gateway (LYNX/IBKR) and show account info |
| trading-hub | `train_strike_selector` | Train the ML strike selector model on closed options positions |
| travel-beat | `init_aifw_actions` | Seed travel-beat domain AIActionType entries into aifw tables |
| travel-beat | `check_site_health` | Check site for broken links, wrong FKs, HTTP errors |
| travel-beat | `export_docs_markdown` | Export Sphinx RST documentation to Markdown files |
| travel-beat | `seed_lookups` | Seeds lookup tables with default values |
| travel-beat | `backfill_quality_scores` | Backfill quality_score=0 chapters and tokens_used=0 stories |
| travel-beat | `cleanup_exports` | Delete files for expired StoryExport records. |
| travel-beat | `fix_total_words` | Recalculate total_words from actual chapter word counts |
| travel-beat | `seed_tier_configs` | Seed TierConfig with enrichment features (ADR-020) |
| travel-beat | `test_v3_pipeline` | Test ADR-025 Three-Phase Pipeline (V3) on a trip |
| travel-beat | `setup_plans` | Create or update default subscription plans |
| travel-beat | `seed_public_tenant` | Create public tenant and register its primary domain |
| travel-beat | `process_milestones` | Verarbeitet importierte Milestones zu Stop/Transport-Objekten |
| ttz-hub | `nl2sql_beispiele_laden` | Laedt nl2sql_examples.json in NL2SQLExample (idempotent). |
| weltenhub | `init_llm_config` | Initialize LLM providers, models, and action types (weltenhub) |
| weltenhub | `seed_action_types` | Seed aifw LLM providers, models and action types (idempotent) |
| weltenhub | `research_locations` | Dispatch research tasks for locations without deep research. |
| weltenhub | `seed_lookups` | Seed all lookup tables idempotently (update_or_create) |
| weltenhub | `seed_scene_templates` | Seed SceneTemplates for travel/transport scenes (idempotent) |
| writing-hub | `kapitel_einspielen` | Spielt fertige Kapitel aus Markdown-Dateien in die Knoten eines Projekts ein |
| writing-hub | `korrigiere_buch` | Behebt maschinell behebbare Befunde eines Buches (Vorschau ohne --anwenden) |
| writing-hub | `optimiere_prompt` | Misst Prompt-Fassungen gegeneinander: je Arm N Runden, Median und Wertebereich |
| writing-hub | `pruefe_buch` | Prueft ein ganzes Buch: Zaehlgroessen, Lektor-Urteil, Buchebenen-Agenten |
| writing-hub | `pruefe_lesbarkeit` | Prueft die Lesbarkeit aller Kapitel eines Projekts (K6) |
| writing-hub | `report_project` | Read-only: Kapitel, Qualitaets-Verdikte, Revisions-Verlauf und Figuren eines Projekts |
| writing-hub | `seed_quality_dimensions` | Seed QualityDimension Lookup-Daten (idempotent) |
| writing-hub | `seed_quality_gate_decisions` | Seed GateDecisionType Lookup-Daten (idempotent) |
| writing-hub | `write_essay` | Autonome wissenschaftliche Aufsatz-Pipeline: Outline → Recherche → Schreiben → Review |
| writing-hub | `write_missing_chapters` | Schreibt die Kapitel eines Projekts nach, die keinen Text haben |
| writing-hub | `count_style_corpus` | Zaehlt den Stil-Referenzkorpus je WritingStyle (KONZ-005 Phase 1). Rein lesend. |
| writing-hub | `generate_style_gate_snapshot` | Berechnet und speichert einen Stiltreue-Gate-Snapshot aus R + K (ADR-202). |
| writing-hub | `generate_style_samples` | Beispieltexte für einen Stil oder alle Stile erzeugen (idempotent) |
| writing-hub | `ingest_style_reference` | Referenzprosa (PDF/EPUB/TXT) als StyleReferenceText an einen WritingStyle ingesten. |
| writing-hub | `measure_style_separation` | Trennmatrix ueber die in der DB gespeicherten Stil-Referenzkorpora. |
| writing-hub | `seed_style_akademisch` | Legt den Stil „Akademisch — Deutsche Fachprosa“ samt Beispieltexten an |
| writing-hub | `seed_style_metall_sinn` | Legt den Stil „Metall-Sinn“ samt Beispieltexten an |
| writing-hub | `seed_style_sinneswelt` | Legt den Stil „Sinneswelt“ (18+, explizit erotische Literatur) samt Beispieltexten an |
| writing-hub | `seed_welt_typen` | Seeded die Welt-Typen der Reihen-Bibel (idempotent) |
| writing-hub | `stil_einspielen` | Uebernimmt einen autorenstil.yaml-Vertrag als WritingStyle und haengt ihn optional ans Buch |
| writing-hub | `altere_wartezustaende` | Setzt ueberfaellige Laeufe aus pending/running auf ihren Endzustand (#814). |
| writing-hub | `dev_konto` | Legt das lokale Entwickler-Konto an (ohne benutzbares Passwort) |
| writing-hub | `dev_login_url` | Generate a signed auto-login URL (expires in 5 minutes) |
| writing-hub | `dienstkonto` | Legt das Dienst-Konto fuer den lesenden illustration-hub-Zugang an (idempotent) |
| writing-hub | `seed_genre_promises` | Seed GenrePromiseLookup (Genre-Versprechen für LLM Layer 10). Idempotent. |
| writing-hub | `seed_series_arc_types` | Seed SeriesArcTypeLookup (ADR-155) — idempotent |
| writing-hub | `seed_turning_point_types` | Seed TurningPointTypeLookup (Drei-Akte / Save-the-Cat). Idempotent. |
| writing-hub | `show_prompt` | Read-only: Quelle (DB/Datei) und Inhalt eines Prompt-Templates anzeigen |
| writing-hub | `transfer_ownership` | Haengt allen Bestand eines Kontos auf ein anderes um (Default: Dry-Run) |
| writing-hub | `seed_studio_einwilligung` | Legt die Studio-Sitzung fuer Band 1 „Die Einwilligung“ an (KONZ-018). |
| writing-hub | `check_illustration_readiness` | Read-only Pre-Flight: Feature-Flag, Client-Config, echte Kapitel-Kandidaten. Löst keinen Job aus. |
| writing-hub | `illustration_reconcile` | Loest IllustrationCandidate im Status  |
| writing-hub | `submit_book_illustration` | Erstellt Slot+Candidate für ein echtes Kapitel und submitted an illustration-hub (ADR-201). |
| writing-hub | `dai_strategy_skripte` | Erzeugt die Vorlesungsskripte aus den Inhaltsmodulen (Owner 2026-09-07). |
| writing-hub | `inhalt_dai_strategy` | Schreibt den ausgearbeiteten Inhalt fuer Session 1. |
| writing-hub | `inhalt_einspielen` | Ein LectureDossier aus einer Datei als menschliche Bearbeitung übernehmen (KONZ-011). |
| writing-hub | `lectures_revision_dag_preflight` | ADR-183 (F16): Preflight-Report für Migration 0011 (Revision-DAG). |
| writing-hub | `medien_dai_strategy` | Setzt die Media-Stichworte auf [Basisname, Variante] um. |
| writing-hub | `modul_paket` | Modul als Paket exportieren: Bündel-JSON + gerenderte Decks (Issue #952 A4). |
| writing-hub | `pruefe_vorlesung` | Prüft Vorlesungen gegen das Deck-Lesbarkeits-Gate (Issue #952 A3). |
| writing-hub | `purge_lecture_project` | DSGVO Art. 17 — Lecture-Projektbaum/User hart löschen (ADR-180 §B14). |
| writing-hub | `seed_digital_ai_strategy` | Legt das Modul Digital & AI Strategy (10130) mit Bloecken + Vorlesungen an. |
| writing-hub | `seed_lecture_outline_wizard_demo` | Reconverge der Lecture-Wizard Demo-Fixtures (ADR-180). |
| writing-hub | `seed_termine_digital_ai_strategy` | Legt die fuenf Vorlesungstermine als Veranstaltungsbloecke an. |
| writing-hub | `verteile_digital_ai_strategy` | Verteilt Themen und Uebungen auf die fuenf Termin-Bloecke. |
| writing-hub | `vorlesung_deck` | Rendert eine Vorlesung als PDF-Foliendeck (Issue #952 A1). |
| writing-hub | `vorlesung_skript` | Rendert eine Vorlesung als Markdown-Skript (Owner-Versuch 2026-09-07). |
| writing-hub | `check_llm_wiring` | LLM-Verdrahtung prüfen: Action → Modell → Provider → Schlüssel → echter Call |
| writing-hub | `check_writing_hub_aifw` | aifw DB-Konfiguration diagnostizieren. |
| writing-hub | `doctor` | Kopplungs-Selbsttest: aifw-Verdrahtung, Provider-Schluessel, weltenhub, Celery-Broker. |
| writing-hub | `pov_backfill` | Setzt OutlineNode.pov_character aus beat_phase, wo der Name eindeutig eine Figur trifft |
| writing-hub | `projekt_exportieren` | Schreibt ein Projekt samt Gliederung, Kapiteln, Serie und Stilprofil als JSON-Bausatz |
| writing-hub | `projekt_importieren` | Liest einen Projekt-Bausatz ein und setzt den Besitz auf das angegebene Konto |
| writing-hub | `redaktionsschleife` | Prueft ein Buch, behebt die behebbaren Befunde und prueft erneut |
| writing-hub | `seed_all` | Alle Stammdaten und aifw-Konfiguration seeden (idempotent). |
| writing-hub | `seed_drama_lookups` | TurningPointTypeLookup, GenrePromiseLookup + QualityDimension seeden (ADR-158). |
| writing-hub | `seed_genre_conventions` | Seed GenreConventionProfile (Genre-Konventionen, ADR-160/#302). Idempotent. |
| writing-hub | `seed_narrative_lookups` | Seed NarrativeModelLookup + ForeshadowingTypeLookup (ADR-156) — idempotent |
| writing-hub | `seed_outline_frameworks` | Seed der Standard-Outline-Frameworks in die Datenbank |
| writing-hub | `seed_project_lookups` | Seed ContentTypeLookup, GenreLookup, AudienceLookup mit Standardwerten |
| writing-hub | `seed_templates` | Seed default ProjectTemplate entries for UC 1.5 |
| writing-hub | `setup_aifw_actions` | aifw-Konfiguration anlegen: LLMProvider, LLMModel, AIActionTypes. |
| writing-hub | `stilcheck` | Stilcheck je Kapitel: Urteil je Regel, Bericht, optional Neuschreiben (#1046) |
| writing-hub | `seed_serie_aas` | Legt die Romanreihe  |
| writing-hub | `seed_serie_aas_band1` | Legt Outline und Kapitel 1 für  |
| writing-hub | `seed_serie_eselsfest_band1` | Legt Outline und Kapitel 1 für  |
| writing-hub | `seed_serie_wiederkehr_band1` | Legt die Outline für  |
| writing-hub | `seed_serien_alternativen` | Legt die Alternativ-Reihen  |
| writing-hub | `kanon_ergaenzen` | Nimmt benannte Figuren in den Kanon eines Projekts auf (Vorschau ohne --anwenden) |
| writing-hub | `kanon_gewinnen` | Legt die Welt an (falls keine da ist) und gewinnt Figuren und Orte aus dem Buch |
| writing-hub | `kanon_hochziehen` | Hebt lokalen Kanon (Welten, Figuren, Orte) nach weltenhub und fuellt die Link-UUIDs |
| writing-hub | `platzhalter_aufloesen` | Loest Platzhalter-IDs auf: Name aus notes retten, erfundene ID verwerfen (#695). |
| writing-hub | `platzhalter_zaehlen` | Zaehlt je Art: echte weltenhub-IDs, Platzhalter (uuid5), ohne ID. |

Service-Funktionen stehen nur in der JSON-Ausgabe (Menge).
