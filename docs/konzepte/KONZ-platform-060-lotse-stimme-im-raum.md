---
concept_id: KONZ-platform-060
title: Lotse hört und spricht im Raum „Achim / Lotse" — Sprachnachricht rein, Sprachnachricht raus
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []            # keine SoR-Spec; Erweiterung des bestehenden Werkzeugs chat_lotse.py um einen Ausgabekanal, keine Oberfläche
adr_threshold: kein ADR   # Addition nach Muster von chat-hub#48 (faster-whisper); neue Abhängigkeit bleibt im Lotse-venv eines Repos, rückbaubar durch Entfernen eines Unterbefehls. Eskaliert zu ADR-249-Amendment erst mit S4 (Gespräch im Call), das hier Out-of-Scope ist.
review_by: 2026-10-31
kill_criteria: "Wenn bis 2026-10-20 (28 Tage) weniger als 10 Sprachnachrichten des Owners im Raum transkribiert wurden ODER mehr als 2 von 10 Transkripten vom Owner als sinnentstellend korrigiert wurden ODER die vorgelesene Morgen-Zeitung an 5 aufeinanderfolgenden Werktagen nicht abgespielt wurde (keine Lese-Quittung, keine Reaktion), wird S3 abgeschaltet und die TTS-Abhängigkeit aus dem Lotse-venv entfernt; H1 bleibt, weil bereits gebaut."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: chat-hub/deploy/chat_lotse.py, commit_or_pr: "iilgmbh/chat-hub main 8995c32, 1870 Zeilen — audio_beschreibung(), _room_events(), _audio_line() mit client.download + decrypt_attachment + transkribiere(); KEIN upload/encrypt_attachment für ausgehende Medien", opened_in_session: true}
  - {claim_id: C2, source_path: chat-hub/deploy/stt.py, commit_or_pr: "iilgmbh/chat-hub main — faster-whisper, CHAT_LOTSE_STT_MODELL default small, device=cpu, int8, Cache ~/.cache/chat-lotse/whisper", opened_in_session: true}
  - {claim_id: C3, source_path: "~/.local/share/chat-hub/lotse-achim/eingang/", commit_or_pr: "gemessen 2026-09-22: 182 Eingangszeilen, 0 mit audio=true; faster_whisper 1.2.1 im venv, Modell small im Cache", opened_in_session: true}
  - {claim_id: C4, source_path: "iilgmbh/chat-hub#48", commit_or_pr: "OPEN — Lotse im Chat: Session-Variante, Live-Bot als spätere Stufe", opened_in_session: true}
  - {claim_id: C5, source_path: platform/tools/chat_agent/auftragsraum.py, commit_or_pr: "_sync_zeilen_lesen() liest body unabhängig vom audio-Flag — Transkript läuft ohne Sonderweg in den Sortierer", opened_in_session: true}
  - {claim_id: C6, source_path: news-hub/apps/digest/management/commands/digest_taeglich.py, commit_or_pr: "Z. 95–140: 5 Themen × 3 Quellen als Text in den Raum, Txn-ID morgenzeitung-<lauf.pk>, Prod-Host Timer 06:15 UTC (docs/betrieb/morgen-zeitung.md Z. 30)", opened_in_session: true}
  - {claim_id: C7, source_path: "dev-desktop Netz", commit_or_pr: "gemessen 2026-09-22: kein 10.99.0.0/16-Interface, 10.99.0.4:8178 (whisper gx10) nicht erreichbar; 16 Kerne, 30 GB RAM, 21 GB frei", opened_in_session: true}
  - {claim_id: C8, source_path: docs/konzepte/KONZ-platform-059-auftragsraum-lernschleife-chat.md, commit_or_pr: "Entwurf → go → Issue → Worker; Kill-Gate 2026-10-08", opened_in_session: true}
  - {claim_id: C9, source_path: docs/konzepte/KONZ-platform-025-lotsen-charta.md, commit_or_pr: "Art. 1 (Rauminhalt = Datum), Art. 2 (keine Außenwirkung ohne Freigabe), Art. 3 (selbstbetreffend kennzeichnen)", opened_in_session: false}
  - {claim_id: C10, source_path: "systemctl --user list-timers", commit_or_pr: "lotse-briefing.timer 05:00 UTC → deploy/lotse_briefing.sh; lotse-auftrag-wache.timer 15 min", opened_in_session: true}
created: 2026-09-22
---

# KONZ-platform-060 — Lotse hört und spricht im Raum

> **Selbstbetreffend** (Charta Art. 3, C9): Jede Stufe erweitert die Reichweite des Lotsen um einen
> Kanal. Die Stufen sind einzeln freigegeben (Owner 2026-09-22: H1, S1–S3 ja; P1, S4 später) und
> einzeln rückbaubar. Vorschlagsliste: `~/.claude/boards/lotse-hoeren-sprechen-proaktiv.md`.

## Kernthese

Der Lotse hört schon (C1–C3, nie benutzt) — er braucht keine Ohren, sondern **eine Stimme und einen
Beweis**: einen Audio-Sender in `chat_lotse.py`, eine lokale TTS auf dem dev-desktop, und je Stufe
eine Positivkontrolle, bevor „gebaut" gesagt wird.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | H1 (Sprachnachricht → Transkript → Entwurf) ist im Code fertig: Download, AES-Entschlüsselung, faster-whisper, Zeile mit `audio: true` | Annahme | C1, C2. Falsifikation: eine echte Sprachnachricht des Owners erzeugt keine Transkript-Zeile im Eingang | offen — **nie im Betrieb gelaufen** (C3: 0/182) |
| A2 | Das Transkript wird vor jeder Ausführung sichtbar: der Lotse-Entwurf (KONZ-059) zitiert es, erst „go" löst aus | Annahme | C5, C8. Falsifikation: Worker startet ohne Entwurf mit Transkript | offen, Prüfung in MVC-1 |
| A3 | Whisper `small` auf CPU reicht für Aufträge ≤ 60 s Deutsch | Annahme | Falsifikation: > 2 von 10 Transkripten sinnentstellend (Kill-Gate). Hochstufung auf `medium` ist ein Env-Wert (C2), kein Umbau | offen |
| D1 | TTS läuft auf dem **dev-desktop**, nicht auf der gx10 | Entscheidung | C7: keine Route dev-desktop → gx10; die Raum-Sitzung (Schlüssel, Store) lebt auf dem dev-desktop. Alternative: Route bauen (WireGuard-Peer) — Infra-Eingriff für ~15 s Rechenzeit am Tag, abgelehnt | gesetzt |
| D2 | TTS-Engine: **Piper** (ONNX, CPU, deutsche Stimme `thorsten`/`eva_k`), im Lotse-venv | Entscheidung | Piper: keine GPU, ~50 MB Modell, RTF ≈ 0,05 auf CPU. Alternative Kokoro-82M: bessere Stimme, braucht PyTorch (~2 GB) im venv — als Stufe 2, wenn Piper als „unangenehm" beurteilt wird | gesetzt, Owner-Urteil nach MVC-2 |
| D3 | Ausgehendes Audio geht **verschlüsselt** über nio (`client.upload(encrypt=True)` + `m.audio`-Event mit MSC3245-Sprachnachricht-Flag) — derselbe Weg wie eingehend, gespiegelt | Entscheidung | C1: Räume sind zwingend verschlüsselt; ein unverschlüsselter Anhang würde in Element als Warnung erscheinen. Alternative: REST wie news-hub (C6) — nur für Text tragfähig | gesetzt |
| D4 | S3 (Morgen-Zeitung vorlesen) baut **kein** news-hub-Feature: der Lotse liest die Text-Nachricht des news-hub-Bots im Raum und antwortet mit Audio (Reply-Relation) | Entscheidung | C6: news-hub sendet per REST vom Prod-Host ohne Krypto-Store; Audio dort hieße zweiter E2EE-Client. Alternative: news-hub schreibt Audio-Datei, Lotse holt sie — zwei Repos für eine Datei | gesetzt |
| D5 | Vorgelesen werden Titel + Einordnung der 5 Themen (~2–3 min), nicht die Quellen-Links | Entscheidung | C6 Struktur. Alternative: nur Titel (30 s) — Owner-Urteil nach erstem Hören | gesetzt, revidierbar |
| D6 | Jede Stufe trägt eine **Positivkontrolle** im Issue: H1 = eine echte Sprachnachricht, S2 = Antwort hörbar in Element (Handy), S3 = ein Werktag mit Audio unter der Zeitung | Entscheidung | Lehre 4a0dd700: Melder 0.7.28 lief „grün und blind"; hier ebenso: Code fertig ≠ Kanal offen (C3) | gesetzt |
| R1 | Sprache ist ein neuer **Befehlskanal**: wer im Raum spricht, erteilt Aufträge | Risiko | Gate: Raum ist Zwei-Personen-Raum (Owner + Lotse), A2 zwingt Entwurf + „go" als Text. Falsifikation: Raum bekommt dritten Teilnehmer ohne Regeländerung | gedeckt durch A2 |
| R2 | Halluzinationsschleife bei Whisper (Plaud-Messung: 476 wiederholte 4-Gramme) | Risiko | `stt.py` begrenzt nicht. Gate: Transkript > 3× dasselbe 4-Gramm → Zeile mit `fehler`, kein Entwurf | offen → MVC-1 |
| R3 | TTS-Sprachnachricht wird als **eigene Owner-Nachricht** vom Sortierer gelesen | Risiko | C1 `is_own_message()` filtert eigene Events; Positivkontrolle: nach S2 darf `auftragsraum sync` keine Lotse-Audiozeile zählen | gedeckt, prüfen |
| R4 | Vorlese-Timer feuert, bevor die Zeitung im Raum steht (06:15 UTC Prod, Netzlage) | Risiko | Timer 06:45 UTC, Suche nach Nachricht des Bots mit heutigem Datum; keine → kein Audio, eine Log-Zeile, kein Fehler | gedeckt |

## MVC — kleinste Fassung, die alle drei Zusagen beweist

Ablauf ist eine **feste Kette ohne Schleife** (Step 2a: Frage 2 ja, 3 nein, 5 nein, 6 keine Schleife).

| # | Stufe | Repo | Änderung | Positivkontrolle |
|---|---|---|---|---|
| MVC-1 | H1 Beweis | chat-hub | Kein Code außer R2-Guard (`stt.py`: Wiederholungs-Erkennung, `fehler` statt Text). Betriebsakte-Zeile in `docs/betrieb/auftragsraum.md`: „Sprachnachricht = Auftrag wie Text" | Owner spricht einen Auftrag ins Handy; Eingang zeigt `audio: true` mit Transkript; Lotse-Entwurf zitiert es |
| MVC-2 | S1 TTS | chat-hub | `deploy/tts.py` (Piper, lazy import wie `stt.py`, Stimme per `CHAT_LOTSE_TTS_STIMME`, Ausgabe OGG/Opus 48 kHz mono); `make chat-lotse-tts-init` (Modell laden + `--selbsttest`); Eintrag in `deploy/raum-sessions/achim/session.env` | `tts.py --selbsttest` schreibt eine hörbare Datei < 5 s |
| MVC-3 | S2 Sender | chat-hub | `chat_lotse.py send-audio --text … [--antwort-auf EVENT]`: `client.upload(encrypt=True)` → `m.audio` mit `org.matrix.msc3245.voice` + `org.matrix.msc1767.audio.duration`; Outbox-Payload-Typ `audio` (bestehender Outbox-Weg C1 Z. 647–726) | Raum-Sitzung antwortet auf einen gesprochenen Auftrag zusätzlich per Audio; Owner hört es in Element |
| MVC-4 | S3 Vorlesen | chat-hub | `chat_lotse.py vorlesen --von @news-hub-bot --heute`: findet die Zeitung (Txn `morgenzeitung-*`), baut Sprechtext (D5), `send-audio --antwort-auf`; `lotse-vorlesen.timer` 06:45 UTC unter `deploy/`, gespiegelt wie `lotse-briefing` (C10) | Ein Werktag: Audio hängt als Antwort unter der Zeitung |
| MVC-5 | Deklaration | platform | `infra/ports.yaml`: Lotse-Sitzung dev-desktop trägt `stt`/`tts` als Bestandteile; Melder-Register unberührt (kein neuer Melder) | `ports.yaml`-Schema grün |

Sprechregel in der Raum-Sitzung (`brief.md`): Audio-Antwort **nur**, wenn der Auftrag per Audio kam
(S2) oder der Timer es verlangt (S3). Text bleibt immer dabei — Audio ergänzt, ersetzt nicht.

## Kill-Gate + Threshold

Siehe `kill_criteria` (Frontmatter). Exception-Budget: bis 2026-10-20 höchstens **3** Fehlläufe von
`vorlesen` ohne Log-Ursache; der vierte schaltet den Timer ab. ADR-Threshold: **kein ADR** — Addition
nach Muster #48; ein ADR-249-Amendment erst, wenn S4 (Vollduplex im Call) aufgenommen wird.

| Kriterium | Status | Beleg |
|---|---|---|
| ≥ 10 Owner-Sprachnachrichten transkribiert bis 2026-10-20 | offen | Eingang `audio: true` zählen |
| ≤ 2 von 10 Transkripten sinnentstellend | offen | Owner-Korrekturen im Raum (`regel`) |
| Zeitung an < 5 Werktagen in Folge ungehört | offen | Reaktion/Lese-Quittung unter dem Audio |

## Befunde (inkl. Advocatus Diabolus)

| # | Befund | Evidenz | Konsequenz |
|---|---|---|---|
| B1 | „Hören" war als Bauauftrag falsch gestellt: der Code existiert seit #48, es fehlte der Beweis | C1–C3 | MVC-1 ist Positivkontrolle, kein Bau |
| B2 | Diabolus: Zweite Wahrheit? TTS-Text ≠ Chat-Text möglich, wenn `vorlesen` kürzt | D5 | Sprechtext wird aus derselben Raum-Nachricht gebaut, nie aus der Datenbank; Kürzung ist Regel (Titel + Einordnung), keine Zusammenfassung per Modell |
| B3 | Diabolus: „sichtbar machen statt verhindern" — Sprache ohne Wecksilbe transkribiert jede Nachricht | C1 | Zwei-Personen-Raum; Wecksilbe (H2 der Liste) bewusst nicht gebaut, bis ein dritter Teilnehmer existiert |
| B4 | Diabolus: Piper-Stimme klingt synthetisch; Owner hört einmal und nie wieder | D2 | Kill-Gate misst genau das (5 Werktage ungehört); Kokoro als vorbereitete Stufe 2 |
| B5 | gx10 ist vom dev-desktop nicht erreichbar — die Vorschlagsliste hatte die gx10 als TTS-Host angenommen | C7 | D1 korrigiert; Liste wird nachgezogen |
| B6 | `stt.py` hat keinen Schutz gegen Whisper-Wiederholungsschleifen | C2, Plaud-Messung 2026-09-17 | R2-Guard in MVC-1 |

## Alternativen

| # | Alternative | Warum nicht |
|---|---|---|
| ALT-1 | Element Call + LiveKit Agent (Vollduplex, S4) | Eigenes Produkt (iil-voice-agent, ADR-249), Wochen; erst wenn Sprachnachrichten im Alltag angekommen sind (Kill-Gate hier) |
| ALT-2 | Cloud-TTS/STT (Plaud-Cloud, Azure, ElevenLabs) | Rauminhalte sind Aufträge und Post des Owners; Policy `llm-routing` und Datensouveränität — lokal reicht und kostet nichts |
| ALT-3 | Audio in news-hub erzeugen und per REST hochladen | Zweiter E2EE-Client auf dem Prod-Host, zwei Repos für eine Datei (D4) |

## Top-3-Risiken

1. **R1 Befehlskanal** — gedeckt durch Entwurf + Text-„go" (A2); Regel bricht, sobald ein Dritter im Raum ist.
2. **B4 Stimme unbrauchbar** — messbar, Kill-Gate; Kokoro vorbereitet.
3. **A3 Transkriptqualität `small`** — Env-Wechsel auf `medium` (CPU-Zeit ×3, bei 60 s Audio ≈ 20 s).

## Out-of-Scope (vertagt, Owner 2026-09-22)

- **P1** Frage statt Meldung („Ich könnte X — 👍 = go") — braucht Freigabe-Regel für Reaktionen (Board-Zug [28]).
- **S4** Gespräch im Element Call — eigenes Konzept unter ADR-249.
- **H2** Wecksilbe, **H3** Plaud-Aufnahme → Auftrag (nach KONZ-iil-voice-agent-004 Kill-Gate 2026-10-31).
