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
| Was im Anhang oder in der Mail des Empfängers schon steht | nur der Satz, der es einordnet — oder nichts | Wiederholung liest sich als Misstrauen und kostet die Aufmerksamkeit, die der neue Teil braucht |
| „X hat A gesagt, Sie sagen B, ich lege B zugrunde“ | die tragfähige Angabe verwenden, den Widerspruch im Vorgang festhalten | eine Mail ist kein Protokoll; Zeugenaussagen gegeneinanderstellen zwingt Dritte in eine Rolle, die sie nicht wollten |

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

**Der Regler kennt eine Gegenrichtung.** Alle drei Stufen zeigen nach unten; es gibt aber
einen Fall, in dem der Text wachsen muss: **wer das Ergebnis nicht selbst herleiten kann,
bekommt den Weg — auch bei `knapp`.** Am 2026-08-25 gab ein IT-Verantwortlicher eine reine
Sachauskunft und bekam darauf eine Rechtsfolge für seine Firma zurück; ohne die drei
Zwischenschritte war das ein Sprung. 90 → 259 Wörter, auf ausdrückliche Owner-Weisung.
Kürze ist ein Mittel gegen Ballast, kein Mittel gegen Begründung.

**Die Faktenregel gilt unabhängig vom Regler, auch bei `ausführlich`:** Jeder Fakt
muss entweder beantworten, was gefragt wurde, oder anstoßen, was wir brauchen.
Alles andere fliegt raus — **auch wenn es stimmt**. Ein Zusatzfakt, den ich nicht
belegen kann, wird zur **Frage**, nicht zum Satz.

---

## 3b — Issues, PRs, Antworten an den Owner

**Owner-Weisung 2026-08-26:** „viel zu umständlich formuliert — ich soll es lesen und
verstehen. Präzise auf den Punkt, unmissverständlich."

**Feste Form für Issue und PR:**

```
Titel      was sich ändert, aktiv, unter 70 Zeichen
Erste Zeile der Kern in einem Satz — was ist jetzt anders
Danach     höchstens fünf Zeilen: was drin ist, was offen bleibt
```

Mehr nicht. Was raus muss, auch wenn es stimmt:

- **Der Werdegang.** Was ich versucht habe, was blockiert wurde, in welcher
  Reihenfolge — interessiert niemanden, der den PR liest.
- **Die Prosa-Wiederholung des Diffs.** Wer den PR öffnet, sieht die Dateien.
- **Belegketten in Klammern.** Ein Link genügt, die Herleitung steht im Commit.
- **Selbstkommentare** („mein Vorschlag war an diesem Punkt zu weit"). Die
  Korrektur selbst ist die Aussage.
- **Motiv-Absätze**, die begründen, warum die Entscheidung richtig war. Sie liest
  nur, wer schon widerspricht — und der braucht das Gespräch, nicht den Absatz.

**Antworten im Kapitäns-Kanal:** Board zuerst (Regeln in `~/.claude/CLAUDE.md`),
darunter höchstens drei kurze Absätze. Ein Absatz sagt eine Sache. Steht dieselbe
Information schon im Board, wird der Absatz gestrichen, nicht umformuliert.

**Prüffrage vor dem Absenden:** Kann der Owner nach dem ersten Satz entscheiden?
Wenn nein, steht die Entscheidung zu weit hinten.

## 4 — Pre-Send-Selbstcheck

Vor dem Ablegen eines Entwurfs jede Zeile einmal gegen diese sechs Fragen:

1. Steht die Antwort im **ersten** Satz?
2. Ist jeder Fakt belegt — oder als Frage formuliert?
3. Spiegelt die Anrede die Gegenseite?
4. Echte Umlaute, keine Handumbrüche?
5. Trägt die Mail die richtige Signatur (IIL: §35a; Rolle setzt sie, nicht ich)?
6. Steht ein Satz drin, der nur erklärt, **warum** etwas so ist? → streichen.
7. Lässt ein Satz mit **Rechtsfolge oder Risikoaussage** eine zweite Lesart zu? → prüfe ihn
   gegen die *falsche* Lesart, nicht gegen die gemeinte. Bei „gilt einheitlich für beide“ ist
   „eine gemeinsame Registrierung“ die falsche Lesart — und sie ist die naheliegendere.

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
- 2026-08-23 · dsb · gestrichen: „Bogen 3 kommt teilweise vorher: Die Kontaktstelle in Teil 3 ist dieselbe Person wie die Meldestelle in Bogen 3“ → „Das Portal verlangt schon bei der Registrierung eine NIS2-Kontaktstelle … dieselbe Person, die im Meldeprozess die Meldestelle besetzt“ · Grund: Owner-Rückfrage „was heißt das?“ — „Teil 3“ meinte Bogen 1, „Bogen 3“ ein anderes Formular; **Nummern-Bezüge sind nur innerhalb eines Dokuments eindeutig, sonst die Sache benennen, nicht die Fundstelle**
- 2026-08-25 · hnu · gestrichen: „Die Fristwerte in P2 stehen als Referenzwerte unter Vorbehalt von Fachbereich 20 und Rechtsamt.“ + die Nummerierung der drei offenen Felder + „Wenn ihr am Zuschnitt etwas anders seht, telefonieren wir darüber.“ · Grund: „viel zu lang, aufs Wesentliche“ — der Vorbehalt stand zweimal im Anhang selbst; 110 → 43 Wörter
- 2026-08-25 · hnu · gestrichen: „P1 erzeugt das klassifizierte Dokument-Ereignis, auf dem P2 aufsetzt“ → „Der Dokumentenworkflow erzeugt das klassifizierte Dokument-Ereignis, auf dem das Fristenmanagement aufsetzt“ · Grund: Projektkürzel sind Binnensprache; der Empfänger liest ein Dokument, keine Projektablage
- 2026-08-25 · hnu · ersetzt: kompletter Entwurf mit Bescheid-Einordnung, Rechtsbehelfsfrist und vier Fragebogen-Befunden → vier Sätze mit der Bitte um Rückruf · Grund: der Owner hatte die Sache telefonisch geklärt — eine Mail, die einen anderen Kanal dupliziert, ist keine Kürzungsfrage, sondern überflüssig
- 2026-08-25 · dsb · gestrichen: die Aufzählung der sechs IT-Punkte und der Absatz „Herr Herrmann hat am 19. August das ERP als separate Installation beschrieben, Sie sagen das Gegenteil.“ · Grund: „nichts Bekanntes unnötig wiederholen, kein der hat gesagt und der hat gesagt“ — die sechs Punkte standen wörtlich in der Mail des Empfängers; 210 → 90 Wörter
- 2026-08-25 · dsb · gestrichen: „über den Lichtwellenleiter erreicht ein Vorfall im einen Werk das andere ohne Hürde“ → „nicht die Strecke ist der Punkt, sondern dass beide Netze eine Umgebung bilden … Trennung und Redundanz sind zwei verschiedene Baustellen“ · Grund: Owner-Rückfrage „ist ein Lichtwellenleiter nicht eher ein Risiko, 2 wäre besser weil redundant“ — ein Risikohinweis, der das Medium statt der Ursache benennt, provoziert die falsche Gegenmaßnahme
- 2026-08-25 · dsb · gestrichen: „Registrierung, Meldeprozess und Nachweise gelten einheitlich für beide.“ → „Er registriert sich eigenständig beim BSI … Der Verbund entscheidet nur darüber, ob er betroffen ist, nicht darüber, wer die Pflichten erfüllt.“ · Grund: Owner-Rückfrage „eigene Registrierung ist doch damit Pflicht oder?“ — „einheitlich für beide“ ließ die Lesart „eine gemeinsame Registrierung“ zu
- 2026-08-25 · dsb · ergänzt: dreischrittige Herleitung (Schwellenwerte allein nicht erreicht → Verbund-Betrachtung → Ausnahme scheitert an der IT), 90 → 259 Wörter · Grund: „bitte das nochmal darlegen (eigentlich nicht aber wegen Tochter schon)“ — die Kürzungsregel endet dort, wo der Empfänger das Ergebnis nicht selbst herleiten kann

---

- 2026-08-26 · intern · Weisung: „deine issues und PR sind viel zu umständlich formuliert … präzise auf den Punkt … unmissverständlich" · Grund: PR-Texte trugen Werdegang, Belegketten und Selbstkommentare; der Owner musste drei Absätze lesen, bevor er entscheiden konnte. Neue Form: § 3b.

- 2026-08-27 · dsb · gestrichen: „aus einer Akte mit zweihundert Seiten" → „aus rund zweihundert Akten und Dokumenten zu einer einzigen Person" · Grund: Owner-Korrektur „falsch: aus ca. 200 Akten / Dokumenten eines einzigen Bürgers" — die Zahl war richtig, die Einheit falsch; ein Rahmen-Satz, der die Sache des Empfängers falsch beschreibt, entwertet den ganzen Teaser, auch wenn alles Weitere stimmt. Vor dem ersten Satz eines Kundentexts die Sache beim Owner gegenprüfen, nicht aus dem Konzept ableiten

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
