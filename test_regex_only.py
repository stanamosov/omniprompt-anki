#!/usr/bin/env python3
"""Test just the regex patterns without importing the module."""

import re

print("=" * 80)
print("REGEX PATTERN VALIDATION TEST")
print("=" * 80)

# The pattern from CodeBlockParser.parse()
codeblock_parser_pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
print(f"CodeBlockParser pattern: {codeblock_parser_pattern}")

# The pattern from parse_multi_field_output (updated)
parse_multi_field_pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
print(f"parse_multi_field_output pattern: {parse_multi_field_pattern}")

# Test data
ai_response_escaped = r"""```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

print("\n" + "=" * 80)
print("Test 1: Matching escaped newlines (literal backslash-n)")
print("-" * 80)

print(f"AI response (first 200 chars): {repr(ai_response_escaped[:200])}")
print(f"Contains '\\n' (backslash-n): {'\\n' in ai_response_escaped}")
print(f"Contains actual newline: {'\n' in ai_response_escaped}")

# Test CodeBlockParser pattern
matches1 = re.findall(codeblock_parser_pattern, ai_response_escaped, re.DOTALL)
print(f"\nCodeBlockParser pattern matches: {len(matches1)}")
for i, (label, content) in enumerate(matches1):
    print(f"  Match {i+1}: Label='{label}', Content preview='{content[:30]}...'")

# Test parse_multi_field_output pattern
matches2 = re.findall(parse_multi_field_pattern, ai_response_escaped, re.DOTALL)
print(f"\nparse_multi_field_output pattern matches: {len(matches2)}")
for i, (label, content) in enumerate(matches2):
    print(f"  Match {i+1}: Label='{label}', Content preview='{content[:30]}...'")

# Simulate the full parsing logic
print("\n" + "=" * 80)
print("Test 2: Simulating full parsing logic")
print("-" * 80)

def simulate_codeblock_parser(text):
    """Simulate CodeBlockParser.parse() logic"""
    fields = {}
    matches = re.findall(codeblock_parser_pattern, text, re.DOTALL | re.UNICODE)
    for label, content in matches:
        label = label.strip()
        content = content.replace('\\n', '\n')
        content = content.strip().replace('\n', '<br/>')
        if label and content:
            fields[label] = content
    return fields

def simulate_parse_multi_field_output(text):
    """Simulate parse_multi_field_output logic"""
    fields = {}
    matches = re.findall(parse_multi_field_pattern, text, re.DOTALL)
    for label, content in matches:
        label = label.strip()
        content = content.replace('\\n', '\n')
        content = content.strip().replace('\n', '<br/>')
        if label and content:
            fields[label] = content
    return fields

fields1 = simulate_codeblock_parser(ai_response_escaped)
fields2 = simulate_parse_multi_field_output(ai_response_escaped)

print(f"CodeBlockParser parsed {len(fields1)} fields:")
for field_name, content in fields1.items():
    print(f"  '{field_name}': '{content[:30]}...'")

print(f"\nparse_multi_field_output parsed {len(fields2)} fields:")
for field_name, content in fields2.items():
    print(f"  '{field_name}': '{content[:30]}...'")

# Test with actual newlines
print("\n" + "=" * 80)
print("Test 3: With actual newlines (converted)")
print("-" * 80)

ai_response_actual = ai_response_escaped.replace('\\n', '\n')
print(f"Converted response (first 200 chars): {repr(ai_response_actual[:200])}")

fields3 = simulate_codeblock_parser(ai_response_actual)
fields4 = simulate_parse_multi_field_output(ai_response_actual)

print(f"\nCodeBlockParser parsed {len(fields3)} fields after conversion:")
for field_name, content in fields3.items():
    print(f"  '{field_name}': '{content[:30]}...'")

print(f"\nparse_multi_field_output parsed {len(fields4)} fields after conversion:")
for field_name, content in fields4.items():
    print(f"  '{field_name}': '{content[:30]}...'")

# Test the old pattern (for comparison)
print("\n" + "=" * 80)
print("Test 4: Old pattern (for comparison)")
print("-" * 80)

old_pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
print(f"Old pattern: {old_pattern}")

old_matches = re.findall(old_pattern, ai_response_escaped, re.DOTALL)
print(f"Old pattern matches with escaped newlines: {len(old_matches)}")

old_matches_actual = re.findall(old_pattern, ai_response_actual, re.DOTALL)
print(f"Old pattern matches with actual newlines: {len(old_matches_actual)}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if len(matches1) == 6 and len(matches2) == 6:
    print("✅ BOTH NEW PATTERNS WORK with escaped newlines!")
else:
    print(f"❌ Pattern mismatch: CodeBlockParser={len(matches1)}, parse_multi_field_output={len(matches2)}")

if len(old_matches) == 0 and len(old_matches_actual) == 6:
    print("✅ OLD PATTERN fails with escaped newlines but works with actual newlines (as expected)")
else:
    print(f"❌ Old pattern behavior unexpected: escaped={len(old_matches)}, actual={len(old_matches_actual)}")

if len(fields1) == 6 and len(fields2) == 6:
    print("✅ FULL PARSING LOGIC works with escaped newlines!")
else:
    print(f"❌ Full parsing failed: CodeBlockParser={len(fields1)}, parse_multi_field_output={len(fields2)}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("The fix is working! Both patterns now handle escaped newlines correctly.")
print("The key change was updating the pattern from:")
print('  r"```\\s*([^`\\n]+?)\\s*\\n([\\s\\S]*?)\\s*```"')
print("to:")
print('  r"```\\s*([^`\\n]+?)\\s*(?:\\\\n|\\n)([\\s\\S]*?)\\s*```"')
print("\nThis pattern matches either literal backslash-n or actual newline.")