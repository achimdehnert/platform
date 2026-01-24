# Windsurf Global Rules - Professional AI Development Standards

## 🤖 AI Agent Core Behavior

### MANDATORY Rules (Always Active)
- **ALWAYS** read files prefixed with @ in memory-bank before ANY code generation
- **ALWAYS** validate understanding by summarizing the task before implementation
- **ALWAYS** run relevant tests after code changes
- **ALWAYS** update progress tracking after completing features
- **ALWAYS** use @meta-prompt-generator.md when user request is vague or unstructured
- **NEVER** delete existing tests or remove security validations
- **NEVER** commit directly to main/master branch
- **NEVER** use deprecated patterns or libraries

### Context Management
- Maximum context window: Prioritize recent changes and @ marked files
- When context is full, summarize and retain critical information
- Reference specific files using relative paths from project root
- Maintain conversation continuity by referencing previous decisions

## 📝 Code Quality Standards

### TypeScript Requirements
```typescript
// REQUIRED Configuration
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

### Function Standards
- Maximum length: 40 lines (excluding comments)
- Maximum parameters: 4 (use object for more)
- Must have JSDoc for public APIs
- Single responsibility principle
- Early returns over nested conditions

### File Organization
- One component/class per file
- Maximum file length: 300 lines
- Related files grouped in feature folders
- Shared code in dedicated directories

## 🏗️ Architecture Principles

### Clean Architecture Layers
1. **Presentation**: UI components, pages
2. **Application**: Business logic, use cases
3. **Domain**: Core entities, interfaces
4. **Infrastructure**: External services, APIs

### Dependency Rules
- Dependencies point inward (UI → Domain)
- Domain layer has zero dependencies
- Use dependency injection
- Interfaces over concrete implementations

## 🧪 Testing Requirements

### Coverage Standards
- Minimum overall: 80%
- Critical paths: 95%
- New features: 100%
- Bug fixes: Include regression tests

### Test Types Priority
1. Unit tests for business logic
2. Integration tests for API endpoints
3. Component tests for UI behavior
4. E2E tests for critical user flows

## 🔒 Security First Development

### Input Validation
- Validate ALL external inputs
- Use schema validation (Zod/Joi/Yup)
- Sanitize user-generated content
- Reject invalid data early

### Authentication & Authorization
- Use established auth libraries
- Implement proper session management
- Apply principle of least privilege
- Log security-relevant events

### Data Protection
- Never log sensitive information
- Encrypt data at rest and in transit
- Use environment variables for secrets
- Implement rate limiting

## ⚡ Performance Standards

### Frontend Performance
- Initial bundle size: <200KB
- Lazy load routes and heavy components
- Image optimization: <100KB per image
- Core Web Vitals compliance

### Backend Performance
- API response time: <500ms (p95)
- Database query optimization required
- Implement caching strategies
- Use pagination for lists

## 🔄 Development Workflow

### Git Conventions
```bash
# Branch naming
feature/short-descriptive-name
bugfix/issue-number-description
hotfix/critical-issue-description

# Commit message format
type(scope): subject

# Types
feat: New feature
fix: Bug fix
refactor: Code refactoring
test: Adding tests
docs: Documentation
perf: Performance improvement
style: Code style changes
chore: Maintenance tasks
```

### Code Review Checklist
- [ ] Follows architecture patterns
- [ ] Includes appropriate tests
- [ ] Updates documentation
- [ ] No security vulnerabilities
- [ ] Performance impact assessed
- [ ] Accessibility considered

## 🚀 Windsurf-Specific Optimizations

### Flow Mode Guidelines
- Use for architectural decisions
- Complex refactoring tasks
- Performance optimization
- Exploring solution options

### Agent Mode Guidelines
- Feature implementation
- Bug fixes
- Test generation
- Documentation updates

### Collaboration Features
- Enable real-time sharing for pair programming
- Use comments for context sharing
- Maintain clear task boundaries
- Document decisions in memory-bank

## 📊 Error Handling Standards

### Error Types
```typescript
// User errors: Clear, actionable messages
class UserError extends Error {
  constructor(message: string, public code: string) {
    super(message);
  }
}

// System errors: Log details, show generic message
class SystemError extends Error {
  constructor(message: string, public details: unknown) {
    super(message);
  }
}
```

### Logging Requirements
- Use structured logging
- Include correlation IDs
- Log level appropriate info
- Never log passwords or tokens

## 🎨 UI/UX Standards

### Accessibility Requirements
- WCAG 2.1 AA compliance
- Semantic HTML required
- ARIA labels where needed
- Keyboard navigation support
- Screen reader compatibility

### Responsive Design
- Mobile-first approach
- Test on multiple viewports
- Progressive enhancement
- Graceful degradation

## 📚 Documentation Standards

### Code Documentation
- JSDoc for public APIs
- Inline comments for complex logic
- README for each module
- Architecture decision records

### User Documentation
- Clear setup instructions
- API documentation
- Troubleshooting guides
- Example implementations

## 🔧 Tooling Configuration

### Required Extensions
- ESLint with team config
- Prettier with team config
- TypeScript language service
- GitLens for version control

### Automation
- Pre-commit hooks for linting
- Automated testing in CI/CD
- Dependency vulnerability scanning
- Code quality metrics

## 🌟 Best Practices

### Do's
- ✅ Write self-documenting code
- ✅ Refactor as you go
- ✅ Keep dependencies updated
- ✅ Use meaningful variable names
- ✅ Handle edge cases explicitly

### Don'ts
- ❌ Premature optimization
- ❌ Copy-paste programming
- ❌ Ignore linter warnings
- ❌ Leave TODOs indefinitely
- ❌ Use magic numbers/strings

## 📈 Continuous Improvement

### Code Metrics to Track
- Cyclomatic complexity
- Test coverage trends
- Bundle size over time
- Performance metrics
- Security scan results

### Regular Reviews
- Weekly code quality review
- Monthly dependency audit
- Quarterly architecture review
- Annual tech debt assessment

---

*These global rules apply to ALL Windsurf projects*
*Last Updated: [Auto-update on save]*
*Version: 2.0*
