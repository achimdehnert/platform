/**
 * CASCADE XL StreamDeck Profile Generator
 *
 * Generates a complete StreamDeck XL profile (32 buttons, 8x4)
 * for CASCADE template automation with BFAgent MCP integration
 *
 * Usage:
 * node index.js path/to/this/file.js
 *
 * Requirements:
 * - streamdeck-profile-generator installed
 * - Custom clipboard action (see CASCADE_ACTIONS.md)
 */

const { action, website, back, folder } = require('../../streamdeck-profile-generator/lib/actions');
const { profile } = require('../../streamdeck-profile-generator/lib/profile');

/** @typedef {import('../streamdeck-profile-generator/lib/profile').Profiles} Profiles */
/** @typedef {import('../streamdeck-profile-generator/lib/actions').Action} Action */

/**
 * Custom clipboard action for CASCADE templates
 * Uses System → Text action to copy text to clipboard
 * @param {{title: string, text: string, color?: string}} config
 * @returns {Action}
 */
function clipboard({ title, text, color }) {
  return {
    'ActionID': `clipboard-${Math.random().toString(36).substr(2, 9)}`,
    'LinkedTitle': true,
    'Name': 'Text',
    'Settings': {
      'text': text,
    },
    'State': 0,
    'States': [{
      'Title': title,
      'TitleColor': color || '#FFFFFF',
      'ShowTitle': true,
    }],
    'UUID': 'com.elgato.streamdeck.system.text',
  };
}

/**
 * Open file action
 * @param {{title: string, path: string, color?: string}} config
 * @returns {Action}
 */
function openFile({ title, path, color }) {
  return {
    'ActionID': `open-${Math.random().toString(36).substr(2, 9)}`,
    'LinkedTitle': true,
    'Name': 'Open',
    'Settings': {
      'openInBrowser': false,
      'path': path,
    },
    'State': 0,
    'States': [{
      'Title': title,
      'TitleColor': color || '#FFFFFF',
      'ShowTitle': true,
    }],
    'UUID': 'com.elgato.streamdeck.system.open',
  };
}

/**
 * Templates for CASCADE
 */
const TEMPLATES = {
  feature: `### Request: [FEATURE NAME]

**Ziel:**
[WAS SOLL ERREICHT WERDEN?]

**Requirements:**
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

**Constraints:**
- [EINSCHRÄNKUNGEN]

**Tools:**
- [x] BFAgent MCP für Best Practices
- [x] Check Protected Paths

**Plan:**
[x] Zeig mir erst den Plan

**Testing:**
- [ ] [TESTING REQUIREMENTS]`,

  quickTask: `Task: [ONE-LINER]

Requirements:
- [ ] Thing 1
- [ ] Thing 2
- [ ] Thing 3

Tools: BFAgent MCP best_practices

Plan: show first`,

  bugFix: `### Bug Fix: [PROBLEM]

**Symptom:**
[WAS FUNKTIONIERT NICHT?]

**Error Message:**
\`\`\`
[ERROR]
\`\`\`

**Location:**
- File: [PATH]
- Function: [NAME]

**Expected Behavior:**
[WAS SOLLTE PASSIEREN?]

**Tools:**
- [x] BFAgent MCP Protected Paths checken`,

  refactor: `### Refactoring: [COMPONENT]

**Ziel:**
[WARUM REFACTOREN?]

**Scope:**
- Domain: [DOMAIN]
- Component: [TYPE]

**Safety Checks:**
- [x] BFAgent MCP: get_refactor_options('[DOMAIN]')
- [x] BFAgent MCP: check_path_protection()
- [x] BFAgent MCP: get_best_practices()

**Plan:**
[x] Zeig mir erst den Plan`,

  minimal: `@CASCADE:
Task: [BESCHREIBUNG]
Requirements: [LISTE]
Tools: BFAgent MCP
Plan: show first`,

  context: `@CASCADE: Context needed

**Frage:**
[WAS MÖCHTE ICH WISSEN?]

**Nutze:**
- [ ] code_search
- [ ] BFAgent MCP: search_handlers
- [ ] BFAgent MCP: get_domain

**Don't code yet - investigation only**`,

  plan: `@CASCADE: Zeig mir erst den Plan für:

[BESCHREIBUNG DER AUFGABE]

Schritte:
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3`,

  checkpoint: `@CASCADE: Checkpoint

- Was ist der Stand?
- Was fehlt noch?
- Welche Requirements sind noch offen?`,

  bestPractices: `Frage BFAgent MCP nach Best Practices für: [THEMA]

Beispiele:
- handlers
- pydantic
- ai_integration
- testing
- error_handling
- performance`,

  protectedPaths: `Check mit BFAgent MCP die Protected Paths für: [FILE_PATH]

IMMER vor Datei-Änderungen checken!`,

  naming: `Hole Naming Convention von BFAgent MCP für: [DOMAIN]

Domains: books, core, expert_hub, ui_hub, etc.`,

  domainInfo: `Zeige mir Domain Info via BFAgent MCP für: [DOMAIN]

Include:
- [x] Handlers
- [x] Phases
- [x] Status`,

  searchHandlers: `Suche mit BFAgent MCP nach existierenden Handlers für: [FUNKTIONALITÄT]

Query: [z.B. "PDF parsing", "Character generation"]`,

  refactorOptions: `Hole Refactoring Options von BFAgent MCP für Domain: [DOMAIN]

Zeige:
- Available components
- Risk level
- Dependencies
- Protected paths`,

  getDomain: `Nutze BFAgent MCP: get_domain()

Domain ID: [DOMAIN_ID]
Include handlers: [x]
Include phases: [x]
Response format: markdown`,

  validateHandler: `Validiere Handler mit BFAgent MCP:

Handler Code: [PATH_TO_HANDLER]
Strict Mode: [ ] yes [x] no

Erwarte Score: 0-100`,

  createDomain: `### New Domain: [DOMAIN_NAME]

**Purpose:**
[WAS MACHT DIESE DOMAIN?]

**Models:**
- [ ] Model 1: [name] - [purpose]

**Handlers:**
- [ ] Handler 1: [name] - [what it does]

**BFAgent MCP:**
- [x] get_naming_convention()
- [x] scaffold_domain()
- [x] Domain in domain_arts registrieren`,

  createHandler: `Erstelle Handler mit BFAgent MCP:

Handler Name: [NAME]
Domain: [DOMAIN]
Handler Type: [ai_powered/rule_based/hybrid]
Description: [BESCHREIBUNG]

Include Tests: [x] yes`,

  createView: `Erstelle View:

View Name: [NAME]
URL: /[path]/
Template: [app]/[name].html

Features:
- [ ] Feature 1
- [ ] Feature 2

Tools: BFAgent MCP`,

  createModel: `Erstelle Model:

Model Name: [NAME]
App: [APP]
Table Name: [prefix]_[name]

Fields:
- [ ] Field 1: [type]
- [ ] Field 2: [type]

Tools: BFAgent MCP naming`,

  createTest: `Erstelle Test:

Test Type: [unit/integration/e2e]
Target: [FILE_OR_FUNCTION]

Test Cases:
- [ ] Case 1
- [ ] Case 2

Tools: BFAgent MCP best_practices`,

  goldenRules: `🏆 CASCADE Golden Rules:

1. REQUIREMENTS FIRST
   → Liste was du willst

2. PLAN BEFORE CODE
   → "Zeig mir erst den Plan"

3. USE BFAGENT MCP
   → "Check mit BFAgent MCP"

Immer befolgen! ✅`,

  continueTask: `@CASCADE: Continue mit letzter Task

Context:
- Letzte Anfrage war: [BESCHREIBUNG]
- Stand ist: [STATUS]
- Nächster Schritt: [STEP]

Bitte fortfahren!`,

  pauseTask: `@CASCADE: Pause aktuelle Task

Bitte speichere:
- [ ] Aktuellen Stand
- [ ] Offene TODOs
- [ ] Nächste Schritte

Dokumentiere in: ACTIVE_CONTEXT.md`,

  startSession: `@CASCADE: Neue Session starten

Session Goal: [HAUPTZIEL]

Tasks:
- [ ] Task 1
- [ ] Task 2

Erstelle Plan und ACTIVE_CONTEXT.md!`,

  completeSession: `@CASCADE: Session abschließen

Bitte erstelle:
- [ ] Session Summary
- [ ] Commit & Push vorbereiten
- [ ] Safe Restart Doku

Was wurde erreicht?`,

  snapshot: `@CASCADE: Status Snapshot

Checkpoint:
- Was ist der Stand?
- Was fehlt noch?
- Welche Files geändert?
- Bereit für Commit?`,

  saveState: `@CASCADE: Save current state

Erstelle/Update:
- ACTIVE_CONTEXT.md
- Alle TODOs
- Offene Requirements

Für sicheren Restart!`,
};

/**
 * Main generator function
 * @type {function(Object): Profiles}
 */
module.exports = (argv) => {
  // ROW 1: Templates (8 buttons)
  const row1 = [
    clipboard({ title: 'Feature\nRequest', text: TEMPLATES.feature, color: '#4CAF50' }),
    clipboard({ title: 'Quick\nTask', text: TEMPLATES.quickTask, color: '#FF9800' }),
    clipboard({ title: 'Bug\nFix', text: TEMPLATES.bugFix, color: '#F44336' }),
    clipboard({ title: 'Refactor', text: TEMPLATES.refactor, color: '#2196F3' }),
    clipboard({ title: 'Minimal\nRequest', text: TEMPLATES.minimal, color: '#607D8B' }),
    clipboard({ title: 'Context\nRequest', text: TEMPLATES.context, color: '#00BCD4' }),
    clipboard({ title: 'Plan\nRequest', text: TEMPLATES.plan, color: '#3F51B5' }),
    clipboard({ title: 'Check\npoint', text: TEMPLATES.checkpoint, color: '#9C27B0' }),
  ];

  // ROW 2: BFAgent MCP Tools (8 buttons)
  const row2 = [
    clipboard({ title: 'BFAgent\nBest', text: TEMPLATES.bestPractices, color: '#8BC34A' }),
    clipboard({ title: 'Protected\nPaths', text: TEMPLATES.protectedPaths, color: '#FF5722' }),
    clipboard({ title: 'Naming\nConv', text: TEMPLATES.naming, color: '#009688' }),
    clipboard({ title: 'Domain\nInfo', text: TEMPLATES.domainInfo, color: '#673AB7' }),
    clipboard({ title: 'Search\nHandlers', text: TEMPLATES.searchHandlers, color: '#795548' }),
    clipboard({ title: 'Refactor\nOptions', text: TEMPLATES.refactorOptions, color: '#FF6F00' }),
    clipboard({ title: 'Get\nDomain', text: TEMPLATES.getDomain, color: '#1976D2' }),
    clipboard({ title: 'Validate\nHandler', text: TEMPLATES.validateHandler, color: '#7B1FA2' }),
  ];

  // ROW 3: Workflows & Creation (8 buttons)
  const row3 = [
    clipboard({ title: 'Create\nDomain', text: TEMPLATES.createDomain, color: '#00897B' }),
    clipboard({ title: 'Create\nHandler', text: TEMPLATES.createHandler, color: '#5E35B1' }),
    clipboard({ title: 'Create\nView', text: TEMPLATES.createView, color: '#C2185B' }),
    clipboard({ title: 'Create\nModel', text: TEMPLATES.createModel, color: '#F57C00' }),
    clipboard({ title: 'Create\nTest', text: TEMPLATES.createTest, color: '#558B2F' }),
    clipboard({ title: 'Golden\nRules', text: TEMPLATES.goldenRules, color: '#FFC107' }),
    openFile({ title: 'Help\nCard', path: 'C:\\Users\\achim\\github\\bfagent\\docs\\QUICK_REFERENCE_CARD.md', color: '#E91E63' }),
    openFile({ title: 'Open\nDocs', path: 'C:\\Users\\achim\\github\\bfagent\\docs', color: '#00ACC1' }),
  ];

  // ROW 4: Session Management (8 buttons)
  const row4 = [
    clipboard({ title: 'Continue\nTask', text: TEMPLATES.continueTask, color: '#43A047' }),
    clipboard({ title: 'Pause\nTask', text: TEMPLATES.pauseTask, color: '#FB8C00' }),
    clipboard({ title: 'Start\nSession', text: TEMPLATES.startSession, color: '#66BB6A' }),
    clipboard({ title: 'Complete\nSession', text: TEMPLATES.completeSession, color: '#26A69A' }),
    clipboard({ title: 'Snapshot\nStatus', text: TEMPLATES.snapshot, color: '#5C6BC0' }),
    website({ title: 'Open\nMonitor', url: 'http://127.0.0.1:8000/monitoring/', color: '#29B6F6' }),
    clipboard({ title: 'Save\nState', text: TEMPLATES.saveState, color: '#AB47BC' }),
    null, // Reserved for future use or folder
  ];

  // Main profile with all 32 buttons (8x4)
  return {
    mainProfile: profile({
      name: 'CASCADE XL Main',
      actions: [
        row1,
        row2,
        row3,
        row4,
      ],
    }),
    additionalProfiles: [],
  };
};
