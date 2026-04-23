#!/usr/bin/env python3
"""Test the actual CodeBlockParser class with user's raw output."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock logger since we're testing without Anki
class MockLogger:
    def info(self, msg):
        print(f"[INFO] {msg}")
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    def debug(self, msg):
        print(f"[DEBUG] {msg}")

# Create mock logger
logger = MockLogger()

# Import the actual CodeBlockParser class
# We need to mock the logger import first
import __init__ as omniprompt_module

# Replace the logger in the module
omniprompt_module.logger = logger

# Now we can import the class
from __init__ import CodeBlockParser

# User's exact raw output with escaped newlines
raw_output = """```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

print("Testing actual CodeBlockParser.parse() method...")
print("=" * 80)
print(f"Raw output length: {len(raw_output)}")
print(f"First 200 chars: {repr(raw_output[:200])}")

# Create parser
parser = CodeBlockParser()

# Test 1: Parse with default (no target fields)
print("\nTest 1: Parsing with no target fields...")
fields1 = parser.parse(raw_output)
print(f"Parsed {len(fields1)} fields:")
for field_name, content in fields1.items():
    print(f"  '{field_name}': '{content[:50]}...'")

# Test 2: Parse with target fields
print("\nTest 2: Parsing with target fields...")
target_fields = ["Part(s) Of Speech", "English gloss", "Sample context", 
                 "English translation of sample context", "Russian gloss", "Extra"]
fields2 = parser.parse(raw_output, target_fields)
print(f"Parsed {len(fields2)} fields:")
for field_name, content in fields2.items():
    print(f"  '{field_name}': '{content[:50]}...'")

# Test 3: Test suggest_mappings
print("\nTest 3: Testing suggest_mappings...")
ai_fields = list(fields1.keys())
note_fields = ["Part(s) Of Speech", "English gloss", "Sample context", 
               "English translation of sample context", "Russian gloss", "Extra",
               "Some Other Field", "Another Field"]
mappings = parser.suggest_mappings(ai_fields, note_fields)
print("Field mappings:")
for ai_field, note_field in mappings.items():
    print(f"  '{ai_field}' -> '{note_field}'")

# Test 4: Test with actual newlines (convert escaped to actual)
print("\nTest 4: Testing with actual newlines (converted)...")
processed_output = raw_output.replace('\\n', '\n')
print(f"Processed output first 200 chars: {repr(processed_output[:200])}")
fields3 = parser.parse(processed_output)
print(f"Parsed {len(fields3)} fields:")
for field_name, content in fields3.items():
    print(f"  '{field_name}': '{content[:50]}...'")

# Test 5: Check HTML conversion
print("\nTest 5: Checking HTML conversion...")
for field_name, content in fields1.items():
    if '\\n' in content:
        print(f"  '{field_name}' contains escaped newline: {repr(content[:30])}")
    elif '<br/>' in content:
        print(f"  '{field_name}' contains <br/>: {repr(content[:30])}")
    else:
        print(f"  '{field_name}' content: {repr(content[:30])}")

print("\n" + "=" * 80)
print("Testing complete!")