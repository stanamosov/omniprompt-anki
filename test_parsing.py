#!/usr/bin/env python3
"""Test the CodeBlockParser with the user's exact output format."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from __init__ import CodeBlockParser, logger

# Enable debug logging
logger.setLevel("DEBUG")

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

# User's note fields (from their description)
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

print("Testing CodeBlockParser with user's exact output...")
print("=" * 60)

parser = CodeBlockParser(note_fields)
fields = parser.parse(test_output)

print(f"Parsed {len(fields)} fields:")
for field_name, content in fields.items():
    print(f"  '{field_name}': '{content[:50]}...'")

print("\n" + "=" * 60)
print("Testing field mapping...")

# Test suggest_mappings
ai_fields = list(fields.keys())
mappings = parser.suggest_mappings(ai_fields, note_fields)
print(f"Mappings:")
for ai_field, mapped_field in mappings.items():
    print(f"  '{ai_field}' -> '{mapped_field}'")

print("\n" + "=" * 60)
print("Testing case-insensitive matching...")

# Test case-insensitive matching
selected_fields = ["Part(s) Of Speech", "English gloss", "Sample context", 
                   "English translation of sample context", "Russian gloss", "Extra"]

for ai_field in ai_fields:
    target_field = mappings.get(ai_field, ai_field)
    target_lower = target_field.lower().strip()
    selected_lower = [f.lower().strip() for f in selected_fields]
    
    if target_lower in selected_lower:
        print(f"✓ '{ai_field}' matches selected field '{target_field}'")
    else:
        print(f"✗ '{ai_field}' does not match any selected field")

print("\n" + "=" * 60)
print("Testing complete!")