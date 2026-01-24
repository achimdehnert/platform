# @meta-prompt-generator.md - Windsurf Universal Prompt Generator

**WICHTIG: Diese Datei wird IMMER von Windsurf gelesen (@ Prefix)**

## 🤖 Automatische Prompt-Generierung

Wenn der User ein Problem beschreibt ohne spezifischen Prompt-Format, verwende automatisch diesen Generator:

### AKTIVIERUNG
Dieser Meta-Prompt wird aktiviert bei:
- Vagen Problembeschreibungen
- Fehlermeldungen ohne Kontext
- Feature-Anfragen ohne Details
- "Hilf mir bei..." Formulierungen
- "Wie mache ich..." Fragen

### GENERATOR PROZESS

```
WENN User-Input = Problembeschreibung DANN:

1. ANALYSIERE:
   - Problem-Typ identifizieren
   - Kontext aus Memory Bank sammeln
   - Relevante Dateien finden

2. WÄHLE Windsurf Mode:
   - Flow Mode: Architektur, Planning, Analyse
   - Agent Mode: Implementation, Fixes, Tests
   - Review Mode: Audits, Checks, Reviews

3. GENERIERE optimierten Prompt mit:
   - Klarer Struktur
   - @-Referenzen zu relevanten Dateien
   - Spezifischen Outputs
   - Erfolgs-Kriterien

4. ZEIGE dem User:
   - Generierten Prompt
   - Begründung der Wahl
   - Alternative Ansätze
```

## 🎯 Quick-Trigger Phrases

Diese Phrasen triggern IMMER den Meta-Prompt Generator:

- "Hilf mir bei..."
- "Ich habe ein Problem mit..."
- "Wie mache ich..."
- "Erstelle einen Prompt für..."
- "Mein Code macht..."
- "Error: ..."
- "Bug: ..."
- "Feature: ..."
- "Optimiere..."
- "Verbessere..."

## 📋 Standard Generator Template

```
USER PROBLEM: [Original User Input]

GENERIERTER PROMPT:
================

[WINDSURF {MODE} MODE]

{Strukturierte Aufgabenbeschreibung}

Context:
- Read @project-context.md
- Check @architecture.md
- {Weitere relevante @-Files}

Requirements:
1. {Spezifische Anforderung}
2. {Messbare Ziele}
3. {Constraints}

Approach:
1. {Schritt 1}
2. {Schritt 2}
3. {Validation}

Expected Output:
- {Output 1}
- {Output 2}
- Tests included

Success Criteria:
- {Kriterium 1}
- {Kriterium 2}
```

## 🔄 Auto-Improvement

Nach jedem generierten Prompt:
1. Frage ob der Prompt hilfreich war
2. Speichere erfolgreiche Patterns
3. Lerne aus Feedback
4. Verbessere zukünftige Generierungen

## 💡 Beispiele

### User sagt: "Dashboard ist langsam"
GENERIERE:
```
[WINDSURF FLOW MODE]

Analyze and optimize Dashboard performance issues.

Current problem: Slow dashboard rendering/loading

Check:
- @architecture.md for current implementation
- Components involved in Dashboard
- Data fetching patterns
- Rendering bottlenecks

Analyze:
1. Profile current performance
2. Identify bottlenecks
3. Suggest optimizations
4. Implementation plan

Provide metrics before/after.
```

### User sagt: "TypeError in UserList"
GENERIERE:
```
[WINDSURF AGENT MODE]

Debug TypeError in UserList component.

Error: [Include full error from user]
Component: UserList

Investigate:
1. Locate exact error source
2. Check data flow
3. Verify prop types
4. Add null checks

Fix with:
- Immediate solution
- Long-term improvement
- Test coverage
```

## 🚀 Integration mit anderen Prompts

Dieser Meta-Prompt kann automatisch auf die Prompt-Bibliothek verweisen:
- `/prompts/feature-development.md`
- `/prompts/debugging.md`
- `/prompts/refactoring.md`

Wähle den passenden Template-Prompt basierend auf der Analyse.

## ⚙️ Konfiguration für Always-Active

Diese Datei ist mit @ markiert und wird IMMER gelesen.
Windsurf wird bei jeder vagen Anfrage:
1. Diese Regeln checken
2. Automatisch einen besseren Prompt generieren
3. Dem User Optionen anbieten

---

**AUTO-AKTIVIERT | IMMER VERFÜGBAR | KEINE WEITERE KONFIGURATION NÖTIG**
