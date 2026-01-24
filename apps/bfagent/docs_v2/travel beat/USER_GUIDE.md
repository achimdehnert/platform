# Travel Story - Benutzerhandbuch

> Personalisierte Geschichten für Ihre Reise

---

## Inhaltsverzeichnis

1. [Einführung](#1-einführung)
2. [Erste Schritte](#2-erste-schritte)
3. [Reise erfassen](#3-reise-erfassen)
4. [Story-Einstellungen](#4-story-einstellungen)
5. [Meine Welt](#5-meine-welt)
6. [Story lesen](#6-story-lesen)
7. [FAQ](#7-faq)

---

## 1. Einführung

### Was ist Travel Story?

Travel Story erstellt personalisierte Geschichten, die perfekt zu Ihrer Reise passen. Die Handlung spielt an Ihren Reisezielen, die Kapitel sind auf Ihre Lesezeit abgestimmt, und die Story berücksichtigt Ihre persönlichen Vorlieben.

### Wie funktioniert es?

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   1. REISE EINGEBEN                                     │
│      Wohin geht's? Wie lange? Welche Stopps?           │
│                          ↓                              │
│   2. GENRE WÄHLEN                                       │
│      Romance? Thriller? Mystery?                        │
│                          ↓                              │
│   3. PERSONALISIEREN                                    │
│      Charaktere, Orte, Ausschlüsse                     │
│                          ↓                              │
│   4. STORY GENERIEREN                                   │
│      KI erstellt Ihre persönliche Geschichte           │
│                          ↓                              │
│   5. UNTERWEGS LESEN                                    │
│      Kapitel synchron zu Ihrer Reise                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Features

| Feature | Beschreibung |
|---------|--------------|
| **Reise-Sync** | Kapitel passen zu Ihren Reisetagen |
| **Orts-Authentizität** | Echte Locations, atmosphärisch beschrieben |
| **Personalisierung** | Ihre Vorlieben, Ihre Geschichte |
| **Story-Kontinuität** | Charaktere entwickeln sich über mehrere Reisen |
| **Ausschluss-System** | Orte vermeiden, die Sie nicht mögen |

---

## 2. Erste Schritte

### Account erstellen

1. Öffnen Sie `travel-story.app` in Ihrem Browser
2. Klicken Sie auf **"Registrieren"**
3. Geben Sie E-Mail und Passwort ein
4. Bestätigen Sie Ihre E-Mail

### Dashboard

Nach dem Login sehen Sie Ihr Dashboard:

```
┌─────────────────────────────────────────────────────────┐
│  🏠 Travel Story                    [Profil] [Logout]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ + NEUE      │  │ 📖 MEINE    │  │ 🌍 MEINE    │     │
│  │   REISE     │  │   STORIES   │  │   WELT      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  LETZTE STORY                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ "Schatten über Barcelona"                        │   │
│  │ Kapitel 5 von 12 • Fortsetzen →                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Reise erfassen

### Neue Reise anlegen

1. Klicken Sie auf **"+ Neue Reise"**
2. Füllen Sie das Formular aus:

#### Basis-Informationen

| Feld | Beschreibung | Beispiel |
|------|--------------|----------|
| **Reisename** | Titel für Ihre Reise | "Mittelmeer-Trip 2025" |
| **Startdatum** | Wann geht's los? | 15.06.2025 |
| **Enddatum** | Wann kommen Sie zurück? | 25.06.2025 |

#### Stopps hinzufügen

Für jeden Stopp:

```
┌─────────────────────────────────────────────────────────┐
│  STOPP 1                                    [Entfernen] │
├─────────────────────────────────────────────────────────┤
│  Stadt:        [Barcelona____________]                  │
│  Land:         [Spanien______________]                  │
│  Ankunft:      [15.06.2025]                            │
│  Abreise:      [18.06.2025]                            │
│  Unterkunft:   [Hotel ▼]                               │
│                                                         │
│  [+ Weiteren Stopp hinzufügen]                         │
└─────────────────────────────────────────────────────────┘
```

**Unterkunftstypen:**
- 🏨 Hotel (45 Min Abend-Lesezeit)
- 🏠 Airbnb (50 Min)
- 🛏️ Hostel (30 Min)
- 🏕️ Camping (20 Min)
- 👥 Bei Freunden (25 Min)

#### Transport zwischen Stopps

```
┌─────────────────────────────────────────────────────────┐
│  TRANSPORT: Barcelona → Rom                             │
├─────────────────────────────────────────────────────────┤
│  Transportmittel:  [Flugzeug ▼]                        │
│  Dauer (ca.):      [2:00] Stunden                      │
│                                                         │
│  💡 Flugzeit = ~60 Min effektive Lesezeit              │
└─────────────────────────────────────────────────────────┘
```

**Transportmittel & Lesezeit:**

| Transport | Lesezeit-Effizienz |
|-----------|-------------------|
| ✈️ Flugzeug | 50-65% der Reisezeit |
| 🚂 Zug | 80% |
| 🚌 Bus | 50% |
| 🚗 Auto (Beifahrer) | 40% |
| 🚗 Auto (Fahrer) | 0% |

### Reisetyp wählen

```
┌─────────────────────────────────────────────────────────┐
│  WAS FÜR EINE REISE IST DAS?                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ○ 🏙️  Städtereise                                     │
│  ○ 🏖️  Strandurlaub         → +90 Min Pool/Strand     │
│  ○ 🧘  Wellness             → +75 Min Entspannung      │
│  ○ 🎒  Backpacking          → Flexible Lesezeiten      │
│  ○ 💼  Geschäftsreise       → Kürzere Kapitel         │
│  ○ 👨‍👩‍👧  Familienurlaub       → Weniger Lesezeit        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Story-Einstellungen

### Genre wählen

```
┌─────────────────────────────────────────────────────────┐
│  WÄHLEN SIE IHR GENRE                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐          │
│  │   💕      │  │   🔪      │  │   💕🔪    │          │
│  │  Romance  │  │ Thriller  │  │ Romantic  │          │
│  │           │  │           │  │ Suspense  │          │
│  └───────────┘  └───────────┘  └───────────┘          │
│                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐          │
│  │   🔍      │  │   ☕      │  │   🐉      │          │
│  │  Mystery  │  │   Cozy    │  │  Fantasy  │          │
│  │           │  │  Mystery  │  │ (Coming)  │          │
│  └───────────┘  └───────────┘  └───────────┘          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Spice Level (für Romance)

```
○ 🌶️    None      - Keine expliziten Szenen
○ 🌶️🌶️   Mild      - Angedeutete Intimität
○ 🌶️🌶️🌶️  Moderate  - Sinnliche Szenen
○ 🌶️🌶️🌶️🌶️ Spicy     - Explizite Szenen
```

### Ending-Präferenz

```
○ 😊 Happy End     - Garantiert positives Ende
○ 😢 Sad End       - Tragisches, aber berührendes Ende
○ 🤔 Open End      - Offenes Ende zum Nachdenken
○ 🎲 Überraschung  - Lassen Sie sich überraschen
```

### Lesegeschwindigkeit

```
○ 🐢 Langsam    - 200 Wörter/Minute
○ 🚶 Normal     - 250 Wörter/Minute
○ 🏃 Schnell    - 300 Wörter/Minute
```

---

## 5. Meine Welt

### Was ist "Meine Welt"?

"Meine Welt" speichert Ihre Story-Präferenzen:
- **Charaktere** aus früheren Stories
- **Persönliche Orte** (Lieblingscafés, besondere Plätze)
- **Ausschlüsse** (Orte, die Sie vermeiden möchten)
- **Erinnerungen** (was in Ihren Stories passiert ist)

### Story-Universum

Geben Sie Ihrem Universum einen Namen:

```
┌─────────────────────────────────────────────────────────┐
│  MEIN STORY-UNIVERSUM                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Name: [Elena & Marco's Abenteuer___________]          │
│                                                         │
│  💡 Alle Ihre Stories spielen im selben Universum.     │
│     Charaktere können wiederkehren!                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Charaktere verwalten

```
┌─────────────────────────────────────────────────────────┐
│  MEINE CHARAKTERE                      [+ Neu]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  👩 Elena Berger                                        │
│     Rolle: Protagonistin                                │
│     Eingeführt: "Schatten über Barcelona"              │
│     Status: In Beziehung mit Marco                     │
│     [Bearbeiten] [Löschen]                             │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  👨 Marco Conti                                         │
│     Rolle: Love Interest                                │
│     Eingeführt: "Schatten über Barcelona"              │
│     Status: Partner von Elena                          │
│     [Bearbeiten] [Löschen]                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Persönliche Orte

Fügen Sie Orte hinzu, die in Ihren Stories vorkommen sollen:

```
┌─────────────────────────────────────────────────────────┐
│  PERSÖNLICHE ORTE                      [+ Neu]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ✅ Can Paixano, Barcelona                              │
│     "Meine Entdeckung 2019, beste Cava der Stadt!"     │
│     → Wird in Stories verwendet                         │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  ❌ Sagrada Familia, Barcelona                          │
│     "War dort mit Ex - bitte nicht verwenden"          │
│     → Wird NICHT in Stories verwendet                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Ausschlüsse & Trigger

Vermeiden Sie Themen, die Sie nicht lesen möchten:

```
┌─────────────────────────────────────────────────────────┐
│  THEMEN VERMEIDEN                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ☑️ Autounfälle                                         │
│  ☑️ Verlust von Haustieren                             │
│  ☐ Krankheit                                           │
│  ☐ Betrug in Beziehungen                               │
│  ☐ ...                                                 │
│                                                         │
│  Eigene hinzufügen: [_____________________] [+]        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Story lesen

### Story-Übersicht

Nach der Generierung sehen Sie:

```
┌─────────────────────────────────────────────────────────┐
│  📖 Schatten über dem Mittelmeer                        │
│  Genre: Romantic Suspense • 12 Kapitel • 28.500 Wörter │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LESEPLAN                                               │
│                                                         │
│  Tag 1 (Barcelona)                                      │
│  ├─ Kapitel 1: Der Fund              ✓ Gelesen         │
│  └─ Kapitel 2: Der Fremde            ◐ Halb gelesen    │
│                                                         │
│  Tag 2 (Barcelona)                                      │
│  ├─ Kapitel 3: Schatten in der Nacht   Geplant         │
│  └─ Kapitel 4: Vertrauen               Geplant         │
│                                                         │
│  Tag 3 (Flug nach Rom)                                  │
│  └─ Kapitel 5: Flucht                  Geplant         │
│                                                         │
│  ...                                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Kapitel lesen

```
┌─────────────────────────────────────────────────────────┐
│  Kapitel 3: Schatten in der Nacht                       │
│  📍 Barcelona, Barri Gòtic                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Die Gassen des Gotischen Viertels verschluckten        │
│  jeden Laut. Elena beschleunigte ihre Schritte,         │
│  als sie die Footsteps hinter sich hörte...             │
│                                                         │
│  [Fortlaufender Story-Text]                             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ◀ Kapitel 2          [Lesezeichen]         Kapitel 4 ▶│
│                                                         │
│  Fortschritt: ████████░░░░ 65%    ~8 Min verbleibend   │
└─────────────────────────────────────────────────────────┘
```

### Offline-Modus

```
┌─────────────────────────────────────────────────────────┐
│  📥 OFFLINE SPEICHERN                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ☑️ Gesamte Story herunterladen                        │
│                                                         │
│  Format:                                                │
│  ○ 📱 App (automatisch synchronisiert)                 │
│  ○ 📄 PDF                                              │
│  ○ 📚 EPUB (für E-Reader)                              │
│                                                         │
│  [Herunterladen]                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 7. FAQ

### Allgemein

**Wie lange dauert die Story-Generierung?**
> Ca. 2-5 Minuten für eine 10-Kapitel-Story.

**Kann ich eine Story nachträglich ändern?**
> Nein, aber Sie können eine neue Version mit angepassten Einstellungen generieren.

**Werden meine Daten gespeichert?**
> Ja, Ihre Reisen und Stories werden sicher in Ihrem Account gespeichert.

### Personalisierung

**Warum wird mein Lieblingsort nicht erwähnt?**
> Stellen Sie sicher, dass der Ort in "Meine Welt" → "Persönliche Orte" als ✅ markiert ist.

**Wie kann ich einen Ort ausschließen?**
> Gehen Sie zu "Meine Welt" → "Persönliche Orte" → Ort hinzufügen → "In Story verwenden: Nein"

**Können meine Charaktere in der nächsten Reise weiterleben?**
> Ja! Charaktere aus Ihrem Story-Universum können in jeder neuen Story wieder auftauchen.

### Technisch

**Welche Browser werden unterstützt?**
> Chrome, Firefox, Safari, Edge (aktuelle Versionen)

**Gibt es eine App?**
> Eine mobile App ist in Entwicklung. Aktuell nutzen Sie die Web-App.

**Kann ich Stories exportieren?**
> Ja, als PDF oder EPUB unter "Story" → "Herunterladen"

---

## Support

Bei Fragen oder Problemen:

- 📧 E-Mail: support@travel-story.app
- 💬 Chat: In der App unten rechts
- 📖 Hilfe-Center: help.travel-story.app

---

*Version 1.0 • Stand: Januar 2025*
