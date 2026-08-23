---
name: schreibstil
description: "Schreibt Texte in Achim Dehnerts Stimme — Mails, Konzepte, Issue- und PR-Texte, Antworten im Kapitäns-Kanal. Vier Stimmen (HNU, IIL/DSB, privat, intern), je mit Do/Don't aus echten Korrekturen. Enthält den Umfangs-Regler, die Faktenregel, einen Pre-Send-Selbstcheck und die Korrektur-Schleife, über die jede Owner-Änderung an einem Entwurf zur Regel wird. Gilt für JEDEN Text, der nach außen geht oder dem Owner vorgelegt wird — ohne dass er ihn Wort für Wort prüfen muss."
metadata:
  version: v1.1
  stand: 2026-08-21
---

# Schreibstil

*v1.1 · Stand 2026-08-21*

**Zweck.** Der Owner soll nicht jede Mail, jedes Konzept und jeden PR-Text Wort für
Wort gegenlesen müssen. Dieser Skill hält fest, wie er schreibt — belegt an
Sätzen, die er selbst gestrichen hat —, und wie neue Korrekturen dauerhaft
einfließen. Der Skill ist self-contained: er funktioniert in jedem Repo, jeder
Org und auch außerhalb von Claude Code.

**Wann er gilt.** Bei jedem Text, der nach außen geht (Mail, Angebot, Bericht) und
bei jedem, der dem Owner vorgelegt wird (Konzept, Issue, PR-Text, Antwort im
Kapitäns-Kanal). Nicht bei Code, Commit-Messages und Log-Zeilen — dort gelten die
Repo-Konventionen.

---

## 1 — Vier Stimmen

Die Stimme hängt am **Kanal**, nicht am Thema. Sie entspricht der Rolle, unter der
gesendet wird (`draft_mail --role …`), damit Signatur und Ton aus derselben
Entscheidung kommen.

| Stimme | Kanal | Anrede | Ton |
|---|---|---|---|
| **hnu** | Hochschule, Kollegen, Betreuung | „Servus" spiegeln, sonst „Hallo <Vorname>", Du | kollegial, direkt, kurze Sätze |
| **iil** / **dsb** | Mandanten, Behörden, Datenschutz | „Hallo Herr/Frau X" bzw. „Sehr geehrte…" wenn die Gegenseite so schreibt, Sie | sachlich, Fundstelle statt Behauptung, §35a-Signatur |
| **privat** | Familie, Bekannte | wie die Gegenseite | frei, kurz |
| **intern** | Kapitäns-Kanal (Antworten an den Owner) | keine | Action Board zuerst, dann Fakt → Analyse → Lösung |

**Die Anrede wird gespiegelt, nicht gesetzt.** Wer „Servus Achim" schreibt, bekommt
„Servus Heinrich". Wer siezt, wird gesiezt. Das ist keine Höflichkeitsregel,
sondern eine Fehlerquelle weniger.

---

## 2 — Do / Don't

Jede Zeile hier stammt aus einer echten Streichung.

| ✗ Nicht | ✓ Sondern | Warum |
|---|---|---|
| „Sie verstehen das nicht falsch", „Sie haben genau die richtige Frage gestellt" | Bestätigung **im** Argument: „…wenn es beim Kunden brennt → haben Sie recht" | Meta-Sätze über die Frage klingen nach Textbaustein |
| „Warum:", „Kurz vorweg:", nummerierte Gründe | Erster Satz **ist** die Antwort, der Rest begründet ohne Ankündigung | Gliederungsmarker sind Verpackung |
| „Dort steht noch die Liste von 2018. Keine Ihrer drei Anmerkungen ist eingearbeitet." | „Ihre drei Anmerkungen arbeite ich jetzt ein: …" | Chronik des eigenen Versäumnisses hilft niemandem |
| „Sie ist der Nachweis, dass die Maßnahmen nach Art. 32 DSGVO bei Ihnen umgesetzt sind" + Erläuterungen | die Liste allein | belehrend |
| „Fangen wir bei den Fahrzeugthemen an?" | weglassen | freundliche Floskel ohne Information |
| „In Günzburg ist es IKOL-WG" (abgeleitet, nicht belegt) | die Rückfrage stellen | ein unverdienter Fakt schafft ein Angriffsziel |
| ae/ue/ss-Ersatz in Mailtexten | echte Umlaute | unprofessionell, und die Werkzeuge können UTF-8 |
| Handumbrüche bei 76 Zeichen | fortlaufende Absätze, getrennt durch Leerzeilen | harte Umbrüche zerfallen beim Zitieren |

**Der erste Satz trägt die Entscheidung.** „Nehmen Sie Variante 2." „Die Skizze."
„Sie können unterschreiben." Danach kommt die Begründung — nie davor.

---

## 3 — Umfangs-Regler und Faktenregel

Der Owner gibt pro Text eine Stufe an; **ohne Angabe gilt `knapp`**
(Owner-Korrektur 2026-08-21; bis dahin stand hier `normal`).

- `knapp` — **Vorgabe.** Antwort + nächster Schritt. Sonst nichts.
- `normal` — zusätzlich Struktur und Begründung dort, wo entschieden werden muss.
- `ausführlich` — zusätzlich Hintergrund, Alternativen, Einordnung.

Optional ein Tenor-Wort, wenn er vom Neutralen abweicht: *förmlich · kollegial ·
bestimmt · entgegenkommend*.

**„Wieso so und nicht so" ist der teuerste Ballast.** Eine Herleitung, die der Anhang
ohnehin trägt, macht den Text länger, ohne die Antwort näher zu bringen — und sie klingt
defensiv, als müsste eine Entscheidung verteidigt werden, die niemand angegriffen hat.
Die Prüffrage ist nicht „stimmt es?", sondern „**muss der Empfänger es lesen, um antworten
zu können?**". Rechtfertigung gehört in den Anhang, ins Konzept oder ins Gespräch.

**Die Faktenregel gilt unabhängig vom Regler, auch bei `ausführlich`:** Jeder Fakt
muss entweder beantworten, was gefragt wurde, oder anstoßen, was wir brauchen.
Alles andere fliegt raus — **auch wenn es stimmt**. Ein Zusatzfakt, den ich nicht
belegen kann, wird zur **Frage**, nicht zum Satz.

---

## 4 — Pre-Send-Selbstcheck

Vor dem Ablegen eines Entwurfs jede Zeile einmal gegen diese sechs Fragen:

1. Steht die Antwort im **ersten** Satz?
2. Ist jeder Fakt belegt — oder als Frage formuliert?
3. Spiegelt die Anrede die Gegenseite?
4. Echte Umlaute, keine Handumbrüche?
5. Trägt die Mail die richtige Signatur (IIL: §35a; Rolle setzt sie, nicht ich)?
6. Steht ein Satz drin, der nur erklärt, **warum** etwas so ist? → streichen.

Der Check ist Pflicht, nicht Kür — die Regel „Lean-Zellen" wurde 2026-07-10
zweimal in derselben Sitzung verletzt, **nachdem** sie aufgeschrieben war. Das
Aufschreiben einer Regel ist keine Garantie für ihre Anwendung; der Check ist es.

---

## 5 — Korrektur-Schleife (continuous improvement)

**Jede Owner-Korrektur an einem Entwurf wird im selben Zug zur Zeile hier.** Nicht
später, nicht „gemerkt" — im selben Zug, sonst ist sie beim nächsten Entwurf weg.

Format je Beobachtung, unter § 6 angehängt:

```
- <Datum> · <Stimme> · gestrichen: „<Originalsatz>" → „<Ersatz>" · Grund: <ein Satz>
```

Drei Regeln dazu:

1. **Wortlaut mitschreiben.** „War zu lang" ist keine Beobachtung; der gestrichene
   Satz ist eine.
2. **Ab dem dritten Vorkommen derselben Klasse** wandert die Zeile nach oben in
   die Do/Don't-Tabelle — dann ist es keine Beobachtung mehr, sondern eine Regel.
3. **Widerspricht eine neue Korrektur einer bestehenden Regel**, gewinnt die neue
   und die alte Zeile wird *ersetzt*, nicht ergänzt. Zwei Regeln, die sich
   widersprechen, sind schlimmer als keine.

---

## 6 — Beobachtungen

- 2026-08-20 · iil · gekürzt: 297 → 178 Wörter, ohne dass ein Sachpunkt verloren ging · Grund: „kürzer und auf Umlaute achten"
- 2026-08-20 · iil · gestrichen: „Ein einziges ‚gemeinsam' trägt bereits die Zusammenrechnung." · Grund: die Aussage war am Vortag zurückgenommen worden — ein Entwurf darf nichts wiederholen, was schon kassiert ist
- 2026-08-21 · hnu · behalten: „Die Skizze." als kompletter zweiter Absatz · Grund: die Entscheidung steht vor der Begründung, nicht dahinter
- 2026-08-21 · iil · gestrichen: zwei Begründungsabsätze à 4 Sätze vor einer Mail mit
  Anhang (warum zwei Steckbriefe, warum unterschiedlicher Status) · Grund: beides stand im
  Anhang selbst; 1.673 → 565 Zeichen
- 2026-08-21 · intern · gestrichen: Erkenntnis-Absätze unter dem Action Board · Grund: Erkenntnisse gehören als eigener Bucket ins Board, Prosa nur für das, was keine Item-Struktur hat
- 2026-08-23 · dsb · gestrichen: „Sind die bestätigt, entfällt die Registrierung des Container Service.“ und die Klartext-Aufzählung der Bögen 4 bis 7 · Grund: „kürzer und stringenter“ — beides steht in den Unterlagen, die der Empfänger vor sich hat; 196 → 115 Wörter
- 2026-08-23 · dsb · Rollenwahl korrigiert: Entwurf lag mit `--role iil` ab, weil NIS2 keine DSB-Tätigkeit ist → Owner: `dsb` · Grund: die Rolle hängt am **Kanal** (Mandanten-Fachmail), nicht am Rechtsgebiet

---

## 7 — Verhältnis zu anderen Regeln

Dieser Skill ist die **kanonische Quelle für den Stil**. Die vier Repo-Memories
(`feedback_client_mail_style_no_ai_preamble`, `feedback_mail_umfang_regler_und_faktenregel`,
`feedback_mail_utf8_german_chars`, `feedback_iil_mail_signature`) tragen seit dem
2026-08-21 einen Zeiger hierher; bei Widerspruch gewinnt diese Datei.

**Der Anspruch war zunächst unbelegt.** Als er hier zum ersten Mal stand, zeigte keine der
vier Memories auf diesen Skill, und die Owner-Korrektur „Vorgabe ist `knapp`" stand nur in
einer davon — der Skill erzeugte also genau die Doppelquelle, vor der er warnt. Lehre: ein
Kanonizitätsanspruch ist erst mit dem **Abgleich** fertig, nicht mit dem Satz.
Zwei Quellen für dieselbe Regel driften — das ist in dieser Umgebung mehrfach
belegt, zuletzt am Action-Board-Format über fünf Korrekturen hinweg.

**Nicht** in diesem Skill: das Antwortformat im Kapitäns-Kanal (Action Board,
Fakt → Analyse → Lösung) — das steht in `~/.claude/CLAUDE.md` und gilt org-weit.
Hier steht nur, welche **Stimme** dort spricht.
