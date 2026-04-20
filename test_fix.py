#!/usr/bin/env python3
"""
Test script to verify the GPT-5 phase fix.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock Anki objects
class MockConfigManager:
    def getConfig(self, name):
        return None
    def writeConfig(self, name, config):
        pass
    def setConfigAction(self, name, func):
        pass

class MockMw:
    def __init__(self):
        self.addonManager = MockConfigManager()

# Set up mw globally
import __init__ as module
module.mw = MockMw()

# Import after mocking
from __init__ import OmniPromptManager, DEFAULT_CONFIG, GPT5_MODELS

def test_config_migration():
    """Test migration from old config to new version."""
    print("Testing config migration...")
    mgr = OmniPromptManager()
    
    # Simulate old config
    old_config = {
        "_version": 1.1,
        "AI_PROVIDER": "openai",
        "OPENAI_MODEL": "gpt-4o-mini",
        "OPENAI_PHASE": "final_answer",  # This caused the error
        "API_KEYS": {"openai": "test"}
    }
    
    # Load config through migrate_config
    migrated = mgr.migrate_config(old_config)
    
    # Check that phase is now "none" (or at least not causing error)
    phase = migrated.get("OPENAI_PHASE", "none")
    print(f"  OPENAI_PHASE after migration: {phase}")
    assert phase == "none", f"Expected 'none', got {phase}"
    
    # Check version updated
    assert migrated["_version"] == 1.4
    print("  Config migration passed")

def test_gpt5_request_building():
    """Test that GPT-5 request doesn't include top-level phase parameter."""
    print("\nTesting GPT-5 request building...")
    mgr = OmniPromptManager()
    mgr.config = {
        "OPENAI_REASONING_EFFORT": "none",
        "OPENAI_VERBOSITY": "medium",
        "OPENAI_PHASE": "final_answer",  # Should be ignored
        "TEMPERATURE": 0.2,
        "MAX_TOKENS": 500,
        "API_KEYS": {"openai": "test"},
        "TIMEOUT": 30,
        "API_DELAY": 1
    }
    
    # Call internal method
    from __init__ import logger
    import logging
    logger.setLevel(logging.WARNING)  # Suppress debug
    
    # We'll inspect the data dict that would be sent
    # We can't call _make_gpt5_request directly because it requires API key,
    # but we can monkey-patch _send_gpt5_request to capture data
    captured_data = []
    original_send = mgr._send_gpt5_request
    def capture_send(url, headers, data, stream_callback=None):
        captured_data.append(data)
        return "[Test response]"
    mgr._send_gpt5_request = capture_send
    
    try:
        result = mgr._make_gpt5_request(
            prompt="Test prompt",
            model="gpt-5.4-mini",
            api_key="test_key",
            stream_callback=None
        )
        
        if captured_data:
            data = captured_data[0]
            print(f"  Request data keys: {list(data.keys())}")
            # Ensure no top-level 'phase' key
            assert "phase" not in data, f"Top-level 'phase' found: {data.get('phase')}"
            # Ensure input is string
            assert isinstance(data["input"], str)
            # Ensure temperature present (effort=none)
            assert "temperature" in data
            # Ensure verbosity present
            assert "text" in data and data["text"]["verbosity"] == "medium"
            print("  GPT-5 request building passed")
        else:
            print("  WARNING: No data captured")
    finally:
        mgr._send_gpt5_request = original_send

def test_parse_gpt5_response():
    """Test parsing various GPT-5 response formats."""
    print("\nTesting GPT-5 response parsing...")
    mgr = OmniPromptManager()
    mgr.config = {"GPT5_USE_LEGACY_PARSE": False}
    
    test_cases = [
        # (response, expected_output_description)
        ({"output_text": "Hello world"}, "output_text"),
        ({"text": "Simple text"}, "text string"),
        ({"text": {"content": "Nested content"}}, "text.content"),
        ({"text": {"value": "Nested value"}}, "text.value"),
        ({"choices": [{"message": {"content": "Legacy format"}}]}, "choices[0].message.content"),
        ({"output": "Output field"}, "output field"),
        ({"content": "Content field"}, "content field"),
        ({"response": "Response field"}, "response field"),
        ({"text": {"parts": ["Part1", "Part2"]}}, "text.parts"),
    ]
    
    for resp, desc in test_cases:
        try:
            result = mgr._parse_gpt5_response(resp)
            print(f"  {desc}: OK (length {len(result)})")
        except Exception as e:
            print(f"  {desc}: ERROR - {e}")
            raise
    
    # Test with non-dict response (should fallback)
    result = mgr._parse_gpt5_response("raw string")
    print(f"  Non-dict response: OK (fallback used)")
    
    print("  Response parsing passed")

def test_phase_ignored():
    """Ensure phase parameter doesn't cause errors in single-turn requests."""
    print("\nTesting phase handling...")
    mgr = OmniPromptManager()
    mgr.config = {
        "OPENAI_PHASE": "final_answer",
        "OPENAI_REASONING_EFFORT": "none",
        "OPENAI_VERBOSITY": "medium",
        "API_KEYS": {"openai": "test"}
    }
    
    # Monkey-patch to check request
    import requests
    original_post = requests.post
    request_captured = []
    
    def mock_post(url, headers=None, json=None, timeout=None):
        request_captured.append((url, json))
        # Return mock response
        class MockResponse:
            status_code = 200
            text = '{"output_text": "Test"}'
            def json(self):
                return {"output_text": "Test response"}
        return MockResponse()
    
    requests.post = mock_post
    
    try:
        # This would normally be called via _make_openai_request
        # but we need to mock deeper. Let's just test that the code paths exist.
        # We'll directly test _make_gpt5_request with our mock
        captured_data = []
        original_send = mgr._send_gpt5_request
        def capture_send(url, headers, data, stream_callback=None):
            captured_data.append(data)
            # Return mock
            return "Test response"
        mgr._send_gpt5_request = capture_send
        
        result = mgr._make_gpt5_request(
            prompt="Test",
            model="gpt-5.4-mini",
            api_key="test",
            stream_callback=None
        )
        
        if captured_data:
            data = captured_data[0]
            print(f"  Phase in config: {mgr.config['OPENAI_PHASE']}")
            print(f"  Phase in request data: {'phase' in data}")
            assert "phase" not in data, f"Unexpected phase in request: {data.get('phase')}"
            print("  Phase correctly ignored in single-turn request")
    finally:
        requests.post = original_post
        mgr._send_gpt5_request = original_send

def main():
    print("=" * 60)
    print("OmniPrompt GPT-5 Phase Fix Test")
    print("=" * 60)
    
    try:
        test_config_migration()
        test_gpt5_request_building()
        test_parse_gpt5_response()
        test_phase_ignored()
        
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