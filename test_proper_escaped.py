#!/usr/bin/env python3
"""Test with proper escaped newlines (literal backslash-n)."""

import re

# User's exact raw output with LITERAL backslash-n (not actual newlines)
# In Python, we need to escape the backslash: \\n becomes \\\\n in string literal
raw_output_proper = r"""```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

print("Testing with PROPER escaped newlines (literal backslash-n)...")
print("=" * 80)
print(f"Raw output (first 100 chars): {repr(raw_output_proper[:100])}")
print(f"Contains '\\n' (backslash-n): {'\\n' in raw_output_proper}")
print(f"Contains actual newline (ASCII 10): {'\n' in raw_output_proper}")

# Pattern 1: Simple pattern [\w\s]+ (from working version)
pattern1 = r"```\s*([\w\s]+)\s*\n([\s\S]*?)\s*```"
print(f"\nPattern 1 (simple): {pattern1}")
matches1 = re.findall(pattern1, raw_output_proper, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches1)} matches")

# Pattern 2: Current pattern [^`\n]+?
pattern2 = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
print(f"\nPattern 2 (current): {pattern2}")
matches2 = re.findall(pattern2, raw_output_proper, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches2)} matches")

# Pattern 3: Enhanced pattern with escaped newline support
pattern3 = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
print(f"\nPattern 3 (enhanced): {pattern3}")
matches3 = re.findall(pattern3, raw_output_proper, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches3)} matches")

# Pattern 4: Match literal backslash-n only (not actual newline)
pattern4 = r"```\s*([^`\n]+?)\s*\\n([\s\S]*?)\s*```"
print(f"\nPattern 4 (backslash-n only): {pattern4}")
matches4 = re.findall(pattern4, raw_output_proper, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches4)} matches")

# Show what's captured
print("\n" + "=" * 80)
print("Detailed analysis of Pattern 3 matches:")
print("-" * 80)
for i, (label, content) in enumerate(matches3):
    print(f"\nMatch {i+1}:")
    print(f"  Label: '{label}'")
    print(f"  Content raw: {repr(content[:50])}")
    print(f"  Contains '\\n' in content: {'\\n' in content}")
    print(f"  Contains actual newline in content: {'\n' in content}")

# Test the actual parse logic
print("\n" + "=" * 80)
print("Testing actual parse logic (simplified):")
print("-" * 80)

def parse_logic(text):
    """Simplified version of CodeBlockParser.parse()"""
    import re
    text = text.strip()
    if not text:
        return {}
    
    # Current pattern from CodeBlockParser
    block_pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
    blocks = re.findall(block_pattern, text, re.DOTALL | re.UNICODE)
    
    fields = {}
    for label, content in blocks:
        label = label.strip()
        # Convert any literal \n in content to actual newlines for HTML conversion
        content = content.replace('\\n', '\n')
        content = content.strip().replace('\n', '<br/>')  # Anki HTML
        if label and content:
            fields[label] = content
    
    return fields

fields = parse_logic(raw_output_proper)
print(f"Parsed {len(fields)} fields:")
for field_name, content in fields.items():
    print(f"  '{field_name}': '{content[:50]}...'")

# Test with actual newlines (for comparison)
print("\n" + "=" * 80)
print("Testing with actual newlines (converted):")
print("-" * 80)
raw_output_actual = raw_output_proper.replace('\\n', '\n')
print(f"Converted string (first 100 chars): {repr(raw_output_actual[:100])}")
fields2 = parse_logic(raw_output_actual)
print(f"Parsed {len(fields2)} fields after conversion:")
for field_name, content in fields2.items():
    print(f"  '{field_name}': '{content[:50]}...'")

print("\n" + "=" * 80)
print("Conclusion:")
print("-" * 80)
if len(fields) == 6:
    print("✓ Parser works with literal backslash-n sequences")
else:
    print(f"✗ Parser fails: found {len(fields)} fields instead of 6")
    print(f"  Pattern 1 matches: {len(matches1)}")
    print(f"  Pattern 2 matches: {len(matches2)}")
    print(f"  Pattern 3 matches: {len(matches3)}")
    print(f"  Pattern 4 matches: {len(matches4)}")