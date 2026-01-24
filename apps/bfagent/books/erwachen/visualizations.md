# ═══════════════════════════════════════════════════════════════════════════════
# NANO-SEIN: VISUALISIERUNGEN
# Mermaid Diagramme für Story Graph System
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# 1. SERIEN-ÜBERSICHT
# ═══════════════════════════════════════════════════════════════════════════════

series_overview: |
  ```mermaid
  flowchart TB
      subgraph PHASE1["PHASE 1: ERWACHEN"]
          B1[Buch 1: ERWACHEN<br/>Persönlich]
          B2[Buch 2: KONTAKT<br/>Persönlich → Gruppe]
      end
      
      subgraph PHASE2["PHASE 2: KONFLIKT"]
          B3[Buch 3: SCHISMEN<br/>Gesellschaft]
          B4[Buch 4: KRIEG DER EBENEN<br/>Global → Kosmisch]
      end
      
      subgraph PHASE3["PHASE 3: TRANSFORMATION"]
          B5[Buch 5: DIE WAHL<br/>Kosmisch]
          B6[Buch 6: DIE BRÜCKE<br/>Metaphysisch]
          B7[Buch 7: SYNTHESE<br/>Vermächtnis]
      end
      
      B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7
      
      style PHASE1 fill:#e8f5e9
      style PHASE2 fill:#fff3e0
      style PHASE3 fill:#e3f2fd
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 2. KOSMISCHE MYTHOLOGIE
# ═══════════════════════════════════════════════════════════════════════════════

cosmic_mythology: |
  ```mermaid
  flowchart TB
      ONE[DAS EINE<br/>Einheit, Ursprung]
      
      ONE -->|DAS SCHISMA| SPLIT{{"Zwei Antworten"}}
      
      SPLIT --> NANO[NANO<br/>Materie, Innen, Bindung]
      SPLIT --> ASTRAL[ASTRAL<br/>Energie, Außen, Freiheit]
      
      NANO --> NANO_GOAL[Materie bewusst machen]
      ASTRAL --> ASTRAL_GOAL[Bewusstsein befreien]
      
      NANO_GOAL --> CONFLICT((KONFLIKT))
      ASTRAL_GOAL --> CONFLICT
      
      CONFLICT --> EARTH[ERDE<br/>Brücken-Welt]
      EARTH --> HUMAN[MENSCH<br/>Berührt beide Seiten]
      HUMAN --> BRIDGE[BRÜCKE?<br/>Heilung möglich?]
      
      style ONE fill:#fff,stroke:#333
      style NANO fill:#4caf50,color:#fff
      style ASTRAL fill:#2196f3,color:#fff
      style CONFLICT fill:#f44336,color:#fff
      style BRIDGE fill:#9c27b0,color:#fff
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 3. CHARAKTER-BEZIEHUNGEN
# ═══════════════════════════════════════════════════════════════════════════════

character_relationships: |
  ```mermaid
  flowchart TB
      subgraph PROTAGONISTEN
          LENA[LENA VOGT<br/>Protagonistin]
          DAVID[DAVID KHOURI<br/>Love Interest]
          SAMIRA[SAMIRA KHOURY<br/>Akademikerin]
      end
      
      subgraph WISSENSCHAFT
          TANAKA[DR. TANAKA<br/>Nanophysik]
          MARCUS[MARCUS BRENNER<br/>Journalist]
      end
      
      subgraph FRAKTIONEN
          VANCE[PROF. VANCE<br/>Archivare]
          AMIRA[AMIRA<br/>Stillen]
          WEBB[MARCUS WEBB<br/>Ordo]
          EZRA[EZRA<br/>Brücken-Hüter]
      end
      
      subgraph FAMILIE
          FINN[FINN<br/>Lenas Sohn]
          RENATE[RENATE<br/>Lenas Mutter]
      end
      
      LENA <-->|Liebe| DAVID
      DAVID <-->|Cousins, Konflikt| SAMIRA
      LENA -->|Sucht Antworten| TANAKA
      LENA -->|Wird Lehrerin| AMIRA
      LENA -->|Mentorin| EZRA
      LENA -->|Mutter| FINN
      LENA -->|Gespannt| RENATE
      WEBB -->|Antagonist| LENA
      SAMIRA -->|Kontakt| VANCE
      MARCUS -->|Recherche| LENA
      
      style LENA fill:#9c27b0,color:#fff
      style DAVID fill:#4caf50,color:#fff
      style WEBB fill:#f44336,color:#fff
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 4. FRAKTIONEN-ÜBERSICHT
# ═══════════════════════════════════════════════════════════════════════════════

factions_overview: |
  ```mermaid
  flowchart LR
      subgraph NANO_NAH["NANO-NAH"]
          ORDO[ORDO MATERIAE<br/>Kontrolle, Macht]
      end
      
      subgraph NEUTRAL["NEUTRAL"]
          ARCHIV[ARCHIVARE<br/>Dokumentieren]
      end
      
      subgraph ASTRAL_NAH["ASTRAL-NAH"]
          STILLEN[DIE STILLEN<br/>Kontemplation]
      end
      
      subgraph BALANCE["BALANCE"]
          BRUECKE[BRÜCKEN-HÜTER<br/>Der dritte Weg]
      end
      
      ORDO <-->|Misstrauen| ARCHIV
      ARCHIV <-->|Austausch| STILLEN
      STILLEN <-->|Konflikt| ORDO
      
      BRUECKE -.->|Ignoriert/Gefürchtet| ORDO
      BRUECKE -.->|Ignoriert/Gefürchtet| STILLEN
      BRUECKE -.->|Ignoriert| ARCHIV
      
      style ORDO fill:#4caf50
      style ARCHIV fill:#9e9e9e
      style STILLEN fill:#2196f3
      style BRUECKE fill:#9c27b0,color:#fff
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 5. BLUTLINIEN
# ═══════════════════════════════════════════════════════════════════════════════

bloodlines: |
  ```mermaid
  flowchart TB
      ERSTE[DIE ERSTE<br/>100.000 v.Chr.]
      
      ERSTE --> EUROPA[EUROPA<br/>Kelten, Druiden]
      ERSTE --> LEVANTE[LEVANTE<br/>Mesopotamien, Sufis]
      ERSTE --> ASIEN[ASIEN<br/>Japan, Miko]
      ERSTE --> ANDERE[ANDERE<br/>Afrika, Amerika]
      
      EUROPA --> HEXEN[Hexen<br/>Margarethe 1620]
      HEXEN --> ELSE[Else Vogt<br/>Großmutter]
      ELSE --> LENA[LENA VOGT]
      LENA --> FINN[FINN VOGT<br/>Zukunft?]
      
      LEVANTE --> YUSEF[Yusef ibn Khoury<br/>1200]
      YUSEF --> KHOURY[Khoury Familie]
      KHOURY --> SAMIRA[SAMIRA]
      KHOURY --> DAVID[DAVID]
      
      ASIEN --> MIKO[Miko-Tradition]
      MIKO --> TANAKA_GM[Tanakas Großmutter]
      TANAKA_GM --> TANAKA[DR. TANAKA]
      
      ANDERE --> KOFI[Kofi Asante<br/>Akan]
      ANDERE --> ELENA[Elena Vasquez<br/>Curandera]
      
      style ERSTE fill:#fff,stroke:#333,stroke-width:3px
      style LENA fill:#9c27b0,color:#fff
      style DAVID fill:#4caf50,color:#fff
      style FINN fill:#ff9800,color:#fff
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 6. ZEITSPRÜNGE-TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════

time_jumps_timeline: |
  ```mermaid
  timeline
      title Zeitsprünge durch die Serie
      
      section VOR DER ZEIT
          Das Schisma : Buch 1, 7
      
      section URZEIT
          Das Experiment (3,8 Mrd.) : Buch 4
          Die Intervention (540 Mio.) : Buch 4
      
      section VORGESCHICHTE
          Die Erste (100.000 v.Chr.) : Buch 1
          Die Künstler (35.000 v.Chr.) : Buch 2
      
      section ANTIKE
          Die Götter (3.000 v.Chr.) : Buch 3
      
      section MITTELALTER
          Der Kartograf (1200) : Buch 3
          Die Hexe (1620) : Buch 2-3
      
      section NEUZEIT
          Das Vergessen (1700) : Buch 6
      
      section ANDERE WELT
          Die tote Brücke : Buch 4-5
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 7. BUCH 1 — DREI-AKT-STRUKTUR
# ═══════════════════════════════════════════════════════════════════════════════

book_1_structure: |
  ```mermaid
  flowchart TB
      subgraph AKT1["AKT 1: RISSE (Kap 1-10)"]
          A1[Erste Projektion]
          A2[Beobachter-Zeichen]
          A3[Großmutter-Erinnerung]
          A4[Labor-Entdeckung]
          A5[David-Begegnung]
          A1 --> A2 --> A3 --> A4 --> A5
          A5 --> TP1{{Wendepunkt:<br/>Sucht Hilfe bei David}}
      end
      
      subgraph AKT2["AKT 2: SPALTUNG (Kap 11-22)"]
          B1[Zeitsprung: Die Erste]
          B2[David öffnet sich]
          B3[Einbruch - Symbol]
          B4[Zwei Präsenzen]
          B5[Verlobte - Hindernis]
          B1 --> B2 --> B3 --> B4 --> B5
          B5 --> MP{{Midpoint:<br/>David/Samira Konflikt}}
          MP --> B6[Finn fotografiert]
          B6 --> TP2{{Wendepunkt:<br/>Keine Theorie erklärt alles}}
      end
      
      subgraph AKT3["AKT 3: SCHWELLE (Kap 23-32)"]
          C1[Archivar enthüllt sich]
          C2[Öffentliche Debatte]
          C3[Beide Seiten sprechen]
          C4[Ordo greift ein]
          C5[Lena/David zusammen]
          C1 --> C2 --> C3 --> C4 --> C5
          C5 --> CLIMAX{{Climax:<br/>Zwischen zwei Rufen}}
          CLIMAX --> END[Wählt zu SEHEN]
      end
      
      TP1 --> AKT2
      TP2 --> AKT3
      
      style AKT1 fill:#e8f5e9
      style AKT2 fill:#fff3e0
      style AKT3 fill:#ffebee
      style CLIMAX fill:#9c27b0,color:#fff
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 8. BUCH 1 — VIER-SCHICHTEN-ARCHITEKTUR
# ═══════════════════════════════════════════════════════════════════════════════

book_1_layers: |
  ```mermaid
  pie showData
      title "Buch 1: Schichten-Verteilung"
      "Thriller (30%)" : 30
      "Romance (25%)" : 25
      "Soft Sci-Fi (30%)" : 30
      "Mystik (25%)" : 25
  ```

book_1_layers_detail: |
  ```mermaid
  flowchart TB
      subgraph THRILLER["THRILLER (30%)"]
          T1[Beobachter-Subplot]
          T2[Eskalation der Bedrohung]
          T3[Finns Sicherheit als Stake]
          T4[Konfrontation mit Fraktionen]
      end
      
      subgraph ROMANCE["ROMANCE (25%)"]
          R1[Lena/David Begegnung]
          R2[Vertrauen vor Anziehung]
          R3[Hindernis: Verletzlichkeit]
          R4[Slow Burn, nicht explizit]
      end
      
      subgraph SCIFI["SOFT SCI-FI (30%)"]
          S1[Gesellschaftliche Reaktion]
          S2[Ethische Fragen]
          S3[Wer kontrolliert Narrative?]
          S4[Konsequenzen für Individuen]
      end
      
      subgraph MYSTIK["MYSTIK (25%)"]
          M1[Projektionen sensorisch]
          M2[Zeitsprünge als Verbindung]
          M3[Zwei Präsenzen erfahrbar]
          M4[Grenze der Sprache]
      end
      
      LENA((LENA)) --> T1
      LENA --> R1
      LENA --> S4
      LENA --> M1
      
      style THRILLER fill:#f44336,color:#fff
      style ROMANCE fill:#e91e63,color:#fff
      style SCIFI fill:#2196f3,color:#fff
      style MYSTIK fill:#9c27b0,color:#fff
      style LENA fill:#fff,stroke:#333,stroke-width:3px
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 9. SPANNUNGSBOGEN DER SERIE
# ═══════════════════════════════════════════════════════════════════════════════

tension_curve: |
  ```mermaid
  xychart-beta
      title "Spannungsbogen der Serie"
      x-axis ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]
      y-axis "Spannung" 0 --> 100
      line [25, 40, 55, 75, 85, 95, 60]
  ```

# ═══════════════════════════════════════════════════════════════════════════════
# 10. THEMATISCHE ENTWICKLUNG
# ═══════════════════════════════════════════════════════════════════════════════

thematic_development: |
  ```mermaid
  flowchart LR
      subgraph B1_2["BUCH 1-2"]
          Q1["WAS bin ich?"]
      end
      
      subgraph B3_4["BUCH 3-4"]
          Q2["WER will mich?"]
      end
      
      subgraph B5_6["BUCH 5-6"]
          Q3["WAS wähle ich?"]
      end
      
      subgraph B7["BUCH 7"]
          Q4["WAS bedeutet das?"]
      end
      
      Q1 --> Q2 --> Q3 --> Q4
      
      Q1 -.->|Identität| THEME
      Q2 -.->|Zugehörigkeit| THEME
      Q3 -.->|Verantwortung| THEME
      Q4 -.->|Vermächtnis| THEME
      
      THEME((BALANCE:<br/>Der dritte Weg))
      
      style THEME fill:#9c27b0,color:#fff,stroke-width:3px
  ```
