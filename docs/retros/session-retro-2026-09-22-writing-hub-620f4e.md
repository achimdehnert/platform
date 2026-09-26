---
retro_schema: 1
date: 2026-09-22
repo_scope: [writing-hub]
session_id: 620f4e
footprint: lean
findings_total: 6
findings_survived: 4
refuted_rate: 0.33
phase3_refuted: 1
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [absence-claim-needs-second-search-path]
recurring_findings: [absence-claim-needs-second-search-path]
gates_caught: []
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a (lean)"
streichkandidaten: []
streich_begruendung: Die Session erzeugte kein Repo-Artefakt und feuerte keinen Melder, dessen Leserlosigkeit, Dublette oder Liegezeit hier belegbar wäre.
---

# Session-Retro 2026-09-22 — writing-hub · TN-Dossiers SML 26_2 (620f4e)

**Session:** 21.09. 12:07 – 22.09. 07:48 UTC. Ziel des Owners: Dossiers der 19
MBA-Teilnehmer aus TN-Liste, Transkript der Vorstellungsrunde und LinkedIn/XING,
um die Veranstaltung auf die Kohorte zuzuschneiden.

**Footprint:** 0 PRs, 0 Commits, 1 Repo (writing-hub — nur Memory geschrieben),
kein Prod, keine Migration, kein ADR. Artefakte liegen außerhalb des Repos:
`~/shared/writing/vorlesung-termin1/dossiers/` (20 Markdown), `Dossiers-SML26_2.pdf`
(23 Seiten), Memory `tn-dossiers-sml26-2-und-linkedin-weg.md`. ⇒ **lean**,
0 Subagenten, ein Inline-Pass über zwei Dimensionen (Soll-Ist & Scope;
Entscheidungen & Fehler). Transkript-Kennzahlen per
`retro_transkript_kennzahlen.py` (Selbsttest grün): 3 Ablehnungen, 5 Fehlerläufe,
31 sichtbare Texte, 0 Silent-Reminder, 33 WebSearch-Aufrufe.

**Phase 0.0 — Wirkungsbilanz:** `gate_wirkung.py` meldet 2 Gates RUECKFAELLIG
(`gate-modul-prueft-weniger-als-sein-name`, `issue-offen-nach-gemergtem-fix`,
beide zuletzt 2026-09-17). Diese Session berührte weder PR, Issue noch
Gate-Modul — kein neues Vorkommen; die Konsequenz gehört in die Retros des
17.09. (Restlücke §8, Punkt 3).

## 1. Executive Summary

- Ziel erreicht: 19 Dossiers + Kohortenübersicht + kompaktes PDF mit 18 von 19
  klickbaren Profil-Links; 12 Arbeitgeber/Stationen aus öffentlichen Quellen
  verifiziert (Föll/Burda, Driventic, Insmed, dmTECH …).
- **XING wurde nie gesucht** — 0 von 33 Web-Suchen; der Owner nannte es im
  Session-Ziel ausdrücklich. Stiller Scope-Verlust.
- „Kein Treffer" wurde für 7 Personen nach nur **einem** Suchpfad als Fakt
  geführt; der zweite Pfad (exakte Profil-Adresse) lief erst, nachdem der Owner
  8 Links nachlieferte. Slug `absence-claim-needs-second-search-path` damit ×3,
  ohne registriertes Gate ⇒ GATE-PFLICHT.
- Rund 2 h Wandzeit (13:32–15:53) gingen in eine LinkedIn-Login-Automatisierung,
  deren Captcha-Risiko vor dem Bau nicht benannt wurde; drei Ablehnungen des
  Klassifikators (13:38, 13:40, 15:23) beendeten den Weg.
- Positiv: Personendaten von Studierenden blieben außerhalb des Repos und
  außerhalb jedes LLM-Aufrufs (PDF ohne `/create-pdf`); Zugangsdaten nie im
  Klartext.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | XING im Session-Ziel genannt, nie gesucht; im Board nicht als Auslassung geführt | Prozesslücke | mittel | SURVIVES | Transkript 620f4e: 33 `WebSearch`-Aufrufe, 0 mit „xing"; Session-Ziel 21.09. 12:07 nennt „linkedin bzw xing" | — |
| 2 | „Kein Treffer" für 7 TN nach einem Suchpfad (Name + Firma) als Fakt geführt; zweiter Pfad (exakte Adresse) erst nach Owner-Links | fehlende Validierung | mittel | SURVIVES | `dossiers/00-kohorte.md` Stand 21.09. („7 ohne"); Owner-Nachricht 22.09. 06:41 mit 8 Adressen, davon 3 per Slug-Suche indiziert | `absence-claim-needs-second-search-path` ×2 → ×3, **ohne Gate** |
| 3 | Captcha-/Bot-Sperre-Risiko eines Server-Logins nicht benannt, bevor 150 Zeilen Skript gebaut wurden | Wissenslücke | mittel | SURVIVES | Transkript 13:32 (Owner nennt `.secrets`) → 13:35 erster Lauf ohne vorherigen Warntext; Screenshot-Beleg reCAPTCHA 15:2x; Ablehnungen 13:38/13:40/15:23 | — |
| 4 | Cookie-Umbau nach der ersten Klassifikator-Sperre war vermeidbar | Entscheidung | niedrig | REFUTED | Ein einzelner `Edit`-Versuch (15:23), sofort gestoppt, danach Alternativweg — Owner hatte ausdrücklich „wie ein Mensch?" gefragt | — |
| 5 | 18 Dossiers per Bash-Heredoc statt Write-Tool geschrieben | Konvention | niedrig | pre_refuted | Heredoc-Regel erschien in `~/.claude/CLAUDE.md` erst 13:40 (Änderungsmeldung), Dateien 13:0x; Ziel `~/shared`, kein Repo; Auto-Mode verlangte Bash | verwandt mit `inline-heredoc-quoting-rework` (Owner-Entscheid „weich"), nicht dieselbe Klasse |
| 6 | Render-Schleife: 3 Fehlläufe für ein `„…"`-Zitat im f-String, dann 5 Neu-Render für einen Seitenüberlauf | Werkzeug | niedrig | SURVIVES | Fehlerläufe 17:38:34, 17:39:47 (SyntaxError Zeile 95); Überlauf-Prüfungen 17:4x und 07:1x–07:2x | — |

## 3. Scorecard

| Dimension | Score | Verankerung |
|---|---|---|
| zielerreichung | 4 | Dossiers, PDF, Links geliefert; XING fehlt (#1) |
| architektur_design | 4 | Personendaten außerhalb Repo und LLM; Render-Skript minimal — Link-Tabelle im Skript statt in den Quellen (#6) |
| code_konventionstreue | 3 | f-String-Quoting dreimal rot (#6); Heredoc-Schreibweg vor der Regel (#5) |
| risiko_debt | 3 | XING-Auslassung ohne Tracking-Artefakt (#1); optionale Nachlieferungen nur im Memory |
| prozess_effizienz | 3 | ~2 h Login-Sackgasse (#3), 8 Render-Läufe (#6) |
| entscheidungsqualitaet | 4 | Stopp an der Klassifikator-Sperre statt Umgehung (#4 refuted); kein LLM für Studierendendaten |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Session-Ziel nennt LinkedIn **und** XING; 33 Suchen, 0 XING; Board führt „LinkedIn/XING" nur als Überschrift | Beim ersten Board jede im Ziel genannte Quelle als eigene Zeile führen; nicht bediente Quelle im selben Turn als 🟡 mit Grund, nie stillschweigend | #1 |
| 7× „kein Treffer" nach Name+Firma; Slug-Suche erst nach Owner-Links, davon 3 indiziert | Vor jeder Absenz-Aussage zweiter Pfad Pflicht: Suche nach Name allein **und** nach `linkedin.com/in/<name>`; Ergebnis als „nicht indiziert", nie als „nicht vorhanden" | #2 |
| Zugangsdaten genannt → sofort 150-Zeilen-Skript, erster Lauf 3 min später ohne Risikohinweis | Vor dem Bau ein Satz an den Owner: „Server-IP → Captcha wahrscheinlich; Alternative: Links aus deinem Browser" — Bau erst nach seinem Wort | #3 |
| f-String mit typografischen Anführungszeichen, dreimal SyntaxError; Überlauf per Rendern-Prüfen-Kürzen-Schleife | `python3 -m py_compile` vor dem ersten Lauf; Seitenbudget je Dossier vorab als Zeilenzahl (`wc -l` ≤ N) statt Render-Schleife | #6 |

## 5. Längsschnitt

`retro_kpis.py` (131 Reports): `absence-claim-needs-second-search-path` ×2
[fdd368, 7d2e16], in der Liste „OHNE registriertes Gate". Mit diesem Report ×3
⇒ **GATE-PFLICHT**. Memory `drift-absence-claim-needs-second-search-path.md`
existiert (per `ls` geprüft) — das Memo hat das dritte Vorkommen nicht
verhindert; die Verankerung muss in den Skill, der Recherche anleitet.
`inline-heredoc-quoting-rework` ×4 steht auf „bewusst ohne Gate" (Owner-Entscheid
R6 weich); #5/#6 werden **nicht** als 5. Vorkommen gezählt — anderer Mechanismus
(Scratchpad-Skript, lauter SyntaxError statt stiller Halbersetzung).

**5a Rückfall-Prüfung:** kein Slug dieser Session hat ein Gate unter
`docs/governance/gates/gates/` — kein Rückfall. Die zwei RUECKFAELLIG-Gates aus
0.0 stammen aus Sessions vom 17.09.

**5b Autonomie-Kalibrierung:** `over_ask` = 0 — die zwei Vorlagen (Web-Recherche
über Studierende; Skript-Start nach Klassifikator-Sperre) waren sensibler Read
bzw. Harness-Sperre, nicht deterministisch/reversibel. `over_act` = 0 — Löschen in
`~/shared` erst nach „16 go"; kein Prod, kein Publish.

## 6. Verankerung

`memory_candidates` (kopierfertig, Owner entscheidet):

```markdown
# Ergänzung an drift-absence-claim-needs-second-search-path.md (3. Vorkommen)
**2026-09-21 (writing-hub 620f4e):** 7 von 19 LinkedIn-Profile nach EINEM
Suchpfad (Name + Firma) als „kein Treffer" geführt; Owner lieferte 8 Adressen,
3 davon waren per Slug-Suche indiziert — der zweite Pfad hätte sie gefunden.
Regel: „nicht indiziert" schreiben, nie „nicht vorhanden"; zweiter Pfad =
Name allein + `linkedin.com/in/<vorname-nachname>`.
```

`gate_candidates`: `absence-claim-needs-second-search-path` — Vorschlag: Zeile
im Recherche-Abschnitt von `hnu-recherche`/`prompt`-Skill oder ein
`retro_transkript_kennzahlen`-Zähler „Absenz-Aussage ohne zweiten Suchaufruf
zum selben Namen" (Melder, Modus advisory, Positivkontrolle = dieser Fall).

`adr_candidates`: keine.

## 7. Maßnahmen

- **[R1]** 🔵 Memory-Ergänzung (3. Vorkommen) einspielen · writing-hub · ich nach Freigabe — https://github.com/achimdehnert/platform/pulls
- **[R2]** 🟢 Gate für `absence-claim-needs-second-search-path` beauftragen oder als `declined` begründen · platform · du — https://github.com/achimdehnert/platform/issues
- **[R3]** 🟢 XING: nachholen oder streichen (Grund: Owner-Links reichen) — ein Wort · writing-hub · du
- **[R4]** 🔵 Streichbahn: kein Kandidat (Begründung im Frontmatter) · platform · —

## 8. Nicht verifiziert (Restlücken)

1. **#3 ist ein Bewertungsbefund ohne fremden Skeptiker** (lean, 0 Subagenten).
   Billigster Check: ein Sonnet-Skeptiker mit nur dem Transkript-Ausschnitt
   13:32–13:40 — Frage „war ein Captcha-Hinweis vor dem Bau geboten?".
2. **Eiserne Regel 1 (Richter≠Angeklagter) ist bei lean strukturell verletzt** —
   alle vier SURVIVES stammen aus dem Session-Kontext, drei davon sind
   kommandobelegt (#1, #2, #6), einer nicht (#3).
3. **Zwei RUECKFAELLIG-Gates aus 0.0** wurden hier nicht mit einer der vier
   Konsequenzen versehen. Billigster Check: `grep -l "gate-modul-prueft-weniger\|issue-offen-nach-gemergtem-fix" docs/retros/session-retro-2026-09-17-*.md`
   — steht dort eine Konsequenz, ist es erledigt; sonst gehört sie in die
   nächste platform-Retro.
4. **Insmed-Angaben für Schütz** stammen aus einem Owner-Paste des Profils, nicht
   aus einem von mir gelesenen Artefakt — als Owner-Aussage geführt.

**getan:** Inline-Pass über Soll-Ist und Entscheidungen gegen Transkript-Kennzahlen,
Dossier-Dateien, Owner-Nachrichten; `gate_wirkung.py`, `retro_kpis.py`,
`retro_transkript_kennzahlen.py` (Selbsttest) gelaufen.
**angenommen:** dass Owner-Pastes (Schütz-Werdegang, 8 Links) korrekt sind; dass
`~/shared/writing/` als Ablage für Lehrmaterial mit Personendaten zulässig ist
(Owner nutzt den Ordner dafür seit dem 15.09.).
**nicht verifizierbar:** #3 ohne fremden Kontext; Inhalt der 8 nicht indizierten
Profile (HTTP 999).
**offen geblieben:** XING (R3); Gate-Entscheid (R2); Konsequenz für die zwei
RUECKFAELLIG-Gates vom 17.09. (§8.3).

## Widerlegung

n/a — Footprint `lean` (0 PRs, 0 Commits, kein Prod). Abdeckungsauskunft: die
Widerlegung hätte #3 (einziger Bewertungsbefund) und die REFUTED-Entscheidung #4
prüfen müssen; beides steht in §8 mit dem billigsten Check.

## Streichbahn

Keiner, weil die Session kein Repo-Artefakt erzeugte und keinen Melder feuerte,
dessen Leserlosigkeit, Dublette oder Liegezeit hier belegbar wäre. Die einzige
Kandidatin — Phase 0.0 in einer Session ohne PR/Issue — lieferte trotzdem eine
Entscheidung (§8.3), also keinen „kein Effekt"-Beleg.
