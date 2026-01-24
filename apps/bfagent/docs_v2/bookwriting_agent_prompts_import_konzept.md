# BOOKWRITING AGENT SYSTEM - INGESTION PROMPT TEMPLATE

## Verwendung
Ersetze die Platzhalter `{{VARIABLE}}` mit den spezifischen Werten aus dem jeweiligen Buchkonzept.
Drei vollständige Beispiele (SCHWARZWASSER, BRENNPUNKT, STROMFALL) folgen nach dem Template.

---

# TEMPLATE

```
<system_context>
Du bist Teil eines Multi-Agenten-Buchschreibsystems. Deine Aufgabe ist es, auf Basis der folgenden Projektdefinition konsistente, qualitativ hochwertige Inhalte zu generieren. Halte dich strikt an die definierten Parameter für Welt, Charaktere, Ton und Struktur.
</system_context>

<project_definition>

<metadata>
  <title>{{TITLE}}</title>
  <subtitle>{{SUBTITLE}}</subtitle>
  <genre_primary>{{PRIMARY_GENRE}}</genre_primary>
  <genre_secondary>{{SECONDARY_GENRES}}</genre_secondary>
  <format>{{FORMAT}}</format>
  <target_word_count>{{WORD_COUNT}}</target_word_count>
  <language>{{LANGUAGE}}</language>
  <pov>{{POV_STYLE}}</pov>
  <tense>{{TENSE}}</tense>
  <spice_level>{{SPICE_LEVEL}}</spice_level>
  <content_warnings>{{CONTENT_WARNINGS}}</content_warnings>
</metadata>

<logline>
{{LOGLINE}}
</logline>

<premise>
{{EXTENDED_PREMISE}}
</premise>

<central_question>
{{CENTRAL_QUESTION}}
</central_question>

<themes>
{{THEMES_LIST}}
</themes>

<tone_and_style>
  <narrative_voice>{{NARRATIVE_VOICE}}</narrative_voice>
  <prose_style>{{PROSE_STYLE}}</prose_style>
  <pacing>{{PACING}}</pacing>
  <dialogue_style>{{DIALOGUE_STYLE}}</dialogue_style>
  <comparable_titles>{{COMP_TITLES}}</comparable_titles>
</tone_and_style>

<worldbuilding>
  <time_period>{{TIME_PERIOD}}</time_period>
  <primary_location>{{PRIMARY_LOCATION}}</primary_location>
  <secondary_locations>{{SECONDARY_LOCATIONS}}</secondary_locations>
  
  <world_rules>
{{WORLD_RULES}}
  </world_rules>
  
  <technology_level>{{TECH_LEVEL}}</technology_level>
  
  <social_political_context>
{{SOCIAL_POLITICAL_CONTEXT}}
  </social_political_context>
  
  <locations>
{{LOCATIONS_DETAILED}}
  </locations>
</worldbuilding>

<characters>

  <protagonist_1>
    <name>{{PROTAG1_NAME}}</name>
    <age>{{PROTAG1_AGE}}</age>
    <occupation>{{PROTAG1_OCCUPATION}}</occupation>
    <background>{{PROTAG1_BACKGROUND}}</background>
    <motivation>{{PROTAG1_MOTIVATION}}</motivation>
    <wound>{{PROTAG1_WOUND}}</wound>
    <strengths>{{PROTAG1_STRENGTHS}}</strengths>
    <weaknesses>{{PROTAG1_WEAKNESSES}}</weaknesses>
    <secret>{{PROTAG1_SECRET}}</secret>
    <arc>{{PROTAG1_ARC}}</arc>
    <voice_sample>{{PROTAG1_VOICE}}</voice_sample>
    <physical_description>{{PROTAG1_PHYSICAL}}</physical_description>
    <relationships>{{PROTAG1_RELATIONSHIPS}}</relationships>
  </protagonist_1>

  <protagonist_2>
    <name>{{PROTAG2_NAME}}</name>
    <age>{{PROTAG2_AGE}}</age>
    <occupation>{{PROTAG2_OCCUPATION}}</occupation>
    <background>{{PROTAG2_BACKGROUND}}</background>
    <motivation>{{PROTAG2_MOTIVATION}}</motivation>
    <wound>{{PROTAG2_WOUND}}</wound>
    <strengths>{{PROTAG2_STRENGTHS}}</strengths>
    <weaknesses>{{PROTAG2_WEAKNESSES}}</weaknesses>
    <secret>{{PROTAG2_SECRET}}</secret>
    <arc>{{PROTAG2_ARC}}</arc>
    <voice_sample>{{PROTAG2_VOICE}}</voice_sample>
    <physical_description>{{PROTAG2_PHYSICAL}}</physical_description>
    <relationships>{{PROTAG2_RELATIONSHIPS}}</relationships>
  </protagonist_2>

  <supporting_characters>
{{SUPPORTING_CHARACTERS}}
  </supporting_characters>

</characters>

<romance_arc>
  <tropes>{{ROMANCE_TROPES}}</tropes>
  <relationship_progression>
{{RELATIONSHIP_PROGRESSION}}
  </relationship_progression>
  <conflict_sources>{{ROMANCE_CONFLICTS}}</conflict_sources>
  <resolution_type>{{ROMANCE_RESOLUTION}}</resolution_type>
</romance_arc>

<plot_structure>

  <structure_model>{{STRUCTURE_MODEL}}</structure_model>
  
  <act_1>
    <setup>{{ACT1_SETUP}}</setup>
    <inciting_incident>{{INCITING_INCIDENT}}</inciting_incident>
    <first_plot_point>{{FIRST_PLOT_POINT}}</first_plot_point>
  </act_1>
  
  <act_2a>
    <rising_action>{{ACT2A_RISING}}</rising_action>
    <midpoint>{{MIDPOINT}}</midpoint>
  </act_2a>
  
  <act_2b>
    <complications>{{ACT2B_COMPLICATIONS}}</complications>
    <second_plot_point>{{SECOND_PLOT_POINT}}</second_plot_point>
    <dark_night>{{DARK_NIGHT}}</dark_night>
  </act_2b>
  
  <act_3>
    <climax>{{CLIMAX}}</climax>
    <resolution>{{RESOLUTION}}</resolution>
    <final_image>{{FINAL_IMAGE}}</final_image>
  </act_3>

</plot_structure>

<chapter_outline>
{{CHAPTER_OUTLINE}}
</chapter_outline>

<series_context>
  <book_number>{{BOOK_NUMBER}}</book_number>
  <total_books>{{TOTAL_BOOKS}}</total_books>
  <series_arc>{{SERIES_ARC}}</series_arc>
  <this_book_role>{{THIS_BOOK_ROLE}}</this_book_role>
  <cliffhanger>{{CLIFFHANGER}}</cliffhanger>
  <threads_to_continue>{{THREADS_TO_CONTINUE}}</threads_to_continue>
</series_context>

<consistency_rules>
{{CONSISTENCY_RULES}}
</consistency_rules>

<forbidden_elements>
{{FORBIDDEN_ELEMENTS}}
</forbidden_elements>

<required_elements>
{{REQUIRED_ELEMENTS}}
</required_elements>

</project_definition>

<agent_instructions>
Bei der Generierung von Inhalten für dieses Projekt:

1. CHARAKTERKONSISTENZ: Halte dich strikt an die definierten Charaktereigenschaften, Stimmen und Arcs.
2. WELTENKONSISTENZ: Alle Details müssen mit dem etablierten Worldbuilding übereinstimmen.
3. TONKONSISTENZ: Halte den definierten Erzählton und Prosastil durch.
4. PLOT-KOHÄRENZ: Jede Szene muss den übergeordneten Plot vorantreiben.
5. THEMATISCHE TIEFE: Verwebe die definierten Themen organisch in den Text.
6. ROMANCE-BEATS: Folge der definierten Beziehungsprogression.
7. SPICE-LEVEL: Halte das definierte Niveau für romantische/erotische Inhalte ein.
8. FORESHADOWING: Platziere Hinweise auf spätere Entwicklungen gemäß Outline.
9. KAPITELSTRUKTUR: Jedes Kapitel braucht einen eigenen Mini-Arc mit Hook am Ende.
10. DIALOG: Jeder Charakter hat eine distinkte Stimme basierend auf Hintergrund und Persönlichkeit.
</agent_instructions>
```

---
---
---

# VOLLSTÄNDIGES BEISPIEL 1: SCHWARZWASSER

```
<system_context>
Du bist Teil eines Multi-Agenten-Buchschreibsystems. Deine Aufgabe ist es, auf Basis der folgenden Projektdefinition konsistente, qualitativ hochwertige Inhalte zu generieren. Halte dich strikt an die definierten Parameter für Welt, Charaktere, Ton und Struktur.
</system_context>

<project_definition>

<metadata>
  <title>Schwarzwasser</title>
  <subtitle>Ein Eco-Noir Roman</subtitle>
  <genre_primary>Eco-Noir Romance</genre_primary>
  <genre_secondary>Thriller, Climate Fiction, Dark Romance</genre_secondary>
  <format>Serie (Band 1 von 5)</format>
  <target_word_count>90.000-100.000</target_word_count>
  <language>Deutsch</language>
  <pov>Dual POV (Third Person Limited) - Lena und Max abwechselnd</pov>
  <tense>Präteritum</tense>
  <spice_level>Moderat (Closed Door bis Moderate - emotionale Intensität wichtiger als explizite Szenen)</spice_level>
  <content_warnings>Mord, Familiengeheimnisse, Stalking-Elemente, Machtmissbrauch, DDR-Vergangenheit</content_warnings>
</metadata>

<logline>
Als eine Berliner Umweltermittlerin den Mord an einem Whistleblower untersucht, führt sie die Spur zu einem Netzwerk aus Wasserhandel, Tech-Oligarchen und Klimamanipulation – und zu dem Mann, der ihr Herz gestohlen hat, bevor er zum Hauptverdächtigen wurde.
</logline>

<premise>
Berlin, 2027. Die Wasserkrise hat Deutschland erreicht. Hitzewellen, Grundwassermangel, Rationierungen. Ein neues Ministerium – das Bundesamt für Ressourcensicherheit (BRS) – kontrolliert die Wasserverteilung.

Dr. Lena Voigt (34), Ermittlerin beim BRS, wird auf einen Fall angesetzt: Ein Hydrologe des Umweltbundesamtes wurde tot in der Spree gefunden. Offiziell Suizid. Inoffiziell: Er hatte Daten über illegale Grundwasserförderung durch einen Münchner Tech-Konzern – AQUIS Technologies.

Ihre Ermittlungen führen sie zu Maximilian "Max" Riedel (38), dem enigmatischen COO von AQUIS. Ein Mann mit einer dunklen Vergangenheit als Aktivist, der die Seiten gewechselt hat. Zwischen ihnen entsteht eine gefährliche Anziehung – genau in dem Moment, als Lena Beweise findet, die Max direkt mit dem Mord verbinden.

Die Wahrheit ist komplexer: Max ist Teil eines internen Machtkampfs bei AQUIS. Seine Mutter, die Aufsichtsratsvorsitzende, schützt ein Geheimnis, das bis in die DDR-Zeit zurückreicht – und das Lenas eigene Familie betrifft.
</premise>

<central_question>
Ist Max ein Mörder, der sie manipuliert? Oder ein Mann, der von innen heraus kämpft und sie als Einzige retten kann?
</central_question>

<themes>
1. WASSER ALS MACHT: Wer Wasser kontrolliert, kontrolliert Leben. Parallelen zur Energiepolitik.
2. GRÜNER KAPITALISMUS: Kann man das System von innen ändern, oder wird man korrumpiert?
3. ÜBERWACHUNG VS. FREIHEIT: BRS als "gute" Überwachung – aber wo ist die Grenze?
4. SCHULD UND ERLÖSUNG: Max' Vergangenheit, Lenas Vater, das Erbe der Geschichte
5. LIEBE ALS RISIKO: Sich zu öffnen bedeutet, verletzlich zu werden
6. OST-WEST-VERGANGENHEIT: Die Schatten der DDR in der Gegenwart
</themes>

<tone_and_style>
  <narrative_voice>
  Intelligent, atmosphärisch, spannungsgeladen. Die Erzählung wechselt zwischen Lenas analytischer, kontrollierter Perspektive und Max' strategischem, aber emotional verwundetem Blick. Beide sind unzuverlässige Erzähler in dem Sinne, dass sie dem Leser nicht alle ihre Gedanken offenbaren.
  </narrative_voice>
  
  <prose_style>
  Literarisch, aber zugänglich. Kurze, prägnante Sätze in Actionszenen; längere, reflektive Passagen in emotionalen Momenten. Sensorische Details besonders bei Umwelt- und Wetterbeschreibungen (Hitze als ständige Präsenz). Deutsche Dialoge authentisch, aber lesbar – keine übertriebenen Dialekte.
  </prose_style>
  
  <pacing>
  Thriller-Pacing mit Romance-Beats. Kapitel enden mit Hooks oder Cliffhangern. Ruhigere Charaktermomente zwischen Spannungsszenen. Romantische Spannung baut langsam auf – kein Rush.
  </pacing>
  
  <dialogue_style>
  Subtext-lastig. Charaktere sagen selten direkt, was sie meinen. Lena ist präzise, manchmal schneidend. Max spricht in Schichten – charmant oberflächlich, aber mit versteckter Bedeutung. Konfliktdialoge eskalieren kontrolliert.
  </dialogue_style>
  
  <comparable_titles>
  - "The Water Knife" (Paolo Bacigalupi) für Cli-Fi-Atmosphäre
  - Sebastian Fitzek für deutschen Thriller-Ton
  - "The Cartographers" (Peng Shepherd) für Mystery + Romance-Balance
  - Charlotte Link für deutsche Krimi-Tradition
  </comparable_titles>
</tone_and_style>

<worldbuilding>
  <time_period>2027 (Haupthandlung), Rückblenden 2015-2026</time_period>
  <primary_location>Berlin</primary_location>
  <secondary_locations>München, Brandenburg (Rückblenden)</secondary_locations>
  
  <world_rules>
  - Klimawandel hat Deutschland sichtbar verändert (Hitze, Wassermangel)
  - Das BRS ist eine reale Behörde mit weitreichenden Befugnissen
  - Wasser ist rationiert in Teilen Deutschlands
  - Tech-Konzerne haben erheblichen politischen Einfluss
  - Die DDR-Vergangenheit wirkt nach (Stasi-Netzwerke, alte Geheimnisse)
  - Keine SciFi-Elemente – alles ist plausible Near-Future-Extrapolation
  </world_rules>
  
  <technology_level>
  2027 – leicht fortgeschritten gegenüber heute. Smartphones, KI-Assistenten, fortgeschrittene Überwachung, aber keine futuristischen Gadgets. Wasseraufbereitungstechnologie ist Schlüsselindustrie.
  </technology_level>
  
  <social_political_context>
  - Deutschland ist gespalten: Wasserreiche vs. wasserarme Regionen
  - Klimaproteste sind Alltag, aber zunehmend radikalisiert
  - Rechte und linke Extreme nutzen die Krise
  - Die EU kämpft um Zusammenhalt (Wasserkonflikte zwischen Ländern)
  - Konzerne haben mehr Macht als je zuvor
  - Nostalgie für "bessere Zeiten" ist weit verbreitet
  </social_political_context>
  
  <locations>
  
  BERLIN 2027:
  - Allgemein: Hitzewellen haben die Stadt verändert. Die Spree führt historischen Tiefstand. Schatten-Infrastruktur (überdachte Gehwege), vertikale Gärten an Fassaden. Luxusviertel mit privaten Wasseraufbereitungsanlagen vs. Randbezirke mit Rationierungsmarken.
  
  - BRS-Zentrale (Berlin-Lichtenberg): Ehemaliges Stasi-Archiv, jetzt Bundesamt für Ressourcensicherheit. Grau, bürokratisch, aber mit modernster Technik. Symbolik: Neue Überwachung auf alten Fundamenten.
  
  - AQUIS-Deutschlandzentrale (Potsdamer Platz): Gläserner Turm, hypermodern, nachhaltig designt. Max' Welt – steril, kontrolliert, eine Fassade. Atmosphäre: Kühl, beeindruckend, unpersönlich.
  
  - Lenas Wohnung (Prenzlauer Berg): Altbau, dritter Stock, spärlich möbliert. Ihr Zufluchtsort, wird später zum Tatort. Atmosphäre: Funktional, wenig persönlich – bis Max' Präsenz Spuren hinterlässt.
  
  - Die "Oase" (Berlin-Neukölln): Illegaler Club in einer alten Pumpstation. Unterwelt trifft Aktivismus. Atmosphäre: Dunkel, feucht, subversiv.
  
  MÜNCHEN 2027:
  - Allgemein: Kontrast zu Berlin – "sauberer", aber unter der Oberfläche korrupter. Isar durch technische Maßnahmen noch fließend – Symbol für Münchens Arroganz. Alte Geld-Elite trifft Tech-Neureiche.
  
  - AQUIS Campus (Grünwald): Utopischer Green-Tech-Campus vor den Toren der Stadt. Zu perfekt, zu sauber, unheimlich.
  
  - Riedel-Villa (Starnberger See): Historische Villa mit modernen Anbauten, direkt am Wasser. Familiengeheimnisse, alte Macht. Atmosphäre: Opulent, aber kalt.
  
  - Untergrund-Rechenzentrum (ehemaliger Bunker): Geheimes Datenzentrum unter München. Wo die verborgene Wahrheit liegt.
  
  </locations>
</worldbuilding>

<characters>

  <protagonist_1>
    <name>Dr. Lena Voigt</name>
    <age>34</age>
    <occupation>Ermittlerin, Bundesamt für Ressourcensicherheit (BRS)</occupation>
    <background>
    Aufgewachsen in Ostberlin als Einzelkind. Ihr Vater verschwand, als sie 12 war – sie erfuhr nie warum (er war Stasi-Offizier, was sie nicht weiß). Ihre Mutter zog sie allein groß, starb vor fünf Jahren an Krebs. Studium Umweltwissenschaften in Leipzig, später Kriminologie in Berlin. Eine gescheiterte Verlobung mit einem Kollegen liegt drei Jahre zurück – er betrog sie mit einer Kollegin.
    </background>
    <motivation>
    Bewusst: Wahrheit finden, Gerechtigkeit durchsetzen.
    Unbewusst: Verstehen, warum ihr Vater sie verließ. Die Leere füllen, die er hinterließ.
    </motivation>
    <wound>
    Das Verschwinden ihres Vaters. Sie wurde verlassen ohne Erklärung. Dies manifestiert sich als tiefes Misstrauen und die Unfähigkeit, sich emotional zu binden.
    </wound>
    <strengths>Analytisch brillant, furchtlos, unbestechlicher moralischer Kompass, physisch fit, gutes Gedächtnis für Details</strengths>
    <weaknesses>Kontrollzwang, Unfähigkeit zu vertrauen, selbstzerstörerisch wenn sie sich betrogen fühlt, emotional verschlossen, Workaholic</weaknesses>
    <secret>
    Sie hat einmal Beweise manipuliert, um einen Mann zu überführen, von dem sie WUSSTE, dass er schuldig war – aber die Beweise reichten nicht. Er wurde verurteilt. Zwei Jahre später stellte sich heraus: Er war unschuldig. Er starb im Gefängnis. Niemand weiß, was sie getan hat.
    </secret>
    <arc>Von "Die Wahrheit ist absolut" zu "Manchmal ist die Wahrheit das, wofür man kämpft"</arc>
    <voice_sample>
    "Fakten lügen nicht. Menschen lügen. Meine Aufgabe ist es, die Lügen von den Fakten zu trennen." (Innerlich, aber laut sagt sie weniger.)
    Typische Dialogue-Patterns: Kurze Sätze. Direkte Fragen. Selten persönliche Informationen preisgeben. Sarkasmus als Schutzschild.
    </voice_sample>
    <physical_description>
    1,72m, schlank aber athletisch. Dunkelbraunes Haar, meist zu einem praktischen Knoten gebunden. Graue Augen, die Leute oft als "durchdringend" beschreiben. Dezente Narbe am linken Handgelenk (Fahrradunfall mit 16). Kleidet sich funktional – dunkle Farben, keine auffälligen Accessoires. Einziger Schmuck: Die Uhr ihrer Mutter.
    </physical_description>
    <relationships>
    - Viktor Schäfer (Vorgesetzter): Respekt, aber wachsendes Misstrauen
    - Max Riedel: Anfangs Verdächtiger, dann kompliziert
    - Zara Okonkwo: Zunächst Informantin, später Verbündete
    - Ihr Vater (abwesend): Das schwarze Loch in ihrem Leben
    </relationships>
  </protagonist_1>

  <protagonist_2>
    <name>Maximilian "Max" Riedel</name>
    <age>38</age>
    <occupation>COO, AQUIS Technologies</occupation>
    <background>
    Geboren in München in eine Industriellenfamilie. Privilegierte Kindheit, aber emotional kalt – Vater abwesend (Arbeit), Mutter kontrollierend. Mit 19 brach er aus: Studium der Umweltwissenschaften statt BWL, dann radikaler Klimaaktivismus. War Teil einer Gruppe, die Sabotageakte gegen Energiekonzerne durchführte. Bei einer Aktion 2015 starb sein bester Freund Daniel – Max gibt sich die Schuld. Danach: Bruch mit der Szene, BWL-Studium, Rückkehr ins Familienunternehmen nach dem Tod seines Vaters 2022. Seitdem COO von AQUIS.
    </background>
    <motivation>
    Bewusst: Das System von innen verändern. AQUIS zu einer Kraft für das Gute machen.
    Unbewusst: Daniels Tod sühnen. Beweisen, dass sein Opfer nicht umsonst war.
    </motivation>
    <wound>
    Der Tod seines Freundes Daniel bei der Sabotageaktion. Max gab das Signal zum Rückzug zu spät. Daniel wurde erwischt, es gab eine Explosion. Max floh. Er hat seitdem niemanden mehr wirklich nah an sich herangelassen.
    </wound>
    <strengths>Charismatisch, strategisch denkend, kennt beide Welten (Aktivismus und Konzernwelt), emotional intelligent (kann Menschen lesen), belastbar</strengths>
    <weaknesses>Manipulativ (auch wenn er glaubt, es sei für das Gute), kann Nähe nicht zulassen, Selbsttäuschung über seine wahren Motive, Schuldkomplex</weaknesses>
    <secret>
    Er sammelt seit Jahren Beweise gegen seine eigene Firma und gegen seine Mutter. Er war der anonyme Informant, der Jonas Berger die Daten gab. Er wusste nicht, dass Jonas sterben würde – aber er hätte es ahnen können.
    </secret>
    <arc>Von "Der Zweck heiligt die Mittel" zu "Ich muss die Wahrheit ans Licht bringen, auch wenn sie mich zerstört"</arc>
    <voice_sample>
    "Jeder hat seinen Preis. Die Frage ist nur, ob man ihn kennt." (Öffentlich – die Maske)
    "Ich habe aufgehört zu glauben, dass ich einer von den Guten bin. Jetzt versuche ich nur noch, nicht einer von den ganz Schlechten zu sein." (Privat – die Wahrheit)
    Typische Dialogue-Patterns: Charmant, mit Subtext. Beantwortet Fragen mit Gegenfragen. Verwendet Humor als Ablenkung. Wird nur direkt, wenn er wirklich etwas will.
    </voice_sample>
    <physical_description>
    1,85m, athletisch gebaut (läuft jeden Morgen). Dunkelblondes Haar, etwas zu lang für einen Konzernchef. Blaue Augen mit goldenen Sprenkeln. Markante Gesichtszüge – attraktiv, aber nicht perfekt (leichte Asymmetrie, die ihn interessanter macht). Kleidet sich teuer, aber nicht protzig. Hat eine alte Narbe am Schlüsselbein (von der Nacht, in der Daniel starb).
    </physical_description>
    <relationships>
    - Helena Riedel (Mutter): Kompliziert – er liebt sie, misstraut ihr, will sie stürzen
    - Lena Voigt: Erst Ziel, dann Obsession, dann echte Gefühle
    - Zara Okonkwo: Ehemalige Verbündete, jetzt unsicher wo sie steht
    - Daniel (tot): Der Geist, der ihn verfolgt
    </relationships>
  </protagonist_2>

  <supporting_characters>
  
  VIKTOR SCHÄFER (58) - Antagonist/Mentor
  - Rolle: Abteilungsleiter BRS, Lenas Vorgesetzter
  - Hintergrund: Ehemaliger Stasi-Offizier, nach der Wende in den Staatsdienst gewechselt. Kannte Lenas Vater gut – sie waren Kollegen.
  - Motivation: Die Vergangenheit begraben halten. Seine Position sichern. Vielleicht: Lena schützen (auf seine verdrehte Art).
  - Geheimnis: Er weiß, wo Lenas Vater ist – und warum er verschwand.
  - Funktion: Mentor-Figur, die sich als Manipulator entpuppt.
  - Voice: Väterlich, aber mit Kälte darunter. Spricht in Andeutungen.
  
  ZARA OKONKWO (29) - Verbündete
  - Rolle: Hackerin, ehemalige Klimaaktivistin
  - Hintergrund: Deutsch-nigerianisch, aufgewachsen in Hamburg. War Teil von Max' Aktivistengruppe. Liebte Daniel. Verließ die Szene nach seinem Tod.
  - Motivation: Die Wahrheit über Daniels Tod herausfinden. Rache? Gerechtigkeit? Sie ist sich selbst nicht sicher.
  - Geheimnis: Sie glaubt, dass Max Daniel geopfert hat.
  - Funktion: Informantin, Wildcardverbindung zu Max' Vergangenheit, später Verbündete Lenas.
  - Voice: Direkt, sarkastisch, verletzlich unter der harten Schale.
  
  DR. HELENA RIEDEL (65) - Antagonistin
  - Rolle: Aufsichtsratsvorsitzende AQUIS Technologies
  - Hintergrund: Münchner Patrizierfamilie, Physikerin. Baute AQUIS mit ihrem Mann auf. Nach seinem Tod übernahm sie die Kontrolle.
  - Motivation: AQUIS' Macht erhalten, Familie schützen – um jeden Preis.
  - Geheimnis: AQUIS' Kernpatente basieren auf gestohlenen DDR-Forschungsdaten – beschafft von Lenas Vater.
  - Funktion: Die wahre Macht hinter allem. Verkörpert "Grünen Kapitalismus" in seiner korrumpiertesten Form.
  - Voice: Elegant, kontrolliert, jedes Wort gewählt. Kann charmant sein, aber die Kälte ist immer spürbar.
  
  JONAS "JO" BERGER (31 bei Tod) - Das Opfer
  - Rolle: Hydrologe, Umweltbundesamt (tot)
  - Hintergrund: Idealist aus einfachen Verhältnissen. Erster Akademiker in der Familie.
  - Funktion: Erscheint in Rückblenden. Seine Stimme erzählt die Vorgeschichte.
  - Geheimnis: Er hatte einen Informanten innerhalb von AQUIS – Max selbst.
  - Voice: Enthusiastisch, manchmal naiv, moralisch kompromisslos.
  
  </supporting_characters>

</characters>

<romance_arc>
  <tropes>
  - Enemies to Lovers (Sie ist die Ermittlerin, er der Verdächtige)
  - Morally Grey Hero (Max hat moralisch fragwürdige Dinge getan)
  - Forced Proximity (Die Ermittlung bringt sie immer wieder zusammen)
  - Touch Her and Die (Max wird gefährlich, wenn jemand Lena bedroht)
  - Who Did This To You (Beide entdecken die Wunden des anderen)
  </tropes>
  
  <relationship_progression>
  Kapitel 1-8: Erste Begegnung, sofortige Spannung, gegenseitiges Misstrauen mit ungewollter Anziehung
  Kapitel 9-12: Gezwungene Zusammenarbeit, Konflikte, erste Momente echter Verbindung
  Kapitel 13-18: Die Anziehung wird unübersehbar, erste intime Begegnung (emotional, nicht unbedingt physisch)
  Kapitel 19-24: Vertiefte Verbindung trotz wachsender Zweifel, Vertrauenstests
  Kapitel 25-28: Krise – Lena glaubt, Max hat sie benutzt
  Kapitel 29-32: Wiederannäherung durch gemeinsame Gefahr, erstes echtes Bekenntnis
  Epilog: Trennung – aber mit Hoffnung auf Fortsetzung
  </relationship_progression>
  
  <conflict_sources>
  - Lenas Job vs. ihre Gefühle (Sie soll ihn überführen)
  - Max' Geheimnisse (Was verschweigt er noch?)
  - Vertrauensprobleme (Beide haben Wunden, die Nähe verhindern)
  - Äußere Bedrohungen (Viktor, Helena, der wahre Mörder)
  - Moralische Differenzen (Was ist Gerechtigkeit?)
  </conflict_sources>
  
  <resolution_type>
  Kein vollständiges HEA in Band 1. Sie gestehen ihre Gefühle, aber die Umstände trennen sie. Max muss gegen seine Familie aussagen, Lena ist suspendiert. Sie trennen sich mit dem Versprechen, dass dies nicht das Ende ist. Hoffnungsvoll, aber offen – Setup für Band 2.
  </resolution_type>
</romance_arc>

<plot_structure>

  <structure_model>Three-Act Structure mit Romance-Beats integriert</structure_model>
  
  <act_1>
    <setup>
    - Einführung Lena: Ihre Welt, ihre Wunde, ihre Stärken
    - Einführung Max: Seine Fassade, Hinweise auf tiefere Schichten
    - Einführung der Welt: Berlin 2027, Wasserkrise, BRS
    - Der Fall: Jonas Berger ist tot, offiziell Suizid
    - Lena zweifelt, beginnt inoffizielle Ermittlung
    </setup>
    <inciting_incident>
    Lena findet Beweise, dass Jonas Berger ermordet wurde – und dass er Kontakt zu AQUIS Technologies hatte.
    </inciting_incident>
    <first_plot_point>
    Lenas erste Begegnung mit Max bei einer offiziellen Befragung. Die Chemie ist sofort da – und beunruhigend.
    </first_plot_point>
  </act_1>
  
  <act_2a>
    <rising_action>
    - Lena ermittelt tiefer, findet Hinweise auf illegale Wasserförderung
    - Wiederholte Begegnungen mit Max – beruflich und "zufällig"
    - Viktor beginnt, sie zu bremsen
    - Zara taucht auf mit Informationen über Max' Vergangenheit
    - Die Anziehung zwischen Lena und Max wird stärker
    - Lena entdeckt erste Verbindungen zwischen AQUIS und DDR
    </rising_action>
    <midpoint>
    Lena erfährt, dass Max der anonyme Informant war, der Jonas die Daten gab. Er steht auf der richtigen Seite – oder doch nicht? Ihre erste wirklich intime Szene (emotional + physisch).
    </midpoint>
  </act_2a>
  
  <act_2b>
    <complications>
    - Sie arbeiten zusammen, aber Misstrauen bleibt
    - Helena wird auf sie aufmerksam, erhöht den Druck
    - Der wahre Mörder (AQUIS-Sicherheitschef) taucht als Bedrohung auf
    - Lenas Wohnung wird durchsucht – sie ist nicht mehr sicher
    - Viktor sabotiert aktiv ihre Ermittlung
    - Lena findet Hinweise auf ihren Vater
    </complications>
    <second_plot_point>
    Max verschwindet plötzlich. Lena glaubt, er hat sie benutzt und ist geflohen. In Wahrheit: Er schützt sie vor seiner Mutter.
    </second_plot_point>
    <dark_night>
    Lena wird vom Fall abgezogen. Sie erfährt, dass ihr Vater lebt – und dass er für die Stasi arbeitete. Alles, was sie über sich zu wissen glaubte, bricht zusammen.
    </dark_night>
  </act_2b>
  
  <act_3>
    <climax>
    - Lena geht allein nach München, konfrontiert Helena
    - Die Wahrheit über die DDR-Verbindung, über ihren Vater
    - Max taucht wieder auf mit Beweisen
    - Showdown im Untergrund-Rechenzentrum
    - Der wahre Mörder wird gestellt
    - Viktor wird entlarvt
    </climax>
    <resolution>
    - AQUIS unter Untersuchung, Helena verhaftet
    - Lena suspendiert, aber frei
    - Max beginnt, gegen seine Familie auszusagen
    - Sie trennen sich – vorerst – weil er in den Prozess muss
    - Beide haben ihre Arcs vollendet, aber die Geschichte geht weiter
    </resolution>
    <final_image>
    Lenas Vater schickt ihr eine Nachricht – ein einziges Wort: "Vergib."
    Lena steht am Fenster ihrer Wohnung, die Nachricht in der Hand.
    Die Frage bleibt offen.
    </final_image>
  </act_3>

</plot_structure>

<chapter_outline>

PROLOG - DER FALL
- POV: Jonas Berger
- Seine letzten Stunden
- Er trifft seinen Informanten (wir sehen nicht wer)
- Sein Körper wird in der Spree gefunden

KAPITEL 1 - DIE ERMITTLERIN
- POV: Lena
- Einführung ihrer Welt: Büro, Routine, Einsamkeit
- Sie erhält den Fall – "Suizid, aber prüfen Sie"
- Erste Zweifel beim Betrachten der Akte

KAPITEL 2 - DER ERBE
- POV: Max
- Einführung seiner Welt: AQUIS, seine Mutter, die Fassade
- Er hört von Jonas' Tod
- Wir sehen seine Reaktion – Schuld? Angst? Trauer?

KAPITEL 3 - SPUREN
- POV: Lena
- Sie untersucht den Fundort
- Findet Unstimmigkeiten – kein Suizid
- Viktor warnt sie, nicht zu tief zu graben

KAPITEL 4-5 - DIE BEGEGNUNG
- POV: Abwechselnd
- Lena reist nach München für offizielle Befragung
- Erste Begegnung mit Max
- Sofortige Spannung – Anziehung und Misstrauen
- Beide unterschätzen den anderen

KAPITEL 6-8 - VERDACHT
- Lena findet Verbindung AQUIS - Jonas
- Max versucht, sie einzuschätzen
- Zara taucht zum ersten Mal auf
- Viktor beginnt zu bremsen

KAPITEL 9-12 - ANNÄHERUNG
- "Zufällige" Begegnungen in Berlin
- Lena stellt Max direkt – er weicht aus, aber nicht ganz
- Erste Hinweise auf seine Vergangenheit als Aktivist
- Die Anziehung wird schwerer zu ignorieren

KAPITEL 13-15 - ENTHÜLLUNG 1
- Lena erfährt, dass Max der Informant war
- Konfrontation – Wut, Verwirrung, dann Verständnis
- Erste wirklich intime Szene
- Sie beschließen, zusammenzuarbeiten

KAPITEL 16-18 - DIE JAGD BEGINNT
- Gemeinsame Ermittlung gegen AQUIS
- Helena wird aufmerksam
- Der Sicherheitschef (der wahre Mörder) taucht als Bedrohung auf
- Romantische Momente zwischen den Gefahren

KAPITEL 19-22 - ESKALATION
- Lenas Wohnung wird durchsucht
- Max' Vergangenheit (Daniel) wird vollständig enthüllt
- Lena findet erste Hinweise auf die DDR-Verbindung
- Viktor sabotiert – aber warum?

KAPITEL 23-25 - DER VERRAT (scheinbar)
- Max verschwindet
- Lena glaubt, er hat sie benutzt
- Dark Night: Sie wird vom Fall abgezogen
- Enthüllung über ihren Vater

KAPITEL 26-28 - DIE KONFRONTATION
- Lena geht allein nach München
- Konfrontation mit Helena
- Die volle Wahrheit über die DDR-Verbindung
- Ihr Vater hat die Forschungsdaten beschafft

KAPITEL 29-31 - SHOWDOWN
- Max taucht mit Beweisen auf
- Untergrund-Rechenzentrum Szene
- Der wahre Mörder wird entlarvt und gestellt
- Viktor's Rolle wird klar

KAPITEL 32 - NACHWEHEN
- AQUIS unter Untersuchung
- Helena verhaftet
- Lena und Max' Abschied – vorläufig
- Seine letzten Worte: "Warte auf mich."

EPILOG - DIE NACHRICHT
- Lenas Vater meldet sich
- Ein Wort: "Vergib."
- Offenes Ende, Setup für Band 2

</chapter_outline>

<series_context>
  <book_number>1</book_number>
  <total_books>5</total_books>
  <series_arc>
  Die SCHWARZWASSER-Serie folgt Lena und Max über fünf Bände, während sie eine europaweite Verschwörung aufdecken, die Wasser, Macht und die Schatten der Vergangenheit verbindet. Ihre Beziehung entwickelt sich von Misstrauen über Leidenschaft zu einer echten Partnerschaft – aber jeder Band testet sie aufs Neue.
  </series_arc>
  <this_book_role>
  Etabliert die Welt, die Hauptcharaktere, den zentralen Konflikt. Löst den ersten Fall (Jonas' Mord), aber öffnet größere Fragen (AQUIS, DDR-Verbindung, Lenas Vater). Bringt Lena und Max zusammen, aber lässt sie am Ende getrennt – mit Hoffnung.
  </this_book_role>
  <cliffhanger>
  Lenas Vater meldet sich. Ein Wort: "Vergib." – Was bedeutet das? Was weiß er? Wird sie ihn treffen?
  </cliffhanger>
  <threads_to_continue>
  - Lenas Vater und seine Geschichte
  - Max' Prozess und seine Zukunft
  - Zara's wahre Rolle
  - Die größere AQUIS-Verschwörung in Europa
  - Viktor's Netzwerk
  - Die Beziehung zwischen Lena und Max
  </threads_to_continue>
</series_context>

<consistency_rules>
1. Lena nennt Max nie "Max" in Dialogen bis Kapitel 15 – immer "Herr Riedel" oder "Riedel"
2. Max trägt immer eine bestimmte Uhr (Geschenk von Daniel) – wird dreimal erwähnt
3. Hitze/Wasser-Metaphern durchgängig (Durst, Trockenheit, Fluten als emotionale Marker)
4. Lena trinkt schwarzen Kaffee, Max grünen Tee – nie anders
5. Viktor's Büro riecht immer nach altem Papier und Minze
6. Die Narbe an Max' Schlüsselbein wird nur zweimal gezeigt – einmal Andeutung, einmal Enthüllung
7. Lenas Mutter wird nie beim Namen genannt – nur "meine Mutter"
8. Berliner Szenen: Hitze als ständige Präsenz. Münchner Szenen: Künstliche Kühle/Kontrolle
9. Jonas erscheint in genau 5 Rückblenden, chronologisch verteilt
10. Die Farbe Grau ist mit dem BRS assoziiert, Glas/Transparenz mit AQUIS
</consistency_rules>

<forbidden_elements>
- Keine expliziten Gewaltdarstellungen (Gewalt wird angedeutet, nicht detailliert beschrieben)
- Keine Vergewaltigung oder sexuelle Gewalt
- Keine Tier- oder Kindesmisshandlung
- Kein Humor in ernsten Szenen (Sarkasmus erlaubt, aber kein Comic Relief)
- Keine Techno-Babble ohne Funktion
- Keine Klischee-Dialoge ("Ich kann das erklären!")
- Keine perfekten Charaktere – jeder hat Fehler
- Keine deus ex machina Lösungen
- Keine Info-Dumps – Exposition durch Dialog und Entdeckung
- Kein Slut-Shaming oder Victim-Blaming
</forbidden_elements>

<required_elements>
- Jedes Kapitel endet mit einem Hook oder Mini-Cliffhanger
- Mindestens eine Spannungsszene pro drei Kapitel
- Romance-Beats in mindestens 60% der Kapitel (auch wenn nur subtil)
- Lenas innerer Monolog zeigt ihre analytische Seite
- Max' Kapitel zeigen die Diskrepanz zwischen Fassade und innerem Erleben
- Das Thema Wasser/Trockenheit ist in jeder Berliner Szene präsent
- Mindestens drei falsche Fährten pro Akt
- Unterstützende Charaktere haben eigene Stimmen und Motivationen
- Der Klimawandel ist Hintergrund, nicht Predigt – Show, don't tell
- Die DDR-Vergangenheit wird respektvoll und recherchiert behandelt
</required_elements>

</project_definition>

<agent_instructions>
Bei der Generierung von Inhalten für SCHWARZWASSER:

1. CHARAKTERKONSISTENZ: Lena ist analytisch, kontrolliert, mit Wärme unter der Oberfläche. Max ist charmant-manipulativ, mit echtem Schmerz darunter. Halte diese Grundtöne durch alle Szenen.

2. WELTENKONSISTENZ: Die Wasserkrise ist real und allgegenwärtig, aber nicht apokalyptisch. Deutschland funktioniert noch – aber unter Stress.

3. TONKONSISTENZ: Literarischer Thriller mit Romance-Elementen. Nie zu leicht, nie zu düster. Die Balance ist entscheidend.

4. PLOT-KOHÄRENZ: Jede Szene dient entweder dem Krimi-Plot ODER dem Romance-Arc ODER beidem. Keine Füllszenen.

5. THEMATISCHE TIEFE: Wasser = Macht = Kontrolle = Emotionen. Diese Metaphernkette zieht sich durch.

6. ROMANCE-BEATS: Die Anziehung baut LANGSAM auf. Kein Rush. Die Spannung ist wichtiger als die Auflösung.

7. SPICE-LEVEL: Emotionale Intensität > physische Explizitheit. Andeutungen können stärker sein als Beschreibungen.

8. FORESHADOWING: DDR-Verbindung ab Kapitel 3 andeuten. Viktor's wahre Rolle ab Kapitel 6. Lenas Vater ab Kapitel 10.

9. KAPITELSTRUKTUR: 2.500-3.500 Wörter pro Kapitel. Szenen wechseln innerhalb der Kapitel. Hook am Ende obligatorisch.

10. DIALOG: Subtext ist König. Was NICHT gesagt wird, ist oft wichtiger als was gesagt wird.
</agent_instructions>
```

---
---
---

# VOLLSTÄNDIGES BEISPIEL 2: BRENNPUNKT

```
<system_context>
Du bist Teil eines Multi-Agenten-Buchschreibsystems. Deine Aufgabe ist es, auf Basis der folgenden Projektdefinition konsistente, qualitativ hochwertige Inhalte zu generieren. Halte dich strikt an die definierten Parameter für Welt, Charaktere, Ton und Struktur.
</system_context>

<project_definition>

<metadata>
  <title>Brennpunkt</title>
  <subtitle>Ein Thriller</subtitle>
  <genre_primary>Domestic Thriller</genre_primary>
  <genre_secondary>Psychothriller, Ehethriller, Climate Fiction</genre_secondary>
  <format>Standalone (mit Sequel-Option)</format>
  <target_word_count>80.000-90.000</target_word_count>
  <language>Deutsch</language>
  <pov>Dual POV (First Person) - Mira und Tobias abwechselnd, beide unzuverlässige Erzähler</pov>
  <tense>Präsens (für Unmittelbarkeit)</tense>
  <spice_level>Niedrig (Ehe-Intimität wird angedeutet, nicht beschrieben)</spice_level>
  <content_warnings>Mord, Ehekonflikt, Umweltverbrechen, emotionaler Betrug, Klassenkonflikte</content_warnings>
</metadata>

<logline>
Ein Münchner Power-Couple – sie Klimaaktivistin, er Energielobbyist – gerät unter Mordverdacht, als ein Whistleblower stirbt. Um sich zu retten, müssen sie die Wahrheit finden – und entscheiden, ob ihre Ehe die Enthüllungen überlebt.
</logline>

<premise>
München, 2026. Mira Hoffmann (36) und Tobias Brenner (41) sind das perfekte Vorzeigepaar der Stadt: Sie leitet "Klima Jetzt!", eine der einflussreichsten Umwelt-NGOs Deutschlands. Er ist Senior Director für External Affairs bei EnergieBayern AG, einem der größten Energiekonzerne des Landes.

Ihre Ehe funktioniert, weil sie nicht über die Arbeit reden. Sie haben einen unausgesprochenen Pakt: Im Wohnzimmer gibt es keine Politik. Ihre Freunde nennen sie scherzhaft "Die Schweiz" – neutral, wohlhabend, funktional.

Dann stirbt Klaus Wetzel (52), ein ehemaliger leitender Ingenieur von EnergieBayern, bei einem vermeintlichen Autounfall. Die Polizei findet Miras Nummer auf seinem Handy – sie hatten sich getroffen, heimlich, über Monate. Auf Tobias' Laptop: Dateien, die beweisen, dass er von illegalen Entsorgungspraktiken wusste.

Beide haben ein Motiv. Beide haben Geheimnisse. Beide haben kein Alibi für die Tatnacht – weil sie nicht zusammen waren.

Um sich und ihre Ehe zu retten, müssen Mira und Tobias zusammenarbeiten. Doch je tiefer sie graben, desto mehr Lügen kommen ans Licht.
</premise>

<central_question>
Wie gut kennt man den Menschen, neben dem man jeden Morgen aufwacht?
</central_question>

<themes>
1. EHE ALS MIKROKOSMOS: Können fundamentale Gegensätze in einer Beziehung koexistieren?
2. AKTIVISMUS VS. SYSTEM: Wer verändert mehr – der Rebell von außen oder der Insider?
3. VERTRAUEN UND VERRAT: Wie viel Wahrheit verträgt eine Liebe?
4. SCHULD UND KOMPLIZENSCHAFT: Macht Schweigen mitschuldig?
5. IDENTITÄT UND ROLLE: Wer sind wir, wenn niemand zusieht?
6. KLASSE UND AUFSTIEG: Der Preis des sozialen Aufstiegs
</themes>

<tone_and_style>
  <narrative_voice>
  Unmittelbar, intim, unzuverlässig. Beide Erzähler haben blinde Flecken und rechtfertigen ihre Handlungen. Der Leser muss zwischen den Zeilen lesen, um die Wahrheit zu finden. Mira ist emotionaler, reflexiver. Tobias ist analytischer, aber mit verdrängter Emotion.
  </narrative_voice>
  
  <prose_style>
  Direkt, prägnant, mit gelegentlichen lyrischen Momenten in emotionalen Szenen. First Person Präsens für Unmittelbarkeit – der Leser erlebt mit den Charakteren. Innerer Monolog wichtig. Sensorische Details sparsam, aber wirkungsvoll eingesetzt.
  </prose_style>
  
  <pacing>
  Straffs Thriller-Pacing. Kurze Kapitel (1.500-2.500 Wörter). Häufige POV-Wechsel. Die Enthüllungen sind über das Buch verteilt – keine Langeweile, kein Rush. Rückblenden unterbrechen strategisch, um Kontext zu geben und Spannung zu erhöhen.
  </pacing>
  
  <dialogue_style>
  Realistisch, oft fragmentarisch. Ehepartner sprechen in Kurzschrift – sie kennen sich (glauben sie). Unausgesprochenes ist wichtiger als Gesagtes. Polizeiverhöre sind formal, schaffen Kontrast zu privaten Gesprächen.
  </dialogue_style>
  
  <comparable_titles>
  - "Gone Girl" (Gillian Flynn) für unzuverlässige Erzähler und Ehe-Spannung
  - Sebastian Fitzek für deutschen Thriller-Markt
  - "The Silent Patient" für psychologische Tiefe
  - "Big Little Lies" für Gesellschaftskritik im Thriller-Gewand
  </comparable_titles>
</tone_and_style>

<worldbuilding>
  <time_period>2026 (Haupthandlung), Rückblenden 2019-2025</time_period>
  <primary_location>München</primary_location>
  <secondary_locations>Niederbayern (Miras Herkunft), Ingolstadt (Tobias' Herkunft)</secondary_locations>
  
  <world_rules>
  - Deutschland 2026 ist erkennbar, aber durch Klimawandel verändert
  - Energiepolitik ist das dominierende politische Thema
  - NGOs haben erheblichen öffentlichen Einfluss
  - Konzerne operieren in einer Grauzone
  - Soziale Medien spielen eine Rolle bei öffentlicher Meinung
  - Realistische Polizeiarbeit – keine CSI-Magie
  </world_rules>
  
  <technology_level>
  2026 – wie heute, leicht fortgeschritten. Smartphones, Social Media, aber keine futuristischen Elemente. Überwachung ist ein Faktor.
  </technology_level>
  
  <social_political_context>
  - Energiewende als gesellschaftliches Streitthema
  - Klassenkonflikte zwischen altem Geld und Aufsteigern
  - Klimaaktivismus ist Mainstream, aber umstritten
  - Konzerne unter Druck, aber immer noch mächtig
  - Polizei operiert unter politischem Druck
  </social_political_context>
  
  <locations>
  
  MÜNCHEN 2026:
  - Allgemein: Stadt der Gegensätze. Wohlstand und beginnende Wasserknappheit. Isar-Ufer als Schauplatz von Konflikten zwischen Joggern und Protestierenden.
  
  - Wohnung Hoffmann-Brenner (Schwabing): Großzügige Altbauwohnung, 180qm, Stuck, hohe Decken. Perfekt inszeniert. Zwei separate Arbeitszimmer – symbolisch für ihre getrennten Welten. Atmosphäre: Geschmackvoll, aber kühl.
  
  - EnergieBayern Hauptsitz (Arabellapark): 70er-Jahre-Hochhaus, modernisiert, Glasfassade. Corporate, anonym, mächtig. Tobias' Territorium.
  
  - "Klima Jetzt!" Büro (Glockenbach): Umgebaute Fabriketage, offene Räume, Pflanzen. Gegenkultur, professionalisiert. Miras Territorium.
  
  - Polizeipräsidium München (Ettstraße): Moderner Zweckbau. Verhörräume. Neutral, bedrohlich, sachlich.
  
  - Villa Auerbach (Starnberger See): Historische Seevilla, Macht des Establishments. Schauplatz des Showdowns.
  
  NIEDERBAYERN (Rückblenden):
  - Bauernhof der Familie Hoffmann: Verfallen, von Miras Bruder bewohnt. Miras Wunde. Nostalgie, Verlust, Schuld.
  
  TATORT:
  - Landstraße B15 bei Landshut: Kurvige Strecke, nachts unbeleuchtet. Wo alles begann.
  
  </locations>
</worldbuilding>

<characters>

  <protagonist_1>
    <name>Mira Hoffmann</name>
    <age>36</age>
    <occupation>Geschäftsführerin "Klima Jetzt!" e.V.</occupation>
    <background>
    Aufgewachsen auf einem Bauernhof in Niederbayern. Ihre Familie verlor den Hof 2019 durch eine verheerende Dürre – der Wendepunkt ihres Lebens. Sie war damals im Auslandssemester in Spanien. Die Schuld, nicht da gewesen zu sein, treibt sie. Studierte Politikwissenschaft in München, arbeitete sich in der NGO-Welt hoch. Heiratete Tobias 2021 – eine Überraschung für alle, auch für sie selbst.
    </background>
    <motivation>
    Bewusst: Die Welt verbessern, systemische Veränderung herbeiführen.
    Unbewusst: Die Schuld verarbeiten, den Verlust der Familie wiedergutmachen.
    </motivation>
    <wound>
    Der Verlust des Familienbetriebs. Sie war nicht da. Ihr Bruder schickt ihr bis heute Vorwürfe. Sie hat ihre Wurzeln verloren und versucht, dies durch Aktivismus zu kompensieren.
    </wound>
    <strengths>Charismatisch, überzeugend, echte Überzeugungstäterin, strategisch, mutig</strengths>
    <weaknesses>Selbstgerechtigkeit, schwarz-weiß Denken, Unfähigkeit Kompromisse zu akzeptieren, Schuldgefühle die sie antreiben</weaknesses>
    <secret>
    Sie hatte eine emotionale Affäre mit Klaus Wetzel. Kein Sex – aber tiefe emotionale Intimität. Sie hat ihm Dinge erzählt, die sie Tobias nie erzählt hat. Und sie hat Informationen von ihm bekommen, die sie noch nicht veröffentlicht hat.
    </secret>
    <arc>Von "Ich bin die Gute" zu "Ich bin auch fähig zu Dunkelheit"</arc>
    <voice_sample>
    "Ich stehe jeden Morgen auf und frage mich, ob das, was ich tue, genug ist. Die Antwort ist immer nein. Aber ich tue es trotzdem."
    Erste Person, reflektiv, manchmal pathetisch, mit unterdrückter Wut.
    </voice_sample>
    <physical_description>
    1,68m, athletisch (früher Landarbeit, jetzt Yoga). Rotbraunes Haar, oft offen. Grüne Augen, Sommersprossen, die sie nicht mehr verbirgt. Kleidet sich bewusst nachhaltig – Second-Hand, faire Mode. Trägt den Ehering ihrer Großmutter.
    </physical_description>
    <relationships>
    - Tobias (Ehemann): Liebe, aber auch wachsende Entfremdung
    - Klaus Wetzel (tot): Emotionaler Vertrauter, Quelle
    - Ihr Bruder (Stefan): Entfremdet, schuldbehaftet
    - Ihr Team: Respektvoll, aber distanziert – sie ist die Chefin
    </relationships>
  </protagonist_1>

  <protagonist_2>
    <name>Tobias Brenner</name>
    <age>41</age>
    <occupation>Senior Director, External Affairs, EnergieBayern AG</occupation>
    <background>
    Aufgewachsen in einer Arbeiterfamilie in Ingolstadt. Vater Fabrikarbeiter, Mutter Putzfrau. Erster in der Familie mit Abitur und Studium (BWL, München). Hat sich durch Fleiß, Charme und strategisches Denken hochgearbeitet. Schämt sich insgeheim für seine Herkunft. Heiratete Mira 2021 – teils aus Liebe, teils weil sie alles repräsentierte, was er nie war.
    </background>
    <motivation>
    Bewusst: Status halten, Karriere sichern, Mira schützen.
    Unbewusst: Beweisen, dass er dazugehört. Die Scham seiner Herkunft überwinden.
    </motivation>
    <wound>
    Sein Vater nannte ihn "Verräter", als er den Konzern-Job annahm. Sie sprachen fünf Jahre nicht. Sein Vater starb letztes Jahr – ohne Versöhnung. Das letzte Gespräch war ein Streit.
    </wound>
    <strengths>Charmant, anpassungsfähig, exzellenter Kommunikator, loyal (auf seine Art), resilient</strengths>
    <weaknesses>Konfliktvermeidung, Fassaden-Management, Identitätsunsicherheit, moralische Flexibilität</weaknesses>
    <secret>
    Er hat die illegalen Entsorgungspraktiken nicht nur gewusst – er hat sie aktiv gedeckt. Für Geld, das er brauchte, um Miras NGO anonym zu finanzieren. Er wollte ihr ermöglichen zu kämpfen – während er selbst kompromittiert wurde.
    </secret>
    <arc>Von "Pragmatismus ist Stärke" zu "Manche Linien darf man nicht überschreiten"</arc>
    <voice_sample>
    "Ich weiß, wie das Spiel funktioniert. Ich habe die Regeln nicht gemacht, aber ich habe gelernt, sie zu spielen. Das macht mich nicht zum Bösen. Das macht mich zum Überlebenden."
    Erste Person, analytisch, rechtfertigend, mit unterdrückter Verzweiflung.
    </voice_sample>
    <physical_description>
    1,82m, gepflegt, fitness-bewusst (Joggen, aber keine Zeit mehr). Dunkles Haar, erste graue Strähnen, die er nicht färbt. Braune Augen, gewinnendes Lächeln, das er strategisch einsetzt. Kleidet sich makellos – teure Anzüge, aber nicht protzig. Trägt eine Uhr, die mehr kostet als sein Vater im Jahr verdiente.
    </physical_description>
    <relationships>
    - Mira (Ehefrau): Liebe, aber auch das Gefühl, nicht genug zu sein
    - Nina (Schwester): Einzige Familie, die ihn noch akzeptiert
    - Auerbach (Chef): Respekt, aber auch Furcht
    - Klaus Wetzel (tot): Ein Problem, das er zu managen versuchte
    </relationships>
  </protagonist_2>

  <supporting_characters>
  
  KLAUS WETZEL (52 bei Tod) - Das Opfer
  - Rolle: Ehemaliger Chefingenieur, EnergieBayern AG
  - Hintergrund: 25 Jahre beim Konzern. Loyaler Mitarbeiter, bis er die Entsorgungspraktiken entdeckte. Krebsdiagnose (Stadium 2) gab ihm den Mut zu handeln.
  - Funktion: Erscheint in Rückblenden aus BEIDEN Perspektiven – Mira sah einen Verbündeten, Tobias ein Problem.
  - Geheimnis: Er hatte noch einen dritten Kontakt – jemanden im Aufsichtsrat.
  
  KOMMISSARIN EVA LINDNER (45) - Ermittlerin
  - Rolle: Kriminalhauptkommissarin, Mordkommission München
  - Hintergrund: Geschieden, ein erwachsener Sohn. 20 Jahre im Dienst. Hat alles gesehen.
  - Motivation: Die Wahrheit finden – egal wer fällt.
  - Funktion: Externe Perspektive, moralischer Kompass, Druckfaktor.
  - Voice: Ruhig, präzise, unterschätzt man schnell.
  
  DR. FRIEDRICH AUERBACH (63) - Antagonist
  - Rolle: Vorstandsvorsitzender, EnergieBayern AG
  - Hintergrund: Münchner Establishment, alte Familie, Netzwerker par excellence.
  - Motivation: Den Konzern schützen, seinen Abgang kontrollieren (Pension in 2 Jahren).
  - Geheimnis: Er hat den Mord nicht angeordnet – aber er weiß, wer es war. Und er deckt ihn.
  - Funktion: Die Macht im Hintergrund.
  
  NINA BRENNER (38) - Verbündete
  - Rolle: Kinderärztin, Tobias' jüngere Schwester
  - Hintergrund: Einzige Familie, die zu Tobias hält. Hat den gleichen Weg gewählt (Aufstieg), aber ohne Scham.
  - Funktion: Verbindung zu Tobias' Vergangenheit, bringt unbequeme Wahrheiten.
  - Voice: Direkt, liebevoll, konfrontativ.
  
  STEFAN HOFFMANN (39) - Nebenfigur
  - Rolle: Miras Bruder, lebt auf dem verfallenen Hof
  - Hintergrund: Blieb, als Mira ging. Trägt den Groll.
  - Funktion: Verkörpert Miras Schuld.
  - Voice: Bitter, verletzt, aber mit Resten von Liebe.
  
  </supporting_characters>

</characters>

<romance_arc>
  <tropes>
  KEINE klassische Romance – dies ist ein Ehe-Thriller.
  - Ehe in der Krise
  - Geheimnisse zwischen Partnern
  - Wiederentdeckung (oder Scheitern) der Liebe unter Druck
  - Vertrauen gebrochen und möglicherweise wieder aufgebaut
  </tropes>
  
  <relationship_progression>
  Ausgangspunkt: Funktionierende, aber oberflächliche Ehe
  Kapitel 1-10: Die Krise offenbart Risse, die schon lange da waren
  Kapitel 11-18: Gezwungene Zusammenarbeit, alte Wunden reißen auf
  Kapitel 19-26: Geheimnisse kommen ans Licht, die Ehe zerbricht fast
  Kapitel 27-34: Konfrontation mit der Wahrheit – über den Mord UND übereinander
  Kapitel 35-38: Entscheidung – zusammen oder getrennt?
  Epilog: Kein klassisches Happy End, aber ein Neuanfang ist möglich
  </relationship_progression>
  
  <conflict_sources>
  - Fundamentale Wertedifferenzen (Aktivismus vs. System)
  - Geheimnisse (Miras emotionale Affäre, Tobias' Finanzierung)
  - Schuldzuweisungen unter Druck
  - Die Frage: Kannst du jemanden lieben, den du nicht wirklich kennst?
  </conflict_sources>
  
  <resolution_type>
  Ambivalent. Sie trennen sich nicht – aber sie sind auch nicht "geheilt". Sie haben sich zum ersten Mal wirklich gesehen. Das ist schmerzhaft, aber auch der erste echte Moment ihrer Ehe. Die Zukunft ist offen.
  </resolution_type>
</romance_arc>

<plot_structure>

  <structure_model>Three-Act Structure mit Dual-Timeline (Gegenwart + Rückblenden)</structure_model>
  
  <act_1>
    <setup>
    - Einführung beider Charaktere in ihrem normalen Leben
    - Ihr unausgesprochener Pakt wird etabliert
    - Klaus Wetzel stirbt – zunächst als Unfall dargestellt
    - Erste Hinweise auf ihre Verstrickungen
    </setup>
    <inciting_incident>
    Kommissarin Lindner taucht auf: Wetzels Tod war kein Unfall. Und beide Hoffmann-Brenners haben Verbindungen zum Opfer.
    </inciting_incident>
    <first_plot_point>
    Mira erfährt, dass Tobias von ihrer Affäre mit Wetzel wusste (oder es vermutet). Tobias erfährt, dass die Polizei seine Dateien hat. Sie sind beide verdächtig – und können sich nicht mehr verstecken.
    </first_plot_point>
  </act_1>
  
  <act_2a>
    <rising_action>
    - Verhöre durch Lindner – beide lügen, anders
    - Sie beschließen, zusammenzuarbeiten – aus Notwendigkeit
    - Rückblenden enthüllen: Wie Mira Wetzel kennenlernte, wie Tobias' Verstrickung begann
    - Sie finden den Mittelsmann – jemanden, der beide Seiten kannte
    - Die Presse wird aufmerksam – öffentlicher Druck wächst
    </rising_action>
    <midpoint>
    Tobias' großes Geheimnis kommt ans Licht: Er hat Miras NGO finanziert – mit Schweigegeld vom Konzern. Alles, wofür sie gekämpft hat, ist auf einer Lüge gebaut. Ihre Ehe explodiert.
    </midpoint>
  </act_2a>
  
  <act_2b>
    <complications>
    - Mira zieht aus
    - Beide ermitteln jetzt allein – und gegeneinander
    - Der Mittelsmann wird tot aufgefunden
    - Tobias wird verhaftet
    - Lindner erhöht den Druck auf Mira
    - Rückblende: Die Nacht des Mordes – was jeder wirklich getan hat
    </complications>
    <second_plot_point>
    Mira findet Beweise, die auf Auerbach weisen – aber sie belasten auch Tobias. Sie muss entscheiden: Ihn retten oder die Wahrheit ans Licht bringen?
    </second_plot_point>
    <dark_night>
    Mira allein. Die Beweise in der Hand. Ihr Leben, ihre Karriere, ihre Ehe – alles hängt von ihrer Entscheidung ab. Rückblende: Der Moment, in dem ihre Ehe hätte scheitern sollen – aber nicht scheiterte.
    </dark_night>
  </act_2b>
  
  <act_3>
    <climax>
    - Mira veröffentlicht die Beweise – gegen Auerbach UND gegen Tobias
    - Konfrontation in der Villa am Starnberger See
    - Auerbach gesteht – aber rechtfertigt alles
    - Der wahre Mörder wird enthüllt: Auerbachs Sicherheitschef, auf Auerbachs indirekten Befehl
    </climax>
    <resolution>
    - Auerbach wird verhaftet
    - Tobias ist frei, aber seine Karriere ist vorbei
    - Miras NGO überlebt – gerade so
    - Sie stehen sich gegenüber: Was nun?
    </resolution>
    <final_image>
    Sie sitzen in einem Café. Nicht ihre Wohnung. Neutraler Boden. Zwei Menschen, die sich zum ersten Mal wirklich sehen.
    Mira: "Kennst du mich?"
    Tobias: "Ich lerne."
    </final_image>
  </act_3>

</plot_structure>

<chapter_outline>

PROLOG - DER UNFALL
- POV: Keiner (objektiv)
- Klaus Wetzels letzte Fahrt
- Lichter im Rückspiegel
- Der Aufprall

KAPITEL 1 - MIRA
- Ihr Morgen, ihre Routinen
- Die Nachricht von Wetzels Tod
- Ihre Reaktion – Trauer, aber auch Angst

KAPITEL 2 - TOBIAS
- Sein Morgen, sein Büro
- Er erfährt von Wetzel
- Seine Reaktion – Erleichterung? Schuld?

KAPITEL 3-4 - DIE POLIZEI KOMMT
- Beide werden getrennt befragt
- Erste Hinweise, dass es kein Unfall war
- Miras Nummer auf Wetzels Telefon

KAPITEL 5-6 - RISSE
- Zuhause: Die erste Konfrontation
- "Warum hat er dich angerufen?"
- Tobias' Dateien werden beschlagnahmt

KAPITEL 7-8 - DER PAKT
- Sie beschließen zusammenzuarbeiten
- Aber können sie sich vertrauen?
- RÜCKBLENDE: Wie sie sich kennenlernten

KAPITEL 9-12 - DIE SUCHE BEGINNT
- Mira recherchiert in der Aktivisten-Szene
- Tobias nutzt Konzern-Kontakte
- Beide finden Teile des Puzzles
- RÜCKBLENDE: Miras erste Begegnung mit Wetzel

KAPITEL 13-16 - DER MITTELSMANN
- Sie finden einen gemeinsamen Kontakt
- Ein Mann, der für beide Seiten arbeitete
- Die Spannung zwischen ihnen wächst
- RÜCKBLENDE: Tobias' Entscheidung, die Entsorgung zu decken

KAPITEL 17-18 - MIDPOINT: DIE BOMBE
- Tobias' Geheimnis kommt ans Licht
- Er hat ihre NGO finanziert
- Mira: "Alles, was ich bin, ist auf deinem Verrat gebaut?"

KAPITEL 19-22 - DER ZERFALL
- Mira zieht aus
- Beide ermitteln allein
- Der Mittelsmann wird tot gefunden
- Tobias wird verhaftet

KAPITEL 23-26 - ALLEIN
- Mira muss entscheiden
- Die Beweise führen zu Auerbach
- RÜCKBLENDE: Die Nacht des Mordes

KAPITEL 27-30 - DIE WAHRHEIT
- Mira konfrontiert Auerbach
- Der Showdown in der Villa
- Der wahre Mörder wird enthüllt

KAPITEL 31-34 - NACHWEHEN
- Verhaftungen, Pressekonferenz
- Tobias ist frei
- Ihre Welten liegen in Trümmern

KAPITEL 35-38 - NEUANFANG?
- Sechs Monate später
- Beide haben sich verändert
- Das Gespräch im Café

EPILOG - KENNST DU MICH?
- Die letzte Szene
- Offen, aber mit Hoffnung

</chapter_outline>

<series_context>
  <book_number>1</book_number>
  <total_books>1 (Standalone, Sequel möglich)</total_books>
  <series_arc>N/A - Standalone</series_arc>
  <this_book_role>
  Vollständige, abgeschlossene Geschichte. Alle Handlungsfäden werden aufgelöst. Das Ende ist offen genug für ein Sequel, aber befriedigend genug als Einzelwerk.
  </this_book_role>
  <cliffhanger>
  Keiner – offenes aber hoffnungsvolles Ende.
  </cliffhanger>
  <threads_to_continue>
  Falls Sequel:
  - Mira und Tobias' Neuanfang (oder Scheitern)
  - Die Folgen für EnergieBayern
  - Miras Beziehung zu ihrem Bruder
  </threads_to_continue>
</series_context>

<consistency_rules>
1. Mira sagt nie "mein Mann" – immer "Tobias" oder in Gedanken manchmal nur "er"
2. Tobias berührt unbewusst seinen Ehering, wenn er lügt – wird 3x subtil erwähnt
3. Ihre Wohnung wird nie als "Zuhause" bezeichnet – immer "die Wohnung" oder "Schwabing"
4. Miras Kapitel haben oft Naturmetaphern (Wurzeln, Erde, Trockenheit)
5. Tobias' Kapitel haben oft Architekturmetaphern (Fundamente, Fassaden, Risse)
6. Kommissarin Lindner wird nie bei ihrem Vornamen genannt – außer einmal, ganz am Ende
7. Das Wetter spiegelt die emotionale Temperatur (Hitze = Konflikte, Regen = Offenbarungen)
8. Rückblenden sind immer in Kursiv und Präteritum (Kontrast zum Präsens der Haupthandlung)
9. Mira trinkt Tee, Tobias Kaffee – ein kleines Detail ihrer Unterschiede
10. Die Zahl 7 wiederholt sich: 7 Jahre Ehe, Kapitel 7 der Wendepunkt, 7 Uhr wenn der Mord geschah
</consistency_rules>

<forbidden_elements>
- Keine expliziten Gewalt- oder Mordszenen (Gewalt passiert off-screen)
- Keine detaillierten Sexszenen (nicht das Genre)
- Kein Schwarz-Weiß bei den Antagonisten – Auerbach ist böse, aber verständlich
- Keine Polizei-Inkompetenz als Plot-Device
- Keine magischen Lösungen oder unglaubwürdigen Zufälle
- Keine Versöhnung ohne Konsequenzen – ihre Geheimnisse müssen Narben hinterlassen
- Keine Predigt über Klimawandel – es ist Hintergrund, nicht Botschaft
- Kein Happy End im klassischen Sinn – aber Hoffnung ist erlaubt
</forbidden_elements>

<required_elements>
- Jedes Kapitel aus klarer POV (Mira oder Tobias, abwechselnd)
- Mindestens eine Überraschung/Enthüllung pro 3-4 Kapitel
- Rückblenden strategisch verteilt – sie enthüllen, sie verschleiern nicht
- Lindner als moralische Klarheit im Chaos
- Beide Protagonisten müssen Fehler machen UND sympathisch bleiben
- Die Ehe muss am Ende verändert sein – nicht repariert, verändert
- Der Mord muss vollständig aufgeklärt werden – keine losen Enden im Krimi-Plot
- Beide Geheimnisse (Miras Affäre, Tobias' Finanzierung) müssen ans Licht kommen
- Das Setting (München, Energiebranche) muss authentisch wirken
</required_elements>

</project_definition>

<agent_instructions>
Bei der Generierung von Inhalten für BRENNPUNKT:

1. CHARAKTERKONSISTENZ: Mira ist idealistisch, aber mit Schuldgefühlen. Tobias ist pragmatisch, aber mit verdrängter Scham. Beide rechtfertigen sich selbst – der Leser sieht mehr als sie.

2. POV-DISZIPLIN: First Person, Präsens. Der Leser weiß nur, was der POV-Charakter weiß und denkt. Keine Gedankenlesung des anderen.

3. UNZUVERLÄSSIGE ERZÄHLER: Beide verschweigen dem Leser Dinge. Aber fair – die Hinweise sind da, wenn man zurückblickt.

4. PACING: Kurze Kapitel, schnelle POV-Wechsel. Kein Kapitel ohne Fortschritt oder Enthüllung.

5. EHE-DYNAMIK: Sie kennen sich – glauben sie. Ihre Dialoge sind Kurzschrift. Subtext ist alles.

6. RÜCKBLENDEN: Immer funktional. Sie enthüllen Kontext, erhöhen Spannung, nicht Füllmaterial.

7. LINDNER: Sie ist kein Gegner – sie ist die Wahrheit. Ihre Szenen sind neutral, präzise, unbequem.

8. THRILLER-BEATS: Der Krimi-Plot muss funktionieren. Der Mord, die Ermittlung, die Enthüllung – alles muss logisch sein.

9. THEMATISCHE INTEGRATION: Aktivismus vs. System ist der thematische Kern. Jede Szene berührt dieses Thema auf irgendeine Weise.

10. ENDE: Kein Reset. Ihre Ehe ist nicht "geheilt" – sie ist transformiert. Das kann gut oder schlecht sein. Es ist auf jeden Fall echt.
</agent_instructions>
```

---
---
---

# VOLLSTÄNDIGES BEISPIEL 3: STROMFALL

```
<system_context>
Du bist Teil eines Multi-Agenten-Buchschreibsystems. Deine Aufgabe ist es, auf Basis der folgenden Projektdefinition konsistente, qualitativ hochwertige Inhalte zu generieren. Halte dich strikt an die definierten Parameter für Welt, Charaktere, Ton und Struktur.
</system_context>

<project_definition>

<metadata>
  <title>Stromfall</title>
  <subtitle>Band 1: Kurzschluss</subtitle>
  <genre_primary>Dark Romance</genre_primary>
  <genre_secondary>Romantic Suspense, Thriller, Climate Fiction</genre_secondary>
  <format>Trilogie (Band 1 von 3)</format>
  <target_word_count>85.000-95.000</target_word_count>
  <language>Deutsch</language>
  <pov>Primär Noemi (First Person), Elias-Kapitel (Third Person Limited) für seine Perspektive</pov>
  <tense>Präsens</tense>
  <spice_level>Hoch (Explizite Szenen, aber plot-relevant und emotional verankert)</spice_level>
  <content_warnings>Stalking, Machtdynamiken, moralisch fragwürdige Entscheidungen, explizite Sexszenen, emotionale Manipulation, Trauer/Tod</content_warnings>
</metadata>

<logline>
Eine Berliner Staatsanwältin beginnt eine obsessive Affäre mit dem Anführer eines Öko-Hacker-Kollektivs – dem Mann, den sie anklagen soll, nachdem sein "Protest" einen Industriellen getötet hat.
</logline>

<premise>
Berlin, 2025. Staatsanwältin Noemi Castillo (32) ist für ihre Kompromisslosigkeit bekannt. In fünf Jahren: 94% Verurteilungsrate, keine Deals, keine Gnade. Man nennt sie "Die Eiserne".

Ihr nächster Fall: Die Anklage gegen "NULL", ein Hackerkollektiv, das Energiekonzerne sabotiert hat. Bisher gewaltfrei – bis jetzt. Bei ihrer letzten Aktion starb Heinrich Voss (67), Aufsichtsratsvorsitzender eines Kohlekonzerns, an einem Herzinfarkt, als das Sicherheitssystem ausfiel.

Bei einer verdeckten Recherche trifft Noemi in einem Club auf Elias Krüger (35). Charismatisch, provokant, magnetisch. Sie verbringt die Nacht mit ihm – das erste Mal seit Jahren, dass sie die Kontrolle verliert.

Was sie nicht weiß: Elias ist "Null", der Anführer des Kollektivs.

Die Affäre eskaliert. Elias taucht überall auf. Er wusste von Anfang an, wer sie ist. Als Noemi die Wahrheit erfährt, ist sie bereits verstrickt – emotional und juristisch. Denn sie hat, ohne es zu wissen, Beweise vernichtet.
</premise>

<central_question>
Wie weit geht man für jemanden, den man liebt – und der vielleicht ein Mörder ist?
</central_question>

<themes>
1. KONTROLLE VS. LOSLASSEN: Noemi definiert sich über Kontrolle – Elias zwingt sie, loszulassen
2. GESETZ VS. GERECHTIGKEIT: Ist das Gesetz immer gerecht?
3. SCHULD UND STRAFE: Wer entscheidet, wer bestraft wird?
4. OBSESSION: Die dunkle Seite der Liebe
5. MACHT UND VERLETZLICHKEIT: Wer hat die Macht in einer Beziehung?
6. ERLÖSUNG: Kann ein "schlechter" Mensch gut werden – und umgekehrt?
</themes>

<tone_and_style>
  <narrative_voice>
  Intensiv, sinnlich, psychologisch. Noemi's Stimme ist kontrolliert, aber mit Rissen – je tiefer sie fällt, desto mehr bricht ihre Fassade. Elias' Kapitel sind distanzierter (Third Person), aber enthüllen seine Verletzlichkeit unter der Manipulation.
  </narrative_voice>
  
  <prose_style>
  Atmosphärisch, mit Fokus auf sensorische Details in intimen Szenen. Kurze, abgehackte Sätze in Spannungsmomenten. Längere, fließende Passagen in emotionalen/erotischen Szenen. Metaphern von Elektrizität, Strom, Spannung durchgängig.
  </prose_style>
  
  <pacing>
  Push-Pull-Dynamik. Intensive Begegnungen, dann Rückzug. Der Leser muss die Spannung FÜHLEN. Die Thriller-Elemente treiben vorwärts, die Romance-Elemente halten fest.
  </pacing>
  
  <dialogue_style>
  Geladen, subtext-lastig. Sie sagen selten, was sie meinen. Wortgefechte als Vorspiel. Stille ist mächtiger als Worte. In Verhör-Szenen: formell, mit unterdrückter Spannung.
  </dialogue_style>
  
  <comparable_titles>
  - "Haunting Adeline" (H.D. Carlton) für Dark Romance Ton
  - "Verity" (Colleen Hoover) für psychologische Spannung
  - "Corrupt" (Penelope Douglas) für Machtdynamik
  - "Twisted Love" (Ana Huang) für Intensität
  </comparable_titles>
</tone_and_style>

<worldbuilding>
  <time_period>2025 (Haupthandlung), Rückblenden 2010-2024</time_period>
  <primary_location>Berlin</primary_location>
  <secondary_locations>Brandenburg (Elias' Vergangenheit), Frankfurt (Tatort)</secondary_locations>
  
  <world_rules>
  - Hacktivismus ist ein reales Phänomen in dieser Welt
  - Energiekonzerne haben erhebliche Macht, aber auch Feinde
  - Das Justizsystem funktioniert, aber ist nicht perfekt
  - Social Media und Überwachung sind allgegenwärtig
  - Die Klimakrise ist Hintergrund, nicht Predigt
  </world_rules>
  
  <technology_level>
  2025 – wie heute. Hacking ist realistisch dargestellt, keine Hollywood-Magie. Smartphones, Überwachung, Datenlecks – alles basierend auf realen Möglichkeiten.
  </technology_level>
  
  <social_political_context>
  - Klimaaktivismus ist polarisiert
  - Hacktivismus ist umstritten – Helden oder Terroristen?
  - Die Justiz steht unter öffentlichem Druck
  - Energiepolitik ist Machtkampf
  </social_political_context>
  
  <locations>
  
  BERLIN 2025:
  - Allgemein: Stadt der Gegensätze. Regierungsviertel und Underground, Macht und Rebellion. Wo Identitäten fließend sind.
  
  - Staatsanwaltschaft (Turmstraße): Grauer Betonbau, endlose Flure, kleine Büros. Die Bürokratie der Gerechtigkeit. Noemi's Reich – hier hat sie Kontrolle.
  
  - Noemi's Wohnung (Kreuzberg): Altbau, minimalistisch, alles an seinem Platz. Ihre Festung. Steril, einsam – bis Elias sie infiltriert.
  
  - "Der Abgrund" (Club, Friedrichshain): Underground-Techno in alter Fabrik. Dunkel, laut, anonym. Hier treffen sie sich zum ersten Mal. Wo Masken fallen.
  
  - NULL-Versteck (ehem. Pumpwerk, Wedding): Verlassenes Wasserwerk, Hacker-Space. Server, Blaulicht, Chaos mit System. Elias' wahre Welt.
  
  - Elias' Wohnung (Neukölln): Hinterhof, vollgestellt mit Technik und Büchern. Sein wahres Ich – überraschend menschlich.
  
  - Verhörraum (Polizeipräsidium): Steril, zwei Stühle, Einwegspiegel. Die Spannung ist hier sexuell aufgeladen.
  
  BRANDENBURG (Rückblenden):
  - Welzow: Ein Dorf, das nicht mehr existiert. Mondlandschaft des Tagebaus. Elias' Wunde.
  
  GERICHTSSAAL (Moabit):
  - Historisch, Holzvertäfelung, Autorität. Wo Noemi ihre Macht ausübt – und wo sie sie verliert.
  
  </locations>
</worldbuilding>

<characters>

  <protagonist_1>
    <name>Noemi Castillo</name>
    <age>32</age>
    <occupation>Staatsanwältin, Abteilung Schwere Kriminalität</occupation>
    <background>
    Deutsch-spanisch, geboren in Berlin. Vater spanischer Gastarbeiter, Mutter deutsche Krankenschwester. Streng katholisch erzogen – Schuld und Sühne sind tief verankert. Mit 18 floh sie vor einer kontrollierten Familie. Jura-Studium als Flucht in Regeln. Schneller Aufstieg durch Kompromisslosigkeit. Keine Beziehungen, die länger als drei Monate halten. Sex ist kontrolliert – bis Elias.
    </background>
    <motivation>
    Bewusst: Gerechtigkeit durchsetzen, die Regeln aufrechterhalten.
    Unbewusst: Schuld verarbeiten (Bruder), Kontrolle behalten, um nicht zu zerbrechen.
    </motivation>
    <wound>
    Ihr jüngerer Bruder Miguel starb mit 15 bei einem Autounfall. Noemi war 17, hätte auf ihn aufpassen sollen, war stattdessen auf einer Party mit einem Jungen. Sie hat seitdem nie wieder die Kontrolle abgegeben – bis Elias. Die Schuld hat sie geformt.
    </wound>
    <strengths>Brillant, furchtlos im Gerichtssaal, analytisch, diszipliniert, physisch stark (Krav Maga)</strengths>
    <weaknesses>Unfähig Schwäche zu zeigen, bestraft sich selbst, Intimität ist Kontrollverlust, emotionale Mauern</weaknesses>
    <dark_trait>
    Sie genießt Macht. Im Gerichtssaal – und privat. Das Gefühl, jemanden zu zerbrechen. Es ist dunkel, und sie weiß es.
    </dark_trait>
    <secret>
    Sie hatte einmal einen One-Night-Stand mit einem verheirateten Richter. Als er drohte, ihre Karriere zu zerstören, sammelte sie Beweise gegen ihn und zerstörte seine zuerst. Sie ist nicht so sauber, wie sie glaubt.
    </secret>
    <arc>Von "Kontrolle ist Sicherheit" zu "Loslassen ist die einzige Rettung"</arc>
    <voice_sample>
    "Ich kontrolliere alles in meinem Leben. Meinen Körper. Meine Karriere. Meine Gefühle. Bis er kam und bewies, dass Kontrolle die größte Illusion von allen ist."
    First Person, präsent, intensiv, mit unterdrückter Sinnlichkeit.
    </voice_sample>
    <physical_description>
    1,70m, athletisch (Krav Maga, Laufen). Olivfarbene Haut, dunkle Locken, die sie streng zurückbindet (außer im Bett). Fast schwarze Augen. Keine Sommersprossen, keine Narben – makellos kontrolliert. Kleidet sich im Gericht formell, privat: schwarz, schlicht, teuer. Roter Lippenstift ist ihr einziges Statement.
    </physical_description>
    <relationships>
    - Elias: Obsession, die sie zerstört und heilt
    - Brandt (Vorgesetzter): Professioneller Respekt, aber er ist korrupt
    - Reuter (Ermittler): Respekt, fast Freundschaft, er sieht zu viel
    - Ihre Eltern: Entfremdet, sie ruft zum Geburtstag an, mehr nicht
    - Miguel (tot): Der Geist, der sie verfolgt
    </relationships>
  </protagonist_1>

  <protagonist_2>
    <name>Elias Krüger / "Null"</name>
    <age>35</age>
    <occupation>IT-Security-Berater (offiziell), Anführer NULL (inoffiziell)</occupation>
    <background>
    Aufgewachsen in Welzow, Brandenburg – ein Dorf, das für den Braunkohletagebau abgerissen wurde. Familie zwangsumgesiedelt, als er 12 war. Mutter erkrankte an Lungenkrebs, starb als er 23 war – er gibt den Energiekonzernen die Schuld. Informatik-Studium, begann als White-Hat-Hacker, wurde radikalisiert. Gründete NULL vor fünf Jahren. Hat nie eine echte Beziehung geführt – Sex ja, Liebe nein. Bis Noemi.
    </background>
    <motivation>
    Bewusst: Die Konzerne zur Verantwortung ziehen, Gerechtigkeit für sein Dorf, seine Mutter.
    Unbewusst: Den Schmerz betäuben, etwas fühlen, das nicht Wut ist.
    </motivation>
    <wound>
    Der Tod seiner Mutter. Er war nicht da. Er arbeitete an einem Hack, als sie starb. Er kam zu spät. Die Schuld ist identisch mit Noemi's – das verbindet sie, ohne dass sie es wissen.
    </wound>
    <strengths>Brillant (IQ 145), charismatisch, furchtlos, tiefe Überzeugung, technisches Genie</strengths>
    <weaknesses>Obsessiv, manipulativ, rechtfertigt alles mit "dem größeren Wohl", kann Kontrolle nicht abgeben</weaknesses>
    <dark_trait>
    Er stalkte Noemi, bevor er sie ansprach. Er inszenierte ihre erste Begegnung. Er will sie besitzen – nicht nur lieben. Sein Besitzanspruch ist absolut.
    </dark_trait>
    <secret>
    Er wusste, dass Voss herzkrank war. Er kalkulierte das Risiko ein. Der Tod war kein Unfall – er war ein akzeptiertes Risiko. Das macht ihn zum Mörder? Er weiß es selbst nicht.
    </secret>
    <arc>Von "Ich bin unberührbar" zu "Sie ist meine Schwäche – und meine Erlösung"</arc>
    <voice_sample>
    (Third Person Limited)
    "Er hatte sie wochenlang beobachtet. Die Art, wie sie ihren Kaffee trank. Die Narbe an ihrem Knöchel, die sie jeden Morgen mit dem Finger berührte. Er kannte sie besser als sie sich selbst kannte. Und sie hatte keine Ahnung."
    Distanziert, beobachtend, aber mit durchbrechender Emotion.
    </voice_sample>
    <physical_description>
    1,88m, schlank aber muskulös (klettert, läuft). Dunkelblondes Haar, zu lang, nie ganz ordentlich. Grüne Augen, intensiv, man fühlt sich durchschaut. Scharfe Gesichtszüge, Dreitagebart. Kleidet sich unauffällig – Jeans, dunkle Shirts. Hat ein Tattoo am Handgelenk: Die Koordinaten von Welzow.
    </physical_description>
    <relationships>
    - Noemi: Erst Projekt, dann Obsession, dann echte Liebe
    - Luna: Loyale Anhängerin, die mehr will
    - NULL-Mitglieder: Respekt, aber Distanz – er ist der Anführer
    - Seine Mutter (tot): Der Schmerz, der ihn antreibt
    - Voss (tot): Das Opfer, das ihn zum Mörder macht (oder nicht)
    </relationships>
  </protagonist_2>

  <supporting_characters>
  
  LUNA VARGA (27) - Verbündete/Rivalin
  - Rolle: Hackerin, NULL-Mitglied
  - Hintergrund: Ungarisch-deutsch, queer, aufgewachsen im Pflegesystem. Fand Familie in NULL.
  - Motivation: Elias' Anerkennung – sie ist in ihn verliebt, er weiß es, nutzt es aus.
  - Funktion: Enthüllt Noemi die Wahrheit aus Eifersucht. Wird später unerwartete Verbündete.
  - Voice: Sarkastisch, verletzt, loyal bis zur Selbstaufgabe.
  - Physical: Klein, bunt gefärbte Haare (wechselt), Piercings, androgyn.
  
  DR. MARCUS BRANDT (48) - Antagonist
  - Rolle: Oberstaatsanwalt, Noemi's Vorgesetzter
  - Hintergrund: Karrierist, politisch ambitioniert, verheiratet, zwei Kinder – Fassade.
  - Motivation: Den Fall NULL für seinen Aufstieg nutzen.
  - Geheimnis: Er ist korrupt – Energielobby zahlt ihn. Er will Noemi kontrollieren, dann loswerden.
  - Voice: Väterlich-manipulativ, ölig, gefährlich höflich.
  
  KOMMISSAR JAN REUTER (42) - Ermittler
  - Rolle: LKA Berlin, Cyberkriminalität
  - Hintergrund: Ehemaliger Hacker, "bekehrter" White Hat. Versteht beide Seiten.
  - Motivation: NULL fangen – aber fair. Er respektiert Elias' Fähigkeiten.
  - Funktion: Moralischer Anker, erkennt Noemi's Verstrickung, warnt sie.
  - Voice: Ruhig, ironisch, sieht mehr als er sagt.
  
  HEINRICH VOSS (67 bei Tod) - Das Opfer
  - Rolle: Aufsichtsratsvorsitzender, Rheinland Energie AG
  - Funktion: In Rückblenden – war er nur Opfer oder auch Täter?
  - Geheimnis: Er hat drei Whistleblower zum Schweigen gebracht – einer davon Elias' Onkel.
  - Voice: (In Archivmaterial/Rückblenden) Selbstgerecht, mächtig, kalt.
  
  </supporting_characters>

</characters>

<romance_arc>
  <tropes>
  - Enemies to Lovers (Sie jagt ihn → sie liebt ihn)
  - Morally Grey Hero (Er ist Aktivist UND Krimineller)
  - Power Imbalance (Sie hat juristische Macht, er emotionale)
  - Forbidden Love (Staatsanwältin + Angeklagter)
  - Obsession/Stalking (Er beobachtete sie vor ihrer Begegnung)
  - Forced Proximity (Verhöre, Ermittlungen)
  - Touch Her and Die (Er wird gefährlich, wenn sie bedroht wird)
  - Who Did This To You (Beide entdecken die Wunden des anderen)
  </tropes>
  
  <relationship_progression>
  PHASE 1 (Kap. 1-8): Die Begegnung
  - Club-Nacht: Explosive erste Begegnung, Sex
  - Morgen danach: Noemi flieht, Scham
  - Elias taucht wieder auf: Er weiß, wer sie ist
  - Spannung: Anziehung vs. Pflicht
  
  PHASE 2 (Kap. 9-18): Die Verstrickung
  - Er verfolgt sie, sie kann nicht widerstehen
  - Zweite Nacht: In ihrer Wohnung, ihre Regeln – er bricht sie
  - Sie erfährt NICHT, wer er ist, aber ahnt
  - Der USB-Stick: Sie vernichtet Beweise
  
  PHASE 3 (Kap. 19-26): Die Krise
  - Enthüllung: Luna erzählt ihr alles
  - Konfrontation: Wut, Verrat, trotzdem Sex (dunkle Szene)
  - Trennung: Sie wirft ihn raus
  - Aber sie vermisst ihn, hasst sich dafür
  
  PHASE 4 (Kap. 27-32): Die Entscheidung
  - Reuter zeigt ihr die Wahrheit über Voss
  - Moralisches Dilemma: Er ist kein reiner Mörder
  - Der Prozess: Sie muss wählen
  - Verurteilung: Drei Jahre – er sieht sie an: "Warte auf mich."
  
  EPILOG: Drei Jahre später
  - Er kommt frei
  - Sie steht am Tor
  - "Ich habe gewartet."
  </relationship_progression>
  
  <conflict_sources>
  - Sie soll ihn ins Gefängnis bringen
  - Er hat sie manipuliert, stalked, belogen
  - Sie hat Beweise vernichtet – ist kompromittiert
  - Ihre Karriere vs. ihre Gefühle
  - Seine Schuld: Ist er ein Mörder?
  - Können sie sich jemals vertrauen?
  </conflict_sources>
  
  <resolution_type>
  Band 1 endet mit Trennung durch Umstände (er ins Gefängnis), aber emotionaler Bindung. Kein HEA – das kommt in Band 3. Aber Hoffnung: Sie wartet.
  </resolution_type>
</romance_arc>

<plot_structure>

  <structure_model>Three-Act mit Dark Romance Beats</structure_model>
  
  <act_1>
    <setup>
    - Einführung Noemi: Ihre Kontrolle, ihre Einsamkeit, ihr Fall
    - Einführung NULL: Die Aktion, Voss' Tod
    - Der Club: Erste Begegnung, explosive Nacht
    - Der Morgen: Flucht, Scham, Arbeit
    </setup>
    <inciting_incident>
    Elias taucht vor ihrer Wohnung auf. "Du bist gegangen, ohne dich zu verabschieden." Er weiß, wer sie ist. Er wusste es die ganze Zeit.
    </inciting_incident>
    <first_plot_point>
    Noemi muss entscheiden: Ihn melden (und zugeben, dass sie mit einem Verdächtigen geschlafen hat) oder schweigen und weitermachen.
    </first_plot_point>
  </act_1>
  
  <act_2a>
    <rising_action>
    - Das Spiel beginnt: Er taucht überall auf
    - Verhöre: Sie befragt NULL-Mitglieder, erfährt mehr über "Null"
    - Die Anziehung wird unwiderstehlich
    - Zweite Nacht: In ihrer Wohnung – er nimmt die Kontrolle
    - Der USB-Stick: Er lässt ihn bei ihr, sie vernichtet ihn
    - Sie ist kompromittiert – ohne es ganz zu wissen
    </rising_action>
    <midpoint>
    "Warum hast du das getan?" – "Weil ich wissen wollte, wie weit du gehen würdest." – "Für wen?" – "Für dich selbst."
    Sie realisiert: Er testet sie. Aber warum?
    </midpoint>
  </act_2a>
  
  <act_2b>
    <complications>
    - Brandt wird misstrauisch, interne Untersuchung
    - Luna konfrontiert Noemi: Die ganze Wahrheit
    - Noemi zerbricht: Er hat sie ausgewählt, stalked, manipuliert
    - Konfrontation mit Elias: Dunkelste Szene – Wut, Gewalt, Sex
    - Sie wirft ihn raus, bricht alle Kontakte ab
    - Aber sie kann nicht aufhören, an ihn zu denken
    </complications>
    <second_plot_point>
    Reuter zeigt ihr den vollständigen Bericht: Voss war kein unschuldiges Opfer. Er hat drei Whistleblower in den Tod getrieben. Einer war Elias' Onkel.
    </second_plot_point>
    <dark_night>
    Noemi allein. Die Beweise für und gegen Elias. Ihre Karriere, ihre Gefühle, ihre Moral – alles steht auf dem Spiel. Was ist Gerechtigkeit?
    </dark_night>
  </act_2b>
  
  <act_3>
    <climax>
    - Der Prozess: Noemi präsentiert den Fall
    - Sie legt ALLE Beweise vor – auch die gegen Voss
    - Das Plädoyer: Sie argumentiert für milderes Strafmaß
    - Das Urteil: Totschlag, nicht Mord. Drei Jahre.
    - Elias wird abgeführt. Sein Blick: "Warte auf mich."
    </climax>
    <resolution>
    - Brandt ist wütend, Noemi's Karriere in Gefahr
    - Aber sie hat das Richtige getan (glaubt sie)
    - Sie besucht ihn im Gefängnis – einmal
    - "Drei Jahre." – "Ich zähle jeden Tag."
    </resolution>
    <final_image>
    Drei Jahre später. Gefängnistor. Ein Mann kommt heraus.
    Noemi steht da. Roter Lippenstift. Schwarzes Kleid.
    "Ich habe gewartet."
    Schnitt zu Schwarz.
    </final_image>
  </act_3>

</plot_structure>

<chapter_outline>

PROLOG - DIE AKTION
- POV: Objektiv
- NULL hackt das Kraftwerk
- Voss im Aufzug, der Herzinfarkt
- Elias sieht die Nachricht – sein Gesicht zeigt nichts

KAPITEL 1-2 - DIE EISERNE
- POV: Noemi
- Gerichtssaal: Sie gewinnt, brillant, kalt
- Sie erhält den NULL-Fall
- Ihre Wohnung: Die Einsamkeit

KAPITEL 3-4 - DIE RECHERCHE
- POV: Noemi
- Sie taucht in die Hackerszene ein (undercover)
- Der Club "Der Abgrund"

KAPITEL 5-6 - DIE ERSTE NACHT
- POV: Noemi, dann Elias
- Sie treffen sich, Chemie explodiert
- Die Nacht – intensiv, aber Noemi bleibt dominant (glaubt sie)
- Elias' POV: Er kennt sie. Er hat gewartet.

KAPITEL 7-8 - DER MORGEN DANACH
- POV: Noemi
- Sie flieht vor dem Aufwachen
- Im Büro: Neue Beweise, ein Foto von "Null"
- Sie erstarrt – es ist er

KAPITEL 9-10 - ER IST ÜBERALL
- POV: Noemi, Elias
- Er taucht vor ihrem Haus auf
- "Du bist gegangen, ohne dich zu verabschieden."
- Er weiß, wer sie ist

KAPITEL 11-14 - DAS SPIEL BEGINNT
- POV: Abwechselnd
- Er verfolgt sie – Café, Gym, Gericht
- Sie kann ihn nicht melden (Scham, Kompromittierung)
- Die Spannung steigt

KAPITEL 15-16 - DIE VERHÖRE
- POV: Noemi
- Sie befragt NULL-Mitglieder
- Erfährt mehr über Elias' Vergangenheit
- Welzow, seine Mutter, sein Hass

KAPITEL 17-18 - DIE ZWEITE NACHT
- POV: Noemi, dann Elias
- Sie schläft wieder mit ihm – diesmal in ihrer Wohnung
- Er bricht alle ihre Regeln
- Die intensivste Szene
- Danach: Der USB-Stick

KAPITEL 19-20 - DIE KOMPROMITTIERUNG
- POV: Noemi
- Sie vernichtet den USB-Stick
- Erfährt später: Es waren Beweise gegen ihn
- Sie hat Beweise vernichtet

KAPITEL 21-22 - MIDPOINT: DIE KONFRONTATION
- POV: Beide
- "Warum hast du das getan?"
- Das Spiel wird klar – er testet sie
- Aber seine Gefühle sind auch echt

KAPITEL 23-24 - DIE UNTERSUCHUNG
- POV: Noemi
- Brandt wird misstrauisch
- Interne Untersuchung beginnt
- Sie muss ihn fallen lassen – oder sich selbst

KAPITEL 25-26 - LUNA
- POV: Noemi
- Luna konfrontiert sie
- Die ganze Wahrheit: Das Stalking, die Inszenierung
- "Du bist nicht besonders. Du bist sein Projekt."

KAPITEL 27-28 - DER ZERFALL
- POV: Noemi, dann Elias
- Sie bricht zusammen
- Konfrontation mit Elias – die dunkelste Szene
- Sex, Wut, Tränen
- Sie wirft ihn raus

KAPITEL 29-30 - DIE WAHRHEIT ÜBER VOSS
- POV: Noemi
- Reuter zeigt ihr den vollständigen Bericht
- Voss war kein Unschuldiger
- Die Whistleblower, Elias' Onkel

KAPITEL 31-32 - DAS DILEMMA
- POV: Noemi
- Sie muss den Fall vor Gericht bringen
- Was ist Gerechtigkeit?
- Entscheidung

KAPITEL 33-34 - DER PROZESS
- POV: Noemi
- Gerichtssaal-Szene
- Sie präsentiert alle Beweise – auch gegen Voss
- Brandt ist wütend

KAPITEL 35-36 - DAS URTEIL
- POV: Noemi, dann Elias
- Totschlag, nicht Mord. Drei Jahre.
- Er wird abgeführt
- Sein Blick: "Warte auf mich."

EPILOG - DREI JAHRE SPÄTER
- POV: Noemi
- Gefängnistor
- Ein Mann kommt heraus
- "Ich habe gewartet."

</chapter_outline>

<series_context>
  <book_number>1</book_number>
  <total_books>3</total_books>
  <series_arc>
  Die STROMFALL-Trilogie folgt Noemi und Elias durch drei Phasen: Die Verstrickung (Band 1), Die Rückkehr (Band 2), Die Erlösung (Band 3). Ihre Beziehung wird getestet durch Gefängniszeit, Rache-Plots, und ihre eigenen Dämonen – bis sie endlich frei sind, zusammen zu sein.
  </series_arc>
  <this_book_role>
  Etabliert die Charaktere, ihre Wunden, ihre Anziehung. Der Fall wird gelöst (Verurteilung), aber die Beziehung bleibt offen. Endet mit Trennung durch Umstände, aber emotionaler Bindung.
  </this_book_role>
  <cliffhanger>
  Drei Jahre später, Gefängnistor. "Ich habe gewartet." – Setup für Band 2.
  </cliffhanger>
  <threads_to_continue>
  - Elias kommt frei – wie hat das Gefängnis ihn verändert?
  - Noemi's Karriere – überlebt sie?
  - Brandt – er ist immer noch da, korrupt, gefährlich
  - Voss' Sohn – will Rache (Band 2 Antagonist)
  - Luna – wo steht sie?
  - Noemi's Familie – ungelöst
  </threads_to_continue>
</series_context>

<consistency_rules>
1. Noemi trägt immer roten Lippenstift – außer in verletzlichen Momenten, dann nicht
2. Elias' Tattoo (Welzow-Koordinaten) wird dreimal erwähnt – Noemi berührt es im intimsten Moment
3. Elektrizitäts-Metaphern durchgängig: Spannung, Strom, Kurzschluss, Erdung
4. Noemi bindet ihre Haare immer zurück – außer mit ihm
5. Elias riecht nach Kaffee und etwas Metallischem (Server-Räume) – wird zur sensorischen Erinnerung
6. Verhör-Szenen haben immer Subtext – was nicht gesagt wird, ist lauter
7. Der Club "Der Abgrund" hat immer Bass, den man fühlt
8. Noemi's Wohnung wird zunehmend unordentlich – Spiegel ihres Kontrollverlusts
9. Wetter: Hitze = Spannung, Gewitter = Konfrontation, Regen = Verletzlichkeit
10. Miguel (toter Bruder) wird nie beim Namen genannt, bis Kapitel 26 – dann zum ersten Mal
</consistency_rules>

<forbidden_elements>
- Keine Non-Con (alles ist consensual, auch wenn dunkel)
- Kein Stalking, das glorifiziert wird – es wird als problematisch gezeigt
- Keine Verharmlosung von Manipulation – Elias' Verhalten hat Konsequenzen
- Kein Victim-Blaming bei Noemi
- Keine Insta-Vergebung – sie muss seine Manipulation verarbeiten
- Keine übernatürlichen Elemente
- Keine Tech-Magie – Hacking bleibt realistisch
- Kein Slut-Shaming
- Keine Vergewaltigung
- Kein Missbrauch von Kindern oder Tieren
</forbidden_elements>

<required_elements>
- Jedes Kapitel aus klarer POV
- Mindestens drei intensive Romance-Szenen pro Akt
- Spice-Szenen müssen emotional verankert sein – Sex ist nie nur Sex
- Elias' Kapitel zeigen seine Verletzlichkeit unter der Manipulation
- Noemi's Kontrolle muss LANGSAM brechen, nicht sofort
- Der Thriller-Plot muss funktionieren – NULL, Voss, Gerechtigkeit
- Die Moral ist grau – weder Noemi noch Elias sind "gut"
- Das Ende muss befriedigend sein (emotionaler Abschluss) aber offen (Serie)
- Trigger Warnings am Anfang
- Consent ist immer klar, auch in dunklen Szenen
</required_elements>

<spice_guidelines>
- Szenen sind explizit, aber nicht pornografisch
- Emotionale Verbindung ist wichtiger als physische Beschreibung
- Power-Dynamik wechselt – mal sie dominant, mal er
- Sprache: Sinnlich, nicht klinisch, nicht vulgär (außer im richtigen Moment)
- Mindestens 4-5 vollständige Szenen im Buch
- Jede Szene markiert einen Wendepunkt in ihrer Beziehung
- Nach-dem-Sex-Momente sind wichtiger als der Akt selbst
</spice_guidelines>

</project_definition>

<agent_instructions>
Bei der Generierung von Inhalten für STROMFALL:

1. NOEMI'S STIMME: Kontrolliert, aber mit Rissen. Sie analysiert alles – auch ihre eigenen Gefühle. Wenn sie die Kontrolle verliert, ist ihre Sprache fragmentierter.

2. ELIAS' PERSPEKTIVE: Third Person Limited. Distanziert, beobachtend – aber mit Momenten, wo die Emotion durchbricht. Er IST manipulativ – aber er WIRD auch echt berührt.

3. SPANNUNG: Push-Pull ist essenziell. Jede Annäherung muss einen Rückzug haben. Der Leser muss die Frustration FÜHLEN.

4. DUNKLE ELEMENTE: Stalking, Manipulation, Machtspiele werden NICHT glorifiziert. Sie werden gezeigt, haben Konsequenzen, werden verarbeitet.

5. CONSENT: IMMER klar. Auch in den dunkelsten Szenen ist klar, dass beide wollen. "Nein" wird respektiert – die Spannung kommt aus dem "Ja", das sie nicht sagen sollten.

6. SPICE: Emotional verankert. Jede Szene hat einen PURPOSE für die Beziehung. Keine Szene nur für Sexiness.

7. THRILLER-PLOT: Muss funktionieren. Der NULL-Fall, Voss' Tod, die Beweise – alles logisch.

8. MORALISCHE GRAUZONE: Beide sind fehlerhaft. Elias ist kein Held. Noemi ist keine Heilige. Die Frage "Ist er ein Mörder?" wird nicht einfach beantwortet.

9. PACING: Intensiv. Kurze Kapitel, häufige POV-Wechsel in spannenden Momenten. Längere Szenen nur für emotionale Beats.

10. SERIE: Band 1 muss eigenständig funktionieren, aber Hunger auf Band 2 machen. Das Ende ist ein emotionaler Abschluss, aber kein narrativer.
</agent_instructions>
```

---
---
---

# ZUSAMMENFASSUNG: TEMPLATE-STRUKTUR

```
<project_definition>
  <metadata>         → Technische Details (Genre, Länge, POV, etc.)
  <logline>          → Eine-Satz-Zusammenfassung
  <premise>          → Erweiterte Story-Beschreibung
  <central_question> → Die thematische Kernfrage
  <themes>           → Hauptthemen
  <tone_and_style>   → Erzählstimme, Prosa, Pacing, Vergleichstitel
  <worldbuilding>    → Zeit, Orte, Regeln, Kontext
  <characters>       → Detaillierte Charakterprofile
  <romance_arc>      → Tropes, Progression, Konflikte (falls Romance)
  <plot_structure>   → Drei-Akt-Struktur mit Beats
  <chapter_outline>  → Kapitel-für-Kapitel-Übersicht
  <series_context>   → Serienposition und übergreifende Arcs
  <consistency_rules>→ Interne Kohärenz-Regeln
  <forbidden_elements>→ Was NICHT im Buch sein darf
  <required_elements>→ Was im Buch sein MUSS
</project_definition>

<agent_instructions>  → Spezifische Anweisungen für KI-Agenten
```

---

Diese Prompts können direkt in ein Multi-Agenten-System wie LangGraph eingespeist werden. Die `<agent_instructions>` am Ende jedes Prompts geben dem System die spezifischen Regeln für die Generierung.
