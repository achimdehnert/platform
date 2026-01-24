# BookFactory Memory Bank - Lint & Formatting Error Resolution

## 🚨 KRITISCH: Automatische Fehlerbehebung vor jeder Bearbeitung
**Workflow für ALLE Datei-Bearbeitungen:**
```bash
# 1. Service-Status prüfen (BookFactory-spezifisch)
python service_manager.py status

# 2. Automatische Fixes für alle Dateien
npm run lint:fix
npm run format

# 3. TypeScript-Validierung
npm run type-check

# 4. Für spezifische Dateien
npx eslint --fix path/to/file.tsx
npx prettier --write path/to/file.tsx

# 5. Build-Test nach Änderungen
npm run build
```

## 📋 Standard-Konfiguration für neue Projekte

### ESLint Configuration (.eslintrc.json) - BookFactory Optimized
```json
{
  "extends": [
    "next/core-web-vitals",
    "plugin:@typescript-eslint/recommended",
    "plugin:prettier/recommended",
    "plugin:jsx-a11y/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": ["error", {
      "argsIgnorePattern": "^_",
      "varsIgnorePattern": "^_",
      "destructuredArrayIgnorePattern": "^_"
    }],
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/strict-boolean-expressions": "error",
    "@typescript-eslint/prefer-nullish-coalescing": "error",
    "@typescript-eslint/prefer-optional-chain": "error",
    "react/display-name": "off",
    "react-hooks/exhaustive-deps": "warn",
    "react/prop-types": "off",
    "jsx-a11y/anchor-is-valid": "off",
    "no-console": ["warn", { "allow": ["warn", "error", "info"] }],
    "prefer-const": "error",
    "no-var": "error"
  },
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module",
    "project": "./tsconfig.json"
  }
}
```

### Prettier Configuration (.prettierrc) - BookFactory Standards
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "useTabs": false,
  "quoteProps": "as-needed",
  "bracketSameLine": false,
  "proseWrap": "preserve",
  "htmlWhitespaceSensitivity": "css",
  "embeddedLanguageFormatting": "auto"
}
```

## 🔧 BookFactory-Spezifische Lint-Fehler und Lösungen

### 0. Interface-Mismatch Errors (BookFactory-Häufig)
```typescript
// ❌ Error: Property 'content' is missing in type
interface Chapter {
  id: string
  title: string
  content: string  // Required field
}

// ✅ Fix: Make optional for backward compatibility
interface Chapter {
  id: string
  title: string
  content?: string  // Optional field
}

// ✅ Fix: Add null checks in usage
setContent(chapter.content || '')
```

### 0.1. BaseComponentProps Compliance (BookFactory Standard)
```typescript
// ❌ Error: Component doesn't extend BaseComponentProps
interface MyComponentProps {
  title: string
}

// ✅ Fix: Extend BaseComponentProps
interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
  id?: string
  testId?: string
  'aria-label'?: string
  error?: string | null
  loading?: boolean
}

interface MyComponentProps extends BaseComponentProps {
  title: string
}
```

### 1. Unused Variables
```typescript
// ❌ Error: 'useState' is defined but never used
import { useState, useEffect } from 'react'

// ✅ Fix: Remove unused imports
import { useEffect } from 'react'

// ✅ Alternative: Prefix with underscore for intentionally unused
const handleClick = (_event: MouseEvent) => {
  console.log('clicked')
}
```

### 2. Missing Return Types
```typescript
// ❌ Error: Missing return type on function
const calculate = (a: number, b: number) => {
  return a + b
}

// ✅ Fix: Add explicit return type
const calculate = (a: number, b: number): number => {
  return a + b
}
```

### 3. Any Types
```typescript
// ❌ Error: Unexpected any
const processData = (data: any) => {}

// ✅ Fix: Use specific types
interface DataType {
  id: string
  value: number
}
const processData = (data: DataType) => {}

// ✅ Alternative: Use unknown for truly dynamic data
const processData = (data: unknown) => {
  if (typeof data === 'object' && data !== null) {
    // Type guards
  }
}
```

### 4. React Hook Dependencies
```typescript
// ❌ Error: Missing dependency
useEffect(() => {
  console.log(userId)
}, []) // userId missing

// ✅ Fix: Add all dependencies
useEffect(() => {
  console.log(userId)
}, [userId])

// ✅ Alternative: Disable for specific cases
useEffect(() => {
  // Only run once on mount
  initializeApp()
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])
```

### 5. Async/Await in useEffect
```typescript
// ❌ Error: useEffect must not return a promise
useEffect(async () => {
  await fetchData()
}, [])

// ✅ Fix: Use inner async function
useEffect(() => {
  const loadData = async () => {
    await fetchData()
  }
  loadData()
}, [])
```

## 📝 Formatierungsfehler

### 1. Import Order
```typescript
// ❌ Unorganized imports
import Button from './Button'
import React from 'react'
import { api } from '@/lib/api'
import styles from './styles.module.css'

// ✅ Organized imports (configure with eslint-plugin-import)
import React from 'react'                    // External
import { api } from '@/lib/api'              // Internal absolute
import Button from './Button'                // Internal relative
import styles from './styles.module.css'     // Styles
```

### 2. Line Length
```typescript
// ❌ Line too long
const reallyLongVariableName = someFunction(parameter1, parameter2, parameter3, parameter4, parameter5)

// ✅ Break into multiple lines
const reallyLongVariableName = someFunction(
  parameter1,
  parameter2,
  parameter3,
  parameter4,
  parameter5
)
```

### 3. Trailing Commas
```typescript
// ❌ Inconsistent trailing commas
const obj = {
  a: 1,
  b: 2
}

// ✅ Consistent trailing commas (configured in Prettier)
const obj = {
  a: 1,
  b: 2,
}
```

## 🛠️ BookFactory Auto-Fix Scripts für package.json
```json
{
  "scripts": {
    "lint": "next lint",
    "lint:fix": "next lint --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "type-check": "tsc --noEmit",
    "build": "next build",
    "build:check": "npm run type-check && npm run lint && npm run build",
    "pre-commit": "npm run type-check && npm run lint:fix && npm run format && npm run build:check",
    "fix-all": "npm run lint:fix && npm run format && npm run type-check",
    "validate": "npm run lint && npm run type-check && npm run build"
  }
}
```

## 🎯 VS Code Settings (.vscode/settings.json)
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "files.eol": "\n"
}
```

## 🚀 Quick Fixes Cheatsheet

### Disable Rules (Use Sparingly!)
```typescript
// Disable next line
// eslint-disable-next-line rule-name
problematicCode()

// Disable for file
/* eslint-disable rule-name */

// Disable for block
/* eslint-disable */
code block
/* eslint-enable */
```

### TypeScript Ignore (Last Resort!)
```typescript
// @ts-ignore - Use only when absolutely necessary
// @ts-expect-error - Better: expects an error
```

## 📊 BookFactory ESLint Rules Configuration

```javascript
{
  "rules": {
    // TypeScript (BookFactory Strict)
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-non-null-assertion": "error", // Stricter
    "@typescript-eslint/ban-ts-comment": "error", // Stricter
    "@typescript-eslint/no-unused-vars": ["error", {
      "argsIgnorePattern": "^_",
      "varsIgnorePattern": "^_",
      "destructuredArrayIgnorePattern": "^_"
    }],
    "@typescript-eslint/prefer-nullish-coalescing": "error",
    "@typescript-eslint/prefer-optional-chain": "error",
    "@typescript-eslint/strict-boolean-expressions": "warn",

    // React (Next.js + shadcn/ui optimized)
    "react/prop-types": "off", // TypeScript handles this
    "react/react-in-jsx-scope": "off", // Next.js handles this
    "react/no-unescaped-entities": "warn",
    "react/display-name": "off",
    "react-hooks/exhaustive-deps": "warn",
    "react/jsx-key": "error",
    "react/jsx-no-duplicate-props": "error",

    // Accessibility (BookFactory Standard)
    "jsx-a11y/anchor-is-valid": "off", // Next.js Link handling
    "jsx-a11y/click-events-have-key-events": "warn",
    "jsx-a11y/no-static-element-interactions": "warn",

    // General (BookFactory Standards)
    "no-console": ["warn", { "allow": ["warn", "error", "info"] }],
    "prefer-const": "error",
    "no-unused-expressions": "error",
    "no-var": "error",
    "object-shorthand": "error",
    "prefer-template": "error"
  }
}
```

## 🔍 Debugging Lint Issues

### 1. Check which rule is failing
```bash
npx eslint path/to/file.tsx --debug
```

### 2. See all available rules
```bash
npx eslint --print-config path/to/file.tsx
```

### 3. Ignore files (.eslintignore)
```
# Dependencies
node_modules/
.next/
out/
build/

# Generated files
*.generated.ts
*.d.ts

# Config files
next.config.js
```

## 💡 Best Practices

1. **Fix, Don't Disable**: Always try to fix the issue rather than disable the rule
2. **Configure Once**: Set up ESLint and Prettier at project start
3. **Pre-commit Hooks**: Use husky + lint-staged
4. **CI/CD Integration**: Run linting in your pipeline
5. **Team Alignment**: Share configs across team

## 🎨 Prettier Ignore
```typescript
// prettier-ignore
const matrix = [
  1, 0, 0,
  0, 1, 0,
  0, 0, 1
]
```

## 📦 Essential Dependencies
```bash
npm install -D eslint prettier eslint-config-prettier eslint-plugin-prettier @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

## 🔄 When Working with Existing Code

### Step-by-Step Cleanup
1. Run `npm run lint` to see all errors
2. Run `npm run lint:fix` to auto-fix what's possible
3. Run `npm run format` to fix formatting
4. Manually fix remaining errors
5. Commit with message: `fix: resolve lint and formatting errors`

### Gradual Migration
```javascript
// For large codebases, enable rules gradually
{
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn" // Start with warn
    // Later change to "error"
  }
}
```

## 🆘 BookFactory Emergency Fixes

### Service-Related Lint Issues:
```bash
# 1. Check service status first
python service_manager.py status

# 2. If services down, restart
python service_manager.py restart

# 3. Then fix lint issues
npm run fix-all
```

### When nothing else works:
1. **Stop all BookFactory services**: `python service_manager.py stop`
2. **Clean Node environment**: Delete `node_modules`, `.next`, `out`
3. **Clear all caches**:
   ```bash
   npx eslint --cache-location .eslintcache --cache
   rm -rf .next/cache
   npm cache clean --force
   ```
4. **Reinstall dependencies**: `npm install`
5. **Restart services**: `python service_manager.py start`
6. **Validate setup**: `npm run validate`
7. **Restart VS Code / IDE**

### BookFactory-Specific Conflicts:
- **Backend API errors**: Check port 8002 availability
- **Frontend build fails**: Verify Next.js config and TypeScript
- **Service startup issues**: Use `bulletproof_startup.py`
- **Prettier vs ESLint**: Use `eslint-config-prettier`
- **Different Node versions**: Use `.nvmrc` (Node 18+)
- **Windows vs Unix**: Configure `endOfLine` in Prettier
- **Memory issues**: Increase Node memory: `NODE_OPTIONS="--max-old-space-size=4096"`

## 🎯 BookFactory Development Principles:

### Core Rules:
- **Service Health First**: Always check `python service_manager.py status`
- **Interface Compliance**: All components must extend `BaseComponentProps`
- **TypeScript Strict**: No `any` types, proper null checks
- **Accessibility**: Follow WCAG guidelines with jsx-a11y
- **Consistency > Personal Preference**
- **Automate Everything Possible**
- **Fix Errors Before They Hit Production**

### BookFactory Workflow:
1. **Pre-Development**: Service status + lint check
2. **During Development**: Auto-save with format-on-save
3. **Pre-Commit**: `npm run pre-commit`
4. **Pre-Push**: `npm run validate`
5. **Post-Deployment**: Service health monitoring

### Error Priority:
1. **Critical**: Service failures, TypeScript errors
2. **High**: Interface mismatches, accessibility issues
3. **Medium**: ESLint errors, unused variables
4. **Low**: Formatting, markdown lint

### Memory Bank Integration:
- All fixes are automatically documented
- Patterns are learned and reapplied
- Service management is integrated with lint workflows
- UI guidelines compliance is enforced
- **Document Your Exceptions**
