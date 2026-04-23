#!/usr/bin/env python3
"""Final validation test with the updated parser."""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock logger
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
import __init__ as omniprompt_module
omniprompt_module.logger = logger

from __init__ import CodeBlockParser

print("=" * 80)
print("FINAL VALIDATION TEST")
print("=" * 80)

# Test 1: Simulate AI response with escaped newlines (literal backslash-n)
print("\nTest 1: AI response with escaped newlines (literal backslash-n)")
print("-" * 80)

ai_response_escaped = r"""```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""

print(f"AI response (first 200 chars): {repr(ai_response_escaped[:200])}")
print(f"Contains '\\n' (backslash-n): {'\\n' in ai_response_escaped}")
print(f"Contains actual newline: {'\n' in ai_response_escaped}")

# Test CodeBlockParser
parser = CodeBlockParser()
target_fields = ["Part(s) Of Speech", "English gloss", "Sample context", 
                 "English translation of sample context", "Russian gloss", "Extra"]

fields1 = parser.parse(ai_response_escaped, target_fields)
print(f"\nCodeBlockParser parsed {len(fields1)} fields:")
for field_name, content in fields1.items():
    print(f"  '{field_name}': '{content[:30]}...'")

# Test 2: Simulate parse_multi_field_output logic
print("\n" + "=" * 80)
print("Test 2: Simulating parse_multi_field_output logic")
print("-" * 80)

def simulate_parse_multi_field_output(explanation, target_fields):
    """Simulate the updated parse_multi_field_output logic"""
    import re
    field_map = {}
    # This is the updated pattern from parse_multi_field_output
    pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
    matches = re.findall(pattern, explanation, re.DOTALL)
    
    for field_name, field_content in matches:
        field_name = field_name.strip()
        # Convert any literal \n in content to actual newlines for HTML conversion
        field_content = field_content.replace('\\n', '\n')
        field_content = field_content.strip().replace('\n', '<br/>')  # Anki HTML
        if field_name and field_content:
            field_map[field_name] = field_content
    
    return field_map

fields2 = simulate_parse_multi_field_output(ai_response_escaped, target_fields)
print(f"parse_multi_field_output parsed {len(fields2)} fields:")
for field_name, content in fields2.items():
    print(f"  '{field_name}': '{content[:30]}...'")

# Test 3: With actual newlines (converted)
print("\n" + "=" * 80)
print("Test 3: With actual newlines (converted)")
print("-" * 80)

ai_response_actual = ai_response_escaped.replace('\\n', '\n')
print(f"Converted response (first 200 chars): {repr(ai_response_actual[:200])}")

fields3 = parser.parse(ai_response_actual, target_fields)
print(f"\nCodeBlockParser parsed {len(fields3)} fields after conversion:")
for field_name, content in fields3.items():
    print(f"  '{field_name}': '{content[:30]}...'")

fields4 = simulate_parse_multi_field_output(ai_response_actual, target_fields)
print(f"\nparse_multi_field_output parsed {len(fields4)} fields after conversion:")
for field_name, content in fields4.items():
    print(f"  '{field_name}': '{content[:30]}...'")

# Test 4: Mixed newlines (some escaped, some actual)
print("\n" + "=" * 80)
print("Test 4: Mixed newlines")
print("-" * 80)

mixed_response = """```Part(s) Of Speech\nNoun\n```\n\n```English gloss\\nA badge or insignia\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```"""

print(f"Mixed response: {repr(mixed_response)}")

fields5 = parser.parse(mixed_response)
print(f"\nCodeBlockParser parsed {len(fields5)} fields from mixed response:")
for field_name, content in fields5.items():
    print(f"  '{field_name}': '{content[:30]}...'")

# Test 5: Edge cases
print("\n" + "=" * 80)
print("Test 5: Edge cases")
print("-" * 80)

# Empty response
empty_response = ""
fields_empty = parser.parse(empty_response)
print(f"Empty response: parsed {len(fields_empty)} fields")

# No code blocks
no_blocks = "Some text without code blocks"
fields_no = parser.parse(no_blocks)
print(f"No code blocks: parsed {len(fields_no)} fields")

# Malformed code blocks
malformed = "```Field1\nContent1```\n```Field2\nContent2"
fields_malformed = parser.parse(malformed)
print(f"Malformed code blocks: parsed {len(fields_malformed)} fields")

# Test 6: Field name matching with parentheses
print("\n" + "=" * 80)
print("Test 6: Field name matching with parentheses")
print("-" * 80)

test_with_parentheses = "```Part(s) Of Speech\nnoun (masculine)\n```"
fields_parentheses = parser.parse(test_with_parentheses)
print(f"Test with parentheses: {repr(test_with_parentheses)}")
print(f"Parsed {len(fields_parentheses)} fields:")
for field_name, content in fields_parentheses.items():
    print(f"  '{field_name}': '{content}'")

# Test 7: HTML conversion
print("\n" + "=" * 80)
print("Test 7: HTML conversion")
print("-" * 80)

test_html = "```Test Field\nLine 1\nLine 2\nLine 3\n```"
fields_html = parser.parse(test_html)
print(f"Test HTML conversion: {repr(test_html)}")
print(f"Parsed content: {fields_html.get('Test Field', 'NOT FOUND')}")

# Test with escaped newlines in content
test_escaped_content = r"```Test Field\nLine 1\\nLine 2\\nLine 3\n```"
fields_escaped_content = parser.parse(test_escaped_content)
print(f"\nTest with escaped newlines in content: {repr(test_escaped_content)}")
print(f"Parsed content: {fields_escaped_content.get('Test Field', 'NOT FOUND')}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

all_tests_passed = True

# Check Test 1
if len(fields1) == 6:
    print("✓ Test 1: CodeBlockParser works with escaped newlines")
else:
    print(f"✗ Test 1: CodeBlockParser failed - parsed {len(fields1)} fields instead of 6")
    all_tests_passed = False

# Check Test 2  
if len(fields2) == 6:
    print("✓ Test 2: parse_multi_field_output works with escaped newlines")
else:
    print(f"✗ Test 2: parse_multi_field_output failed - parsed {len(fields2)} fields instead of 6")
    all_tests_passed = False

# Check Test 3
if len(fields3) == 6 and len(fields4) == 6:
    print("✓ Test 3: Both parsers work with actual newlines")
else:
    print(f"✗ Test 3: Failed with actual newlines - CodeBlockParser: {len(fields3)}, parse_multi_field_output: {len(fields4)}")
    all_tests_passed = False

# Check Test 5
if len(fields_empty) == 0:
    print("✓ Test 5: Empty response handled correctly")
else:
    print(f"✗ Test 5: Empty response failed - parsed {len(fields_empty)} fields")
    all_tests_passed = False

# Check Test 6
if "Part(s) Of Speech" in fields_parentheses:
    print("✓ Test 6: Parentheses in field names handled correctly")
else:
    print("✗ Test 6: Parentheses in field names not handled")
    all_tests_passed = False

# Check Test 7
test_field_content = fields_html.get('Test Field', '')
if '<br/>' in test_field_content:
    print("✓ Test 7: HTML conversion works (newlines converted to <br/>)")
else:
    print(f"✗ Test 7: HTML conversion failed - content: {test_field_content}")
    all_tests_passed = False

print("\n" + "=" * 80)
if all_tests_passed:
    print("✅ ALL TESTS PASSED! The parser should now handle escaped newlines correctly.")
else:
    print("❌ SOME TESTS FAILED. Check the output above.")
print("=" * 80)