#!/usr/bin/env python
# Test field extraction with new format

import re

# New format from LLM
test_content = """
1. **Peter Müller**
   - **Role**: The conflicted hero
   - **Background**: A former police officer turned private investigator, haunted by a case that went wrong.
   - **Motivation**: To protect Hilde and seek redemption for his past failures.
   - **Personality**: Brooding, passionate, resourceful, conflicted
   - **Character Arc**: From protector to potential monster, struggling with inner demons
"""

fields = {
    "description": ["profile", "description"],
    "motivation": ["motivation", "goal"],
    "personality": ["traits", "personality"],
    "arc": ["character arc", "arc", "development"],
    "background": ["background", "backstory", "history"],
}

print("Testing field extraction:\n")

for model_field, keywords in fields.items():
    for keyword in keywords:
        # Try with bullet/indent first (new format)
        pattern = rf"(?:^|\n)\s*-\s*\*\*{keyword}\*\*:?\s*(.+?)(?=\n\s*-\s*\*\*|\n\n|$)"
        match = re.search(pattern, test_content, re.IGNORECASE | re.DOTALL)

        if not match:
            # Try without bullet (old format)
            pattern = rf"\*\*{keyword}\*\*:?\s*(.+?)(?=\n\s*-|\n\s*\*\*|$)"
            match = re.search(pattern, test_content, re.IGNORECASE | re.DOTALL)

        if match:
            value = match.group(1).strip()
            value = " ".join(value.split())
            print(f"{model_field:15} ✅ {value[:80]}...")
            break
    else:
        print(f"{model_field:15} ❌ Not found")

print("\n" + "=" * 80)
print("Expected:")
print("  description:   ❌ Not found (no 'Profile' field)")
print("  background:    ✅ A former police officer...")
print("  motivation:    ✅ To protect Hilde...")
print("  personality:   ✅ Brooding, passionate...")
print("  arc:           ✅ From protector to potential monster...")
