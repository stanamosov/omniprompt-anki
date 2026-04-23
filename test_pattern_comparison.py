#!/usr/bin/env python3
"""Compare different regex patterns for parsing code blocks."""

import re

# User's exact raw output with escaped newlines
raw_output_escaped = """```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

# Same output with actual newlines (for comparison)
raw_output_actual = raw_output_escaped.replace('\\n', '\n')

print("Comparing regex patterns...")
print("=" * 80)

# Pattern 1: Simple pattern from working version [\w\s]+
pattern1 = r"```\s*([\w\s]+)\s*\n([\s\S]*?)\s*```"
print(f"\nPattern 1 (simple): {pattern1}")
print("-" * 40)

print("Testing with escaped newlines:")
matches1_escaped = re.findall(pattern1, raw_output_escaped, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches1_escaped)} matches")

print("\nTesting with actual newlines:")
matches1_actual = re.findall(pattern1, raw_output_actual, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches1_actual)} matches")

# Pattern 2: Current pattern [^`\n]+?
pattern2 = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
print(f"\nPattern 2 (current): {pattern2}")
print("-" * 40)

print("Testing with escaped newlines:")
matches2_escaped = re.findall(pattern2, raw_output_escaped, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches2_escaped)} matches")

print("\nTesting with actual newlines:")
matches2_actual = re.findall(pattern2, raw_output_actual, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches2_actual)} matches")

# Pattern 3: Enhanced pattern with escaped newline support
pattern3 = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
print(f"\nPattern 3 (enhanced): {pattern3}")
print("-" * 40)

print("Testing with escaped newlines:")
matches3_escaped = re.findall(pattern3, raw_output_escaped, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches3_escaped)} matches")

print("\nTesting with actual newlines:")
matches3_actual = re.findall(pattern3, raw_output_actual, re.DOTALL | re.UNICODE)
print(f"  Found {len(matches3_actual)} matches")

# Debug: Show what each pattern captures
print("\n" + "=" * 80)
print("Detailed match analysis (using actual newlines):")
print("-" * 80)

for pattern_name, pattern, matches in [
    ("Pattern 1", pattern1, matches1_actual),
    ("Pattern 2", pattern2, matches2_actual),
    ("Pattern 3", pattern3, matches3_actual),
]:
    print(f"\n{pattern_name}:")
    for i, (label, content) in enumerate(matches):
        print(f"  Match {i+1}: Label='{label}' (len={len(label)}), Content preview='{content.strip()[:30]}...'")

# Test character class behavior
print("\n" + "=" * 80)
print("Testing character class [\\w\\s]+ with parentheses:")
print("-" * 80)

test_string = "Part(s) Of Speech"
print(f"Test string: '{test_string}'")
print(f"Does [\\w\\s]+ match the whole string?")
match = re.fullmatch(r"[\w\s]+", test_string)
if match:
    print(f"  YES: '{match.group()}'")
else:
    print(f"  NO")
    
# Check which characters match
print("\nCharacter-by-character analysis:")
for i, char in enumerate(test_string):
    if re.match(r"[\w\s]", char):
        print(f"  Position {i}: '{char}' (U+{ord(char):04X}) matches [\\w\\s]")
    else:
        print(f"  Position {i}: '{char}' (U+{ord(char):04X}) does NOT match [\\w\\s]")

print("\n" + "=" * 80)
print("Testing [^`\\n]+? with parentheses:")
print("-" * 80)

match = re.fullmatch(r"[^`\n]+?", test_string)
if match:
    print(f"  YES: '{match.group()}'")
else:
    print(f"  NO")

print("\n" + "=" * 80)
print("Testing the actual regex in context:")
print("-" * 80)

test_block = "```Part(s) Of Speech\nNoun\n```"
print(f"Test block: {repr(test_block)}")

for pattern_name, pattern in [
    ("Pattern 1", pattern1),
    ("Pattern 2", pattern2),
    ("Pattern 3", pattern3),
]:
    match = re.search(pattern, test_block, re.DOTALL)
    if match:
        print(f"\n{pattern_name} matches:")
        print(f"  Label: '{match.group(1)}'")
        print(f"  Content: '{match.group(2)}'")
    else:
        print(f"\n{pattern_name} does NOT match")

print("\n" + "=" * 80)
print("Conclusion:")
print("-" * 80)

if len(matches1_actual) == 6 and len(matches2_actual) == 6 and len(matches3_actual) == 6:
    print("✓ All patterns work with actual newlines")
else:
    print(f"✗ Pattern differences: P1={len(matches1_actual)}, P2={len(matches2_actual)}, P3={len(matches3_actual)}")

if len(matches1_escaped) == 6:
    print("✓ Pattern 1 works with escaped newlines")
else:
    print(f"✗ Pattern 1 fails with escaped newlines: {len(matches1_escaped)} matches")

if len(matches2_escaped) == 6:
    print("✓ Pattern 2 works with escaped newlines")
else:
    print(f"✗ Pattern 2 fails with escaped newlines: {len(matches2_escaped)} matches")

if len(matches3_escaped) == 6:
    print("✓ Pattern 3 works with escaped newlines")
else:
    print(f"✗ Pattern 3 fails with escaped newlines: {len(matches3_escaped)} matches")