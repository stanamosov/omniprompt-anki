#!/usr/bin/env python3
"""Test regex patterns with escaped newlines."""

import re

# User's exact raw output with escaped newlines
raw_output = """```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

print("Testing current regex pattern...")
print("=" * 60)

# Current regex from CodeBlockParser
current_pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
print(f"Current pattern: {current_pattern}")

matches = re.findall(current_pattern, raw_output, re.DOTALL | re.UNICODE)
print(f"Found {len(matches)} matches with current pattern")

for i, (label, content) in enumerate(matches):
    print(f"\nMatch {i+1}:")
    print(f"  Label: '{label}'")
    print(f"  Content (first 50 chars): '{content.strip()[:50]}...'")

print("\n" + "=" * 60)
print("Testing new pattern with escaped newlines...")

# New pattern that handles both \n and \\n
# We need to match: ```FieldName\nContent``` OR ```FieldName\\nContent```
# The tricky part is that \n in the string is actually a backslash followed by n
# In regex, we need to match literal backslash-n: \\\\n (escaped backslash, then n)
# Actually, in Python string, \\n is two characters: backslash and n
# So we need to match either actual newline \n (which is \n) or literal backslash-n (\\n)

# Option 1: Preprocess to convert \\n to \n
print("\nOption 1: Preprocess to convert \\\\n to \\n")
processed = raw_output.replace('\\n', '\n')
matches = re.findall(current_pattern, processed, re.DOTALL | re.UNICODE)
print(f"Found {len(matches)} matches after preprocessing")

# Option 2: Regex that matches both
print("\nOption 2: Regex that matches both actual newline and \\\\n")
# Pattern: ``` whitespace* fieldname whitespace* (?:\\n|\n) content whitespace* ```
# The (?:\\n|\n) matches either literal backslash-n or actual newline
# But we need to escape the backslash properly: \\\\n
new_pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
print(f"New pattern: {new_pattern}")

matches = re.findall(new_pattern, raw_output, re.DOTALL | re.UNICODE)
print(f"Found {len(matches)} matches with new pattern")

for i, (label, content) in enumerate(matches):
    print(f"\nMatch {i+1}:")
    print(f"  Label: '{label}'")
    print(f"  Content (first 50 chars): '{content.strip()[:50]}...'")

print("\n" + "=" * 60)
print("Testing edge cases...")

# Test with mixed newlines
mixed_output = """```Field1\nContent1```\n\n```Field2\\nContent2```"""
print(f"\nMixed output: {mixed_output}")

# Try new pattern
matches = re.findall(new_pattern, mixed_output, re.DOTALL | re.UNICODE)
print(f"Found {len(matches)} matches in mixed output")

print("\n" + "=" * 60)
print("Testing complete!")