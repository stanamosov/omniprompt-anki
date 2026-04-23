#!/usr/bin/env python3
"""Simple test of the regex pattern used in CodeBlockParser."""

import re

# The exact regex pattern from CodeBlockParser.parse()
block_pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"

# User's exact output format
test_output = """```Part(s) Of Speech
noun (masculine)
```

```English gloss
badge; card; insignia
```

```Sample context
Il a oublié son badge à l’entrée du bâtiment.
```

```English translation of sample context
He forgot his badge at the entrance of the building.
```

```Russian gloss
значок; пропуск; бейдж
```

```Extra
Usually refers to an identification badge or access card worn or carried for entry.
```"""

print("Testing regex pattern with user's exact output...")
print("=" * 60)

blocks = re.findall(block_pattern, test_output, re.DOTALL | re.UNICODE)

print(f"Found {len(blocks)} code blocks:")
for i, (label, content) in enumerate(blocks):
    print(f"\nBlock {i+1}:")
    print(f"  Label: '{label}'")
    print(f"  Content (first 50 chars): '{content.strip()[:50]}...'")

print("\n" + "=" * 60)
print("Testing field name extraction...")

# Check if parentheses cause issues
for label, content in blocks:
    label_stripped = label.strip()
    print(f"Label '{label_stripped}' -> stripped: '{label_stripped}'")

print("\n" + "=" * 60)
print("Testing case-insensitive matching...")

note_fields = [
    "Rank",
    "French Word", 
    "Part(s) Of Speech",
    "English gloss",
    "Sample context",
    "English translation of sample context",
    "Russian gloss",
    "Russian translation of sample context",
    "Audio clip media filename",
    "Thematic",
    "French Example Pronunciation",
    "Sample context with Russian Word",
    "Part of Speech",
    "IPA Transcription",
    "Extra"
]

selected_fields = ["Part(s) Of Speech", "English gloss", "Sample context", 
                   "English translation of sample context", "Russian gloss", "Extra"]

for label, content in blocks:
    label_stripped = label.strip()
    
    # Exact match
    if label_stripped in selected_fields:
        print(f"✓ Exact match: '{label_stripped}'")
        continue
    
    # Case-insensitive match
    label_lower = label_stripped.lower()
    selected_lower = [f.lower() for f in selected_fields]
    
    if label_lower in selected_lower:
        idx = selected_lower.index(label_lower)
        print(f"✓ Case-insensitive match: '{label_stripped}' -> '{selected_fields[idx]}'")
    else:
        print(f"✗ No match: '{label_stripped}'")

print("\n" + "=" * 60)
print("Testing complete!")