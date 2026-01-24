# Windsurf Clarification Protocol

## MANDATORY RULE: Always Ask for Clarification When Requirements Are Unclear

### When to Apply This Rule:
- User request has multiple possible interpretations
- Requirements are vague or incomplete
- Technical approach could go in different directions
- Scope is undefined or ambiguous

### Protocol Steps:
1. **Identify the ambiguity** in the user's request
2. **Formulate a specific interpretation** with concrete assumptions
3. **Present it clearly** using this template:
   ```
   "Your request allows for multiple interpretations.
   I understand it as: [specific interpretation with concrete details]
   Should I proceed this way, or do you have different expectations?"
   ```
4. **Wait for confirmation** before implementing
5. **Proceed only after clarification** is received

### Examples:

#### Example 1: Vague Database Request
```
User: "Improve the database"
AI Response: "I understand this as: Optimize database performance by adding indexes to frequently queried columns and normalizing the table structure. Should I proceed this way, or did you mean something else like adding new features, restructuring the schema, or improving data validation?"
```

#### Example 2: Unclear UI Request
```
User: "Make the interface better"
AI Response: "I interpret this as: Modernize the UI by adding consistent styling, improving navigation with tabs, and enhancing the visual hierarchy with better spacing and colors. Should I focus on these aspects, or were you thinking of specific functionality improvements?"
```

#### Example 3: Ambiguous Feature Request
```
User: "Add user management"
AI Response: "I understand this as: Implement basic user authentication with login/logout functionality and user registration. Should I proceed with this scope, or did you need more advanced features like role-based permissions, user profiles, or admin management?"
```

### Benefits:
- Prevents wasted development time
- Ensures alignment with user expectations
- Reduces back-and-forth corrections
- Builds trust through clear communication
- Leads to better end results

### Integration with Development Workflow:
- Apply this rule before starting any implementation
- Use it during requirements gathering phase
- Implement it when user provides feedback
- Apply when extending existing features

---

**This protocol must be followed in all interactions to ensure effective collaboration and prevent misunderstandings.**
