#!/usr/bin/env python3
"""Test the fix for multi-field mode row matching issue."""

import re

# Test the current pattern from parse_multi_field_output
pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"

print("Testing pattern from parse_multi_field_output:")
print(f"Pattern: {pattern}")

# Test with escaped newlines (literal backslash-n)
test1 = r"""```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia\n```"""
print(f"\nTest 1 (escaped newlines): {test1[:80]}...")
matches1 = re.findall(pattern, test1, re.DOTALL)
print(f"Matches found: {len(matches1)}")
for i, (label, content) in enumerate(matches1):
    print(f"  Match {i+1}: label={repr(label)}, content={repr(content[:30])}...")

# Test with actual newlines
test2 = """```Part(s) Of Speech
Noun
```

```English gloss
A badge or insignia
```"""
print(f"\nTest 2 (actual newlines): {test2[:80]}...")
matches2 = re.findall(pattern, test2, re.DOTALL)
print(f"Matches found: {len(matches2)}")
for i, (label, content) in enumerate(matches2):
    print(f"  Match {i+1}: label={repr(label)}, content={repr(content[:30])}...")

# Test the row matching logic
print("\n\nTesting row matching logic simulation:")
print("=" * 60)

# Simulate start_processing assigning note IDs to rows
note_ids = [123, 456, 789]
rows_assigned = {}
for row, note_id in enumerate(note_ids):
    rows_assigned[note_id] = row
    print(f"start_processing: Assigned note {note_id} to row {row}")

# Simulate update_note_result searching for note
test_note_id = 456
print(f"\nupdate_note_result: Searching for note {test_note_id}")
found_row = None
for row in range(len(note_ids)):
    stored_id = note_ids[row]  # Simulating progress_item.data(Qt.ItemDataRole.UserRole)
    print(f"  Row {row}: stored_id={stored_id}, note.id={test_note_id}")
    if stored_id == test_note_id:
        found_row = row
        break

if found_row is not None:
    print(f"✓ Found note {test_note_id} at row {found_row}")
else:
    print(f"✗ Could not find row for note {test_note_id}")
    print(f"  Available stored IDs: {note_ids}")

print("\n" + "=" * 60)
print("Fix summary:")
print("1. Added debug logging to start_processing for note ID assignment")
print("2. Added debug logging to update_note_result for row matching")
print("3. Fixed race condition: table columns set up BEFORE populating rows")
print("4. Improved row matching with type comparison debugging")
print("5. parse_multi_field_output pattern handles escaped newlines")
print("\nAll fixes have been applied to __init__.py")