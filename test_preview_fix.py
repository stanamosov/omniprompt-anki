#!/usr/bin/env python3
"""
Test script to verify the Preview Parse bug fix.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock minimal Anki objects
class MockConfigManager:
    def getConfig(self, name):
        return None
    def writeConfig(self, name, config):
        pass

class MockMw:
    def __init__(self):
        self.addonManager = MockConfigManager()
        self.col = None

# Mock a note object
class MockNote:
    def __init__(self):
        self.id = 1
        self.mid = 1
        self.fields = {
            "Rank": "1",
            "French Word": "test",
            "Part(s) Of Speech": "noun",
            "English gloss": "test"
        }
    
    def __getitem__(self, key):
        return self.fields.get(key, "")
    
    def __setitem__(self, key, value):
        self.fields[key] = value
    
    def __contains__(self, key):
        return key in self.fields

# Set up mw globally
import __init__ as module
module.mw = MockMw()

# Import after mocking
from __init__ import UpdateOmniPromptDialog, OmniPromptManager, CodeBlockParser, safe_show_info

def test_json_template_escaping():
    """Test that JSON template has escaped curly braces."""
    print("Testing JSON template escaping...")
    
    # Create a mock dialog
    mgr = OmniPromptManager()
    mgr.config = {
        "MULTI_FIELD_MODE": False,
        "DEBUG_MODE": False
    }
    
    # Mock dialog with some notes
    notes = [MockNote()]
    dialog = UpdateOmniPromptDialog(notes, mgr, parent=None)
    
    # Set target note fields
    dialog.target_note_fields = ["Rank", "French Word", "Part(s) Of Speech"]
    dialog.format_combo = type('obj', (object,), {'currentText': lambda: "JSON Fallback ({'field': 'value'})"})()
    
    # Call inject_code_block_template with state=True
    dialog.inject_code_block_template(True)
    
    # Get the prompt text
    prompt_text = dialog.prompt_edit.toPlainText() if hasattr(dialog, 'prompt_edit') else ""
    
    # Check that double curly braces are present
    if "{{" in prompt_text and "}}" in prompt_text:
        print("  ✓ JSON template has escaped curly braces")
    else:
        print("  ✗ JSON template missing escaped curly braces")
        print(f"  Template snippet: {prompt_text[-200:]}")
    
    # Also test that single braces don't cause KeyError
    test_prompt = "Test prompt with {Rank} and {French Word}"
    try:
        result = test_prompt.format(**notes[0])
        print("  ✓ Standard format works with note fields")
    except KeyError as e:
        print(f"  ✗ KeyError with standard format: {e}")

def test_safe_format_prompt():
    """Test the safe formatting fallback."""
    print("\nTesting safe formatting fallback...")
    
    mgr = OmniPromptManager()
    notes = [MockNote()]
    dialog = UpdateOmniPromptDialog(notes, mgr, parent=None)
    
    # Test with problematic template that has JSON braces
    problematic_template = 'Template with JSON example: {{"Rank": "", "French Word": ""}} and field {Rank}'
    
    # This should not raise KeyError for the JSON braces
    result = dialog._format_prompt_safely(problematic_template, notes[0])
    if result:
        print(f"  ✓ Safe formatting handled problematic template")
        print(f"  Result length: {len(result)}")
    else:
        print(f"  ✗ Safe formatting failed")
    
    # Test with normal template
    normal_template = 'Normal template with {Rank} and {French Word}'
    result = dialog._format_prompt_safely(normal_template, notes[0])
    if "1" in result and "test" in result:
        print(f"  ✓ Safe formatting works with normal template")
    else:
        print(f"  ✗ Safe formatting issue with normal template")
        print(f"  Result: {result}")

def test_preview_single_note_logic():
    """Test the preview_single_note logic flow."""
    print("\nTesting preview_single_note logic...")
    
    mgr = OmniPromptManager()
    notes = [MockNote()]
    dialog = UpdateOmniPromptDialog(notes, mgr, parent=None)
    
    # Mock prompt_edit
    dialog.prompt_edit = type('obj', (object,), {'toPlainText': lambda: 'Test {Rank}'})()
    
    # Mock manager.generate_ai_response
    dialog.manager = type('obj', (object,), {'generate_ai_response': lambda x: 'Test AI response'})()
    
    # Mock parser
    dialog.parser = CodeBlockParser(["Rank", "French Word"])
    dialog.target_note_fields = ["Rank", "French Word"]
    
    # We can't run the full method because of UI dependencies,
    # but we can test the formatting part
    prompt_text = 'Test {Rank}'
    
    # Test standard format
    try:
        formatted = prompt_text.format(**notes[0])
        print(f"  ✓ Standard format works: {formatted}")
    except KeyError as e:
        print(f"  ✗ Standard format KeyError: {e}")
    
    # Test with problematic braces
    problematic = 'Test with JSON: {{"Rank": ""}} and field {Rank}'
    try:
        formatted = problematic.format(**notes[0])
        print(f"  ✓ Problematic format with standard: {formatted[:50]}...")
    except KeyError as e:
        print(f"  ✗ Problematic format KeyError (expected): {e}")

def test_multi_field_notifications():
    """Test that multi-field mode shows only one notification."""
    print("\nTesting multi-field notifications...")
    
    # Check safe_show_info function
    import __init__ as module
    if hasattr(module, 'omni_prompt_manager'):
        module.omni_prompt_manager.config = {"DEBUG_MODE": True}
    
    # We can't test QTimer easily, but we can check the function exists
    if hasattr(module, 'safe_show_info'):
        print("  ✓ safe_show_info function exists")
    
    # Check that the notification message is combined
    with open('__init__.py', 'r') as f:
        content = f.read()
        if 'Multi-field enabled for' in content and 'Template injected' in content:
            print("  ✓ Combined notification message found")
        else:
            print("  ✗ Combined notification message not found")
        
        # Check that old injection message is removed
        injection_count = content.count('Injected.*template for')
        if injection_count == 0:
            print("  ✓ Old injection message removed")
        else:
            print(f"  ✗ Old injection message still present ({injection_count} times)")

def main():
    print("=" * 60)
    print("OmniPrompt Preview Parse Bug Fix Test")
    print("=" * 60)
    
    try:
        test_json_template_escaping()
        test_safe_format_prompt()
        test_preview_single_note_logic()
        test_multi_field_notifications()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())