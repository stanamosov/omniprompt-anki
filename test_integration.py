#!/usr/bin/env python3
"""Test the integration - simulate what happens when AI returns escaped newlines."""

import re

# Simulate the exact flow in parse_multi_field_output
def test_parse_multi_field_output_logic():
    print("Testing parse_multi_field_output logic...")
    print("=" * 80)
    
    # AI response with escaped newlines (literal backslash-n)
    ai_response = r"""```Part(s) Of Speech\nNoun\n```\n\n```English gloss\nA badge or insignia, often used to denote membership, authority, or identification.\n```\n\n```Sample context\nLe policier portait un badge visible sur sa poitrine.\n```\n\n```English translation of sample context\nThe police officer wore a badge visible on his chest.\n```\n\n```Russian gloss\nзначок или удостоверение, часто используемое для обозначения членства, полномочий или идентификации.\n```\n\n```Extra\nBadges can be found in various contexts, such as law enforcement, conferences, and employee identification.\n```"""
    
    print(f"AI response (first 200 chars): {repr(ai_response[:200])}")
    print(f"Contains '\\n' (backslash-n): {'\\n' in ai_response}")
    print(f"Contains actual newline: {'\n' in ai_response}")
    
    # Test 1: CodeBlockParser pattern (enhanced)
    print("\n" + "=" * 80)
    print("Test 1: CodeBlockParser pattern (enhanced)")
    print("-" * 80)
    
    # This is the pattern from CodeBlockParser.parse()
    parser_pattern = r"```\s*([^`\n]+?)\s*(?:\\n|\n)([\s\S]*?)\s*```"
    parser_matches = re.findall(parser_pattern, ai_response, re.DOTALL | re.UNICODE)
    print(f"CodeBlockParser pattern matches: {len(parser_matches)}")
    
    parser_fields = {}
    for label, content in parser_matches:
        label = label.strip()
        # Convert any literal \n in content to actual newlines for HTML conversion
        content = content.replace('\\n', '\n')
        content = content.strip().replace('\n', '<br/>')  # Anki HTML
        if label and content:
            parser_fields[label] = content
    
    print(f"Parsed {len(parser_fields)} fields:")
    for field_name, content in parser_fields.items():
        print(f"  '{field_name}': '{content[:30]}...'")
    
    # Test 2: Fallback pattern (simple)
    print("\n" + "=" * 80)
    print("Test 2: Fallback pattern (simple - from parse_multi_field_output)")
    print("-" * 80)
    
    # This is the fallback pattern from parse_multi_field_output
    fallback_pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
    fallback_matches = re.findall(fallback_pattern, ai_response, re.DOTALL)
    print(f"Fallback pattern matches: {len(fallback_matches)}")
    
    fallback_fields = {}
    for field_name, field_content in fallback_matches:
        field_name = field_name.strip()
        field_content = field_content.strip().replace('\n', '<br/>')  # Anki HTML
        if field_name and field_content:
            fallback_fields[field_name] = field_content
    
    print(f"Parsed {len(fallback_fields)} fields:")
    for field_name, content in fallback_fields.items():
        print(f"  '{field_name}': '{content[:30]}...'")
    
    # Test 3: What happens with actual newlines (converted)
    print("\n" + "=" * 80)
    print("Test 3: With actual newlines (converted)")
    print("-" * 80)
    
    converted_response = ai_response.replace('\\n', '\n')
    print(f"Converted response (first 200 chars): {repr(converted_response[:200])}")
    
    # Test with fallback pattern on converted response
    fallback_matches_converted = re.findall(fallback_pattern, converted_response, re.DOTALL)
    print(f"Fallback pattern matches on converted: {len(fallback_matches_converted)}")
    
    # Test with parser pattern on converted response
    parser_matches_converted = re.findall(parser_pattern, converted_response, re.DOTALL | re.UNICODE)
    print(f"Parser pattern matches on converted: {len(parser_matches_converted)}")
    
    print("\n" + "=" * 80)
    print("Analysis:")
    print("-" * 80)
    
    if len(parser_fields) == 6:
        print("✓ CodeBlockParser works with escaped newlines")
    else:
        print(f"✗ CodeBlockParser fails: found {len(parser_fields)} fields")
    
    if len(fallback_fields) == 6:
        print("✓ Fallback pattern works with escaped newlines")
    else:
        print(f"✗ Fallback pattern fails: found {len(fallback_fields)} fields")
    
    if len(fallback_matches_converted) == 6:
        print("✓ Fallback pattern works with actual newlines (after conversion)")
    else:
        print(f"✗ Fallback pattern fails with actual newlines: {len(fallback_matches_converted)} fields")
    
    # Check if parser is initialized in multi-field mode
    print("\n" + "=" * 80)
    print("Checking parser initialization logic:")
    print("-" * 80)
    
    # Simulate the logic from parse_multi_field_output
    multi_field_mode = True
    parser = None  # Simulate parser not initialized
    
    if not multi_field_mode:
        print("Not in multi-field mode")
    elif parser:
        print("Parser is initialized - would use CodeBlockParser")
    else:
        print("Parser is NOT initialized - would use fallback pattern")
        print("This would fail with escaped newlines!")
    
    print("\n" + "=" * 80)
    print("Recommendation:")
    print("-" * 80)
    print("The fallback pattern in parse_multi_field_output should be updated")
    print("to handle escaped newlines like the CodeBlockParser does.")
    print("Change pattern from:")
    print('  r"```\\s*([^`\\n]+?)\\s*\\n([\\s\\S]*?)\\s*```"')
    print("to:")
    print('  r"```\\s*([^`\\n]+?)\\s*(?:\\\\n|\\n)([\\s\\S]*?)\\s*```"')

# Also test the actual pattern from the working version
def test_working_version_pattern():
    print("\n" + "=" * 80)
    print("Testing working version pattern (from earlier test)")
    print("=" * 80)
    
    # The pattern from the working version test
    working_pattern = r"```\s*([\w\s]+)\s*\n([\s\S]*?)\s*```"
    print(f"Working pattern: {working_pattern}")
    
    # Test with actual newlines (not escaped)
    test_output = """```Part(s) Of Speech
noun (masculine)
```

```English gloss
badge; card; insignia
```

```Sample context
Il a oublié son badge à l'entrée du bâtiment.
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
    
    print(f"\nTest output (first 100 chars): {repr(test_output[:100])}")
    
    matches = re.findall(working_pattern, test_output, re.DOTALL | re.UNICODE)
    print(f"Working pattern matches: {len(matches)}")
    
    # Check if it captures parentheses
    for i, (label, content) in enumerate(matches):
        print(f"  Match {i+1}: Label='{label}'")
    
    print("\nNote: This pattern uses [\\w\\s]+ which doesn't match parentheses!")
    print("But the test shows it works... let's check:")
    
    test_string = "Part(s) Of Speech"
    match = re.fullmatch(r"[\w\s]+", test_string)
    print(f"\nDoes '[\\w\\s]+' match '{test_string}'? {bool(match)}")
    
    # Actually test with the exact pattern
    test_block = "```Part(s) Of Speech\nnoun\n```"
    match = re.search(working_pattern, test_block, re.DOTALL)
    print(f"\nDoes working pattern match '{test_block}'? {bool(match)}")
    if match:
        print(f"  Label: '{match.group(1)}'")

if __name__ == "__main__":
    test_parse_multi_field_output_logic()
    test_working_version_pattern()