# BookFactory - Multi-Genre AI Book Development Platform
# This file configures Windsurf AI behavior for this specific project

## 🎯 Project Context

**Project Type**: AI-Powered Book Writing Platform
**Development Stage**: MVP/Development (Phase 1)
**Team Size**: 1-2 developers
**Primary Language**: Python
**AI Assistance Level**: High (90% AI-assisted)
**Core Mission**: Multi-genre book creation with incremental complexity

## 🏗️ Architecture Overview

### Technology Stack

- **Frontend**: Streamlit (Phase 1), React/Next.js (Phase 2+)
- **Backend**: FastAPI + Python 3.11+
- **Database**: SQLite (MVP), PostgreSQL + SQLModel (Production)
- **AI/ML**: OpenAI API, Local LLMs (Ollama), CrewAI
- **Testing**: Pytest, Streamlit Testing
- **Deployment**: Docker, Railway/Vercel

### Architecture Pattern

## 📋 Windsurf AI Instructions

### CRITICAL - Always Active Rules
1. **MUST** read `@project-context.md` before ANY code generation
2. **MUST** follow patterns in `@architecture.md` exactly
3. **MUST** update `progress.md` after completing tasks
4. **MUST** run type checking before considering task complete
5. **MUST** maintain test coverage above 80%
6. **MUST** use `@meta-prompt-generator.md` for vague user requests

### Context Priority (in order)
1. Files marked with @ in memory-bank/
2. Currently open files in editor
3. Recently modified files (last 24h)
4. Test files related to current work
5. Package.json and configuration files

## 🗂️ File Organization Standards

### Naming Conventions
```typescript
// Components
ComponentName.tsx           // PascalCase
ComponentName.test.tsx      // Test files
ComponentName.stories.tsx   // Storybook
ComponentName.module.css    // Styles

// Hooks
useFeatureName.ts          // camelCase with 'use' prefix
useFeatureName.test.ts

// Services
UserService.ts             // PascalCase with 'Service' suffix
ApiService.ts

// Utilities
formatDate.ts              // camelCase
validateEmail.ts

// Types
user.types.ts              // lowercase with .types suffix
api.types.ts

// Constants
API_ENDPOINTS.ts           // UPPER_SNAKE_CASE
CONFIG.ts
```

### Import Order
```typescript
// 1. External dependencies
import React from 'react';
import { useQuery } from '@tanstack/react-query';

// 2. Internal absolute imports
import { Button } from '@/components/ui';
import { useAuth } from '@/hooks';

// 3. Relative imports
import { formatDate } from './utils';
import type { UserProps } from './types';

// 4. Style imports
import styles from './Component.module.css';
```

## 💻 Code Style Guidelines

### React Components
```typescript
// ✅ Preferred: Function components with TypeScript
interface ButtonProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  onClick,
  children
}) => {
  // Implementation
};

// ❌ Avoid: Class components, PropTypes
```

### State Management with Zustand
```typescript
// Store definition pattern
interface StoreState {
  // State
  users: User[];
  loading: boolean;

  // Actions
  fetchUsers: () => Promise<void>;
  addUser: (user: User) => void;
  reset: () => void;
}

export const useUserStore = create<StoreState>((set) => ({
  // Implementation
}));
```

### API Layer Pattern
```typescript
// Service pattern with error handling
export class UserService {
  private api: ApiClient;

  async getUsers(): Promise<Result<User[], ApiError>> {
    try {
      const response = await this.api.get<User[]>('/users');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: parseApiError(error) };
    }
  }
}
```

## 🧪 Testing Requirements

### Test Structure
```typescript
describe('ComponentName', () => {
  // Setup
  beforeEach(() => {
    // Common setup
  });

  // Group related tests
  describe('when user is authenticated', () => {
    it('should display user menu', () => {
      // Test implementation
    });
  });

  // Edge cases
  describe('error states', () => {
    it('should handle network errors gracefully', () => {
      // Test implementation
    });
  });
});
```

### Coverage Requirements
- Statements: 80%
- Branches: 75%
- Functions: 80%
- Lines: 80%
- Critical paths: 95%

## 🔐 Security Patterns

### Input Validation
```typescript
// Always use Zod for validation
import { z } from 'zod';

const UserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).regex(/[A-Z]/).regex(/[0-9]/),
  age: z.number().min(18).max(120)
});

// Use in API routes
export const createUser = async (req: Request) => {
  const result = UserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  // Proceed with validated data
};
```

### Authentication Pattern
```typescript
// Middleware pattern
export const requireAuth = async (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    const user = await verifyToken(token);
    req.user = user;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};
```

## 🚀 Performance Guidelines

### React Optimization
```typescript
// Use React.memo for expensive components
export const ExpensiveComponent = React.memo(({ data }: Props) => {
  // Component implementation
}, (prevProps, nextProps) => {
  // Custom comparison
  return prevProps.data.id === nextProps.data.id;
});

// Use useMemo for expensive calculations
const processedData = useMemo(() => {
  return expensiveCalculation(rawData);
}, [rawData]);

// Use useCallback for stable function references
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
```

### Bundle Optimization
- Lazy load routes
- Code split by feature
- Tree shake imports
- Optimize images (<100KB)
- Use WebP format

## 🔄 Git Workflow

### Branch Strategy
```bash
main          # Production-ready code
├── develop   # Integration branch
    ├── feature/add-user-dashboard
    ├── feature/implement-search
    ├── bugfix/fix-login-error
    └── hotfix/security-patch
```

### Commit Message Format
```
type(scope): subject

[optional body]

[optional footer]

# Examples:
feat(auth): add OAuth2 integration
fix(ui): resolve button alignment issue
refactor(api): simplify user service
test(auth): add integration tests
docs(readme): update setup instructions
```

### PR Guidelines
- Title must follow commit format
- Description must include:
  - What changed
  - Why it changed
  - How to test
  - Screenshots (for UI changes)

## 🤖 Windsurf Mode Usage

### When to Use Flow Mode
- Designing new features
- Major refactoring
- Performance optimization
- Exploring multiple solutions
- Architecture decisions

### When to Use Agent Mode
- Implementing defined features
- Writing tests
- Fixing bugs
- Updating documentation
- Routine maintenance

### When to Use Review Mode
- Before creating PRs
- Security audits
- Performance analysis
- Code quality checks
- Learning from patterns

## 📊 Project-Specific Patterns

### Custom Hooks Pattern
```typescript
// All custom hooks in src/hooks/
export function useFeature() {
  // 1. State from stores
  const { data, loading } = useFeatureStore();

  // 2. External hooks
  const { user } = useAuth();

  // 3. Effects
  useEffect(() => {
    // Side effects
  }, [dependencies]);

  // 4. Handlers
  const handleAction = useCallback(() => {
    // Implementation
  }, [dependencies]);

  // 5. Return interface
  return {
    data,
    loading,
    handleAction
  };
}
```

### Error Boundary Pattern
```typescript
// Wrap feature sections
<ErrorBoundary fallback={<ErrorFallback />}>
  <FeatureComponent />
</ErrorBoundary>
```

## 🚫 DO NOT - Project Specific

### Never Allow AI To:
- Remove TypeScript types
- Disable strict mode
- Use 'any' type
- Skip tests
- Use var instead of const/let
- Commit console.log statements
- Use inline styles
- Create files outside src/
- Modify configuration without approval

### Code Smells to Avoid
- Functions > 40 lines
- Files > 300 lines
- Nested ternaries
- Magic numbers
- Duplicate code
- Mixed concerns
- Global variables
- Direct DOM manipulation

## 📈 Success Metrics

### Code Quality Targets
- TypeScript coverage: 100%
- Test coverage: >80%
- Bundle size: <200KB initial
- Lighthouse score: >90
- Build time: <30s
- No ESLint warnings

### AI Assistance Metrics
Track in progress.md:
- Features completed with AI
- Time saved estimates
- Refactors needed
- Bugs introduced/fixed
- Learning moments

## 🔧 Custom Windsurf Commands

### Project Shortcuts
```
@test-all: Run full test suite with coverage
@build-check: Type check + lint + test + build
@analyze-bundle: Generate bundle analysis
@update-deps: Update dependencies safely
@generate-types: Generate types from API
```

---

*Project-specific rules override global rules where applicable*
*Review and update these rules monthly*
*Version: 1.0*
