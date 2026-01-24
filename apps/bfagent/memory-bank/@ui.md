# BookFactory UI Development Guidelines

## Project Configuration (Updated 2025)
- **Framework**: Next.js 14+ (App Router) ✅ *Currently Used*
- **Styling**: Tailwind CSS + shadcn/ui ✅ *Currently Used*
- **UI Library**: shadcn/ui (Radix UI based) ✅ *Currently Used*
- **State**: React Context + useState (Zustand for complex state)
- **Testing**: Jest + RTL + Playwright (E2E)
- **Animation**: Framer Motion + CSS Transitions
- **Icons**: Lucide React ✅ *Currently Used*
- **Language**: TypeScript (strict mode) ✅ *Currently Used*
- **Error Handling**: ErrorBoundary components ✅ *Currently Used*

## Core Development Principles (BookFactory-Specific)
1. **Component Hierarchy**: shadcn/ui base → Custom variants → Feature components
2. **Type-Safe**: Full TypeScript with proper interfaces (NO `any` types)
3. **Autonomous-First**: Components should handle their own error states
4. **Accessible**: WCAG 2.1 AA compliance + keyboard navigation
5. **Performance**: Lazy load, React.memo, virtual scroll for large datasets
6. **Mobile-First**: Responsive design with breakpoint consistency
7. **Self-Healing**: Components should gracefully handle API failures
8. **Real-time Ready**: Design for WebSocket updates and live collaboration

## Component Standards

### All Components Must Have:
```
ComponentName/
├── ComponentName.tsx       // Main component
├── ComponentName.test.tsx  // Tests
├── ComponentName.stories.tsx // Storybook
├── ComponentName.module.css // Styles (if needed)
├── index.ts               // Exports
└── README.md             // Documentation
```

### Standard Props Interface (BookFactory):
```typescript
interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
  id?: string
  testId?: string
  // Accessibility
  'aria-label'?: string
  'aria-describedby'?: string
  // Error handling
  error?: string | null
  loading?: boolean
  // Project context
  projectId?: string
  // Event handlers
  onClick?: (event: React.MouseEvent) => void
  onError?: (error: Error) => void
}

// Project-specific interfaces
interface ProjectContextProps {
  projectId: string
  projectName: string
  onProjectChange?: (project: Project) => void
}

interface ChapterContextProps {
  chapterId?: string
  chapterTitle?: string
  onChapterSelect?: (chapter: Chapter) => void
}
```

## Design System Tokens (BookFactory)
```css
/* shadcn/ui CSS Variables - Always use these */
--background: 0 0% 100%;
--foreground: 222.2 84% 4.9%;
--card: 0 0% 100%;
--card-foreground: 222.2 84% 4.9%;
--primary: 221.2 83.2% 53.3%;
--primary-foreground: 210 40% 98%;
--secondary: 210 40% 96%;
--secondary-foreground: 222.2 84% 4.9%;
--accent: 210 40% 96%;
--accent-foreground: 222.2 84% 4.9%;
--destructive: 0 84.2% 60.2%;
--destructive-foreground: 210 40% 98%;
--border: 214.3 31.8% 91.4%;
--input: 214.3 31.8% 91.4%;
--ring: 221.2 83.2% 53.3%;
--radius: 0.5rem;

/* BookFactory-specific tokens */
--sidebar-width: 280px;
--header-height: 64px;
--chapter-card-height: 120px;
--editor-min-height: 400px;
```

## Component Checklist
- [ ] TypeScript interfaces defined
- [ ] Props documented with JSDoc
- [ ] Unit tests cover all states
- [ ] Storybook story created
- [ ] Keyboard navigation works
- [ ] Screen reader tested
- [ ] Responsive behavior verified
- [ ] Error states handled
- [ ] Loading states implemented
- [ ] Dark mode supported

## BookFactory Component Patterns

### Project Card Variants
```typescript
type ProjectStatus = 'active' | 'draft' | 'review' | 'complete' | 'archived'
type ProjectCardSize = 'compact' | 'default' | 'detailed'

interface ProjectCardProps extends BaseComponentProps {
  project: {
    id: string
    title: string
    progress: number
    status: ProjectStatus
    chapters: number
    collaborators: number
  }
  selected?: boolean
  onSelect?: (project: Project) => void
  variant?: ProjectCardSize
}
```

### Chapter Management States
```typescript
type ChapterStatus = 'draft' | 'review' | 'complete'
type ChapterView = 'navigation' | 'management' | 'editor'

interface ChapterState {
  id: string
  title: string
  content: string
  status: ChapterStatus
  wordCount: number
  lastModified: Date
  order: number
  error?: string
  loading?: boolean
  saving?: boolean
}
```

### Editor Component Patterns
```typescript
interface EditorProps extends BaseComponentProps {
  content: string
  onChange: (content: string) => void
  onSave?: () => Promise<void>
  autoSave?: boolean
  autoSaveDelay?: number
  placeholder?: string
  readOnly?: boolean
  projectName?: string | null
}
```

### Sidebar Navigation

```typescript
type SidebarSection = 'projects' | 'chapters' | 'agents' | 'analytics' | 'settings'

interface SidebarProps {
  activeSection?: SidebarSection
  onSectionChange?: (section: SidebarSection) => void
  collapsed?: boolean
  onToggle?: () => void
}
```

### Modal/Dialog Sizes (shadcn/ui)

```typescript
type DialogSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'
type SheetSide = 'top' | 'right' | 'bottom' | 'left'
```

## Testing Requirements (BookFactory-Specific)

1. **Unit Tests**: Component logic and rendering
   - Test project switching functionality
   - Test chapter CRUD operations
   - Test error boundary behavior
   - Mock API calls with MSW

2. **Integration Tests**: User interactions
   - Project card selection and state updates
   - Chapter navigation and content loading
   - Sidebar collapse/expand behavior
   - Editor auto-save functionality

3. **A11y Tests**: Accessibility compliance
   - Keyboard navigation through projects/chapters
   - Screen reader compatibility for editor
   - Focus management in modals/dialogs
   - Color contrast in all themes

4. **Visual Tests**: Storybook snapshots
   - All component variants and states
   - Dark/light theme variations
   - Responsive breakpoints
   - Loading and error states

5. **E2E Tests**: Critical user flows
   - Complete project creation workflow
   - Chapter editing and saving
   - Project switching without errors
   - Backend connectivity and recovery

## Performance Guidelines (BookFactory)

### Critical Performance Metrics
- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Cumulative Layout Shift**: < 0.1
- **First Input Delay**: < 100ms

### BookFactory-Specific Optimizations
- **Project Lists**: Virtual scrolling for > 50 projects
- **Chapter Content**: Lazy load chapter content on demand
- **Editor**: Debounce auto-save (500ms for better UX)
- **API Calls**: Implement optimistic updates for chapter saves
- **State Updates**: Use React.memo for project cards
- **Bundle Size**: Code-split by feature (projects, chapters, editor)
- **Images**: Use Next.js Image for project thumbnails
- **Animations**: Respect prefers-reduced-motion
- **WebSocket**: Throttle real-time updates to prevent UI lag

## Accessibility Must-Haves
- Focus indicators: Visible and styled
- ARIA labels: All interactive elements
- Keyboard nav: Tab order logical
- Touch targets: Minimum 44x44px
- Color contrast: 4.5:1 minimum
- Error messages: Clear and actionable

## State Management Rules
1. Local state first (useState)
2. Lift state only when needed
3. Context for cross-cutting concerns
4. Zustand for complex app state
5. No prop drilling beyond 2 levels

## Styling Priorities
1. Tailwind utilities first
2. CSS Modules for complex styles
3. CSS-in-JS only if absolutely needed
4. Never use inline styles
5. Theme via CSS variables

## Code Quality Standards
- ESLint: No warnings allowed
- Prettier: Auto-format on save
- TypeScript: No `any` types
- Comments: Only for complex logic
- Naming: Descriptive and consistent

## Git Commit Format
```
type(scope): description

- feat: New feature
- fix: Bug fix
- style: UI/UX changes
- test: Test updates
- docs: Documentation
- refactor: Code improvement
- perf: Performance optimization
```

## Review Checklist
Before marking PR ready:
- [ ] All tests passing
- [ ] No console errors/warnings
- [ ] Lighthouse score > 90
- [ ] Bundle size checked
- [ ] Cross-browser tested
- [ ] Mobile experience verified
- [ ] Documentation updated

## Common Utilities

### Hooks
- `useDebounce(value, delay)`
- `useMediaQuery(query)`
- `useOnClickOutside(ref, handler)`
- `useLocalStorage(key, defaultValue)`
- `usePrevious(value)`

### Utils
- `cn()` - className merger (clsx + twMerge)
- `formatDate()` - Consistent date formatting
- `truncate()` - Text truncation
- `generateId()` - Unique ID generation

## API Integration (BookFactory)

### Data Fetching Strategy
- **Primary**: Native fetch with custom hooks
- **Fallback**: React Query for complex caching needs
- **Real-time**: WebSocket for live collaboration
- **Offline**: Service Worker for basic offline support

### BookFactory API Patterns
```typescript
// Project API
interface ProjectAPI {
  getProjects(): Promise<Project[]>
  getProject(id: string): Promise<Project>
  createProject(data: CreateProjectData): Promise<Project>
  updateProject(id: string, data: UpdateProjectData): Promise<Project>
  deleteProject(id: string): Promise<void>
}

// Chapter API
interface ChapterAPI {
  getChapters(projectId: string): Promise<Chapter[]>
  getChapter(id: string): Promise<Chapter>
  createChapter(projectId: string, data: CreateChapterData): Promise<Chapter>
  updateChapter(id: string, data: UpdateChapterData): Promise<Chapter>
  deleteChapter(id: string): Promise<void>
  saveChapterContent(id: string, content: string): Promise<void>
}
```

### Error Handling Strategy
- **Network Errors**: Show retry button with exponential backoff
- **API Errors**: Display user-friendly error messages
- **Validation Errors**: Inline field-level error display
- **Timeout Errors**: Auto-retry with loading indicator
- **Backend Unavailable**: Graceful degradation with offline mode

### Caching Strategy
- **Projects**: Cache for 5 minutes, invalidate on updates
- **Chapters**: Cache for 2 minutes, invalidate on edits
- **Chapter Content**: No cache, always fresh for editing
- **User Preferences**: Local storage with sync

## Remember
- User experience > Developer experience
- Accessibility is not optional
- Performance impacts retention
- Consistency builds trust
- Test early, test often
