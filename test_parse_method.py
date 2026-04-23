#!/usr/bin/env python3
"""Test the exact parse method logic."""

import re

def parse_method(text: str, target_note_fields: list = None):
    """Exact copy of CodeBlockParser.parse() logic"""
    import re
    
    text = text.strip()
    if not text:
        return {}
    
    # Use provided target fields or instance fields
    target_fields = target_note_fields or []
    
    # Improved regex for ```FieldName\nContent``` with Unicode support
    # [^`\n]+? matches any character except backtick or newline (supports Unicode, parentheses, etc.)
    block_pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
    blocks = re.findall(block_pattern, text, re.DOTALL | re.UNICODE)
    
    fields = {}
    for label, content in blocks:
        label = label.strip()
        content = content.strip().replace('\n', '<br/>')  # Anki HTML
        if label and content:
            fields[label] = content
    
    # Log parsing results for debugging
    if fields:
        print(f"CodeBlockParser parsed {len(fields)} fields: {list(fields.keys())}")
    else:
        print(f"CodeBlockParser found no fields in text (length: {len(text)})")
    
    return fields

# User's exact raw output with escaped newlines
raw_output = """```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

print("Testing parse method with exact raw output...")
print("=" * 60)
print(f"Raw output length: {len(raw_output)}")
print(f"First 200 chars: {raw_output[:200]}")

fields = parse_method(raw_output)

print(f"\nParsed {len(fields)} fields:")
for field_name, content in fields.items():
    print(f"  '{field_name}': '{content[:50]}...'")

print("\n" + "=" * 60)
print("Debugging regex matches...")

# Let's examine what the regex actually captures
block_pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
blocks = re.findall(block_pattern, raw_output, re.DOTALL | re.UNICODE)

print(f"\nRegex found {len(blocks)} blocks:")
for i, (label, content) in enumerate(blocks):
    print(f"\nBlock {i+1}:")
    print(f"  Raw label: {repr(label)}")
    print(f"  Raw content: {repr(content)}")
    print(f"  Label stripped: {repr(label.strip())}")
    print(f"  Content stripped: {repr(content.strip())}")
    print(f"  Content after replace('\\n', '<br/>'): {repr(content.strip().replace(chr(10), '<br/>'))}")
    print(f"  Has actual newline in content: {chr(10) in content}")
    print(f"  Has backslash-n in content: {'\\n' in content}")

print("\n" + "=" * 60)
print("Testing with preprocessing to convert \\n to actual newline...")

# Convert literal \n to actual newline
processed = raw_output.replace('\\n', '\n')
print(f"After preprocessing, first 200 chars: {processed[:200]}")

fields2 = parse_method(processed)
print(f"Parsed {len(fields2)} fields after preprocessing")

print("\n" + "=" * 60)
print("Testing complete!")