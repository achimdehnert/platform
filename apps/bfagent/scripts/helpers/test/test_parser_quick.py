#!/usr/bin/env python
# Quick regex test

import re

test_content = """
#### Protagonist
1. **Peter Müller**
   - **Role**: The conflicted hero
   - **Background**: A former police officer

2. **Anna Schmidt**
   - **Role**: Love interest

#### Supporting Characters
- **Hilde Schneider**: In her late 20s...

- **Detective Lena Roth**: A seasoned detective...

- **Psychological Complexity**: Characters will experience...

- **Motifs**: Incorporate visual motifs...
"""

# Test NEW pattern (supports both - and 1. format)
char_pattern = r'(?:^|\n)\s*(?:-|\d+\.)\s*\*\*([A-Z][a-zA-ZäöüÄÖÜß]+(?:\s+(?:"[^"]+")?\s*[A-Z][a-zA-ZäöüÄÖÜß]+)*)\*\*:?'
matches = list(re.finditer(char_pattern, test_content, re.MULTILINE))

print(f"Found {len(matches)} potential matches:")
for match in matches:
    name = match.group(1)
    word_count = len(name.split())
    print(f"  - {name} (words: {word_count})")

# Now apply filters
field_blacklist = {"Psychological Complexity", "Motifs", "Role", "Background"}
blacklist_keywords = ["Complexity", "Suggestions"]

print("\nAfter filtering:")
for match in matches:
    name = match.group(1).strip()
    word_count = len(name.split())
    is_valid = (
        name not in field_blacklist
        and not any(bl in name for bl in blacklist_keywords)
        and word_count >= 2
        and name[0].isupper()
    )
    if is_valid:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} (filtered out)")

# Expected valid: Peter Müller, Anna Schmidt, Hilde Schneider, Detective Lena Roth
