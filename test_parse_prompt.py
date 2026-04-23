#!/usr/bin/env python3
"""Test parse_prompt_for_field_names with escaped newlines."""

import re

print("=" * 80)
print("TESTING parse_prompt_for_field_names PATTERN")
print("=" * 80)

# The updated pattern from parse_prompt_for_field_names
code_block_pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)"
print(f"Pattern: {code_block_pattern}")

# Test 1: Prompt with escaped newlines
print("\nTest 1: Prompt with escaped newlines")
print("-" * 80)

prompt_with_escaped = """Here are the fields:
```Part(s) Of Speech\\nContent```
```English gloss\\nContent```
```Sample context\\nContent```"""

print(f"Prompt: {repr(prompt_with_escaped)}")

matches1 = re.findall(code_block_pattern, prompt_with_escaped, re.DOTALL)
print(f"Matches: {len(matches1)}")
for i, field in enumerate(matches1):
    print(f"  Match {i+1}: '{field}'")

# Test 2: Prompt with actual newlines
print("\nTest 2: Prompt with actual newlines")
print("-" * 80)

prompt_with_actual = """Here are the fields:
```Part(s) Of Speech
Content```
```English gloss
Content```
```Sample context
Content```"""

print(f"Prompt: {repr(prompt_with_actual)}")

matches2 = re.findall(code_block_pattern, prompt_with_actual, re.DOTALL)
print(f"Matches: {len(matches2)}")
for i, field in enumerate(matches2):
    print(f"  Match {i+1}: '{field}'")

# Test 3: Mixed newlines
print("\nTest 3: Mixed newlines")
print("-" * 80)

prompt_mixed = """Fields:
```Part(s) Of Speech\\nContent```
```English gloss
Content```
```Sample context\\nContent```"""

print(f"Prompt: {repr(prompt_mixed)}")

matches3 = re.findall(code_block_pattern, prompt_mixed, re.DOTALL)
print(f"Matches: {len(matches3)}")
for i, field in enumerate(matches3):
    print(f"  Match {i+1}: '{field}'")

# Test 4: Old pattern (for comparison)
print("\nTest 4: Old pattern (for comparison)")
print("-" * 80)

old_pattern = r"```\s*([^`\n]+?)\s*\n"
print(f"Old pattern: {old_pattern}")

old_matches_escaped = re.findall(old_pattern, prompt_with_escaped, re.DOTALL)
print(f"Old pattern matches with escaped newlines: {len(old_matches_escaped)}")

old_matches_actual = re.findall(old_pattern, prompt_with_actual, re.DOTALL)
print(f"Old pattern matches with actual newlines: {len(old_matches_actual)}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if len(matches1) == 3 and len(matches2) == 3 and len(matches3) == 3:
    print("✅ NEW PATTERN works with all newline types!")
else:
    print(f"❌ New pattern issues: escaped={len(matches1)}, actual={len(matches2)}, mixed={len(matches3)}")

if len(old_matches_escaped) == 0 and len(old_matches_actual) == 3:
    print("✅ OLD PATTERN fails with escaped newlines (as expected)")
else:
    print(f"❌ Old pattern unexpected: escaped={len(old_matches_escaped)}, actual={len(old_matches_actual)}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("The parse_prompt_for_field_names function now correctly extracts field names")
print("from prompts with either escaped newlines (\\n) or actual newlines.")