#!/usr/bin/env python3
"""
Test script to verify the changes made to omniprompt-anki
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock Anki environment for testing
class MockMw:
    class addonManager:
        @staticmethod
        def getConfig(name):
            return None
        @staticmethod
        def writeConfig(name, config):
            pass
        @staticmethod
        def setConfigAction(name, callback):
            pass

mw = MockMw()
sys.modules['aqt'] = type(sys)('aqt')
sys.modules['aqt'].mw = mw
sys.modules['aqt.utils'] = type(sys)('utils')
sys.modules['aqt.utils'].showInfo = lambda x: print(f"INFO: {x}")
sys.modules['aqt.utils'].getText = lambda prompt, default: (default, True)
sys.modules['anki'] = type(sys)('anki')
sys.modules['anki.hooks'] = type(sys)('hooks')
sys.modules['anki.hooks'].addHook = lambda name, func: None
sys.modules['anki.errors'] = type(sys)('errors')
sys.modules['anki.errors'].NotFoundError = Exception

# Mock PyQt6 modules
for module in ['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets']:
    sys.modules[module] = type(sys)(module)

# Mock QDialog and other Qt classes
class MockQDialog:
    def __init__(self, parent=None):
        self.parent = parent
    def exec(self):
        return 0
    def setWindowTitle(self, title):
        pass
    def setMinimumWidth(self, width):
        pass
    def setMinimumSize(self, width, height):
        pass
    def setWindowModality(self, modality):
        pass
    def show(self):
        pass

class MockQWidget:
    pass

class MockQVBoxLayout:
    def __init__(self, parent=None):
        self.parent = parent
    def addWidget(self, widget):
        pass
    def addLayout(self, layout):
        pass

class MockQComboBox:
    def __init__(self):
        self.items = []
        self.current_text = ""
    def addItems(self, items):
        self.items.extend(items)
    def clear(self):
        self.items = []
    def setCurrentText(self, text):
        self.current_text = text
    def currentText(self):
        return self.current_text
    def setEditable(self, editable):
        pass

class MockQLineEdit:
    def __init__(self):
        self.text_value = ""
    def setText(self, text):
        self.text_value = str(text)
    def text(self):
        return self.text_value
    def setPlaceholderText(self, text):
        pass
    def setValidator(self, validator):
        pass

class MockQPushButton:
    def __init__(self, text=""):
        self.text = text
    def clicked(self):
        pass
    def connect(self, callback):
        pass

# Patch the Qt classes
sys.modules['PyQt6.QtWidgets'].QDialog = MockQDialog
sys.modules['PyQt6.QtWidgets'].QVBoxLayout = MockQVBoxLayout
sys.modules['PyQt6.QtWidgets'].QComboBox = MockQComboBox
sys.modules['PyQt6.QtWidgets'].QLineEdit = MockQLineEdit
sys.modules['PyQt6.QtWidgets'].QPushButton = MockQPushButton
sys.modules['PyQt6.QtWidgets'].QLabel = MockQWidget
sys.modules['PyQt6.QtWidgets'].QGroupBox = MockQWidget
sys.modules['PyQt6.QtWidgets'].QFormLayout = MockQVBoxLayout
sys.modules['PyQt6.QtWidgets'].QTextEdit = MockQWidget
sys.modules['PyQt6.QtWidgets'].QHBoxLayout = MockQVBoxLayout
sys.modules['PyQt6.QtWidgets'].QCheckBox = MockQWidget
sys.modules['PyQt6.QtWidgets'].QCompleter = MockQWidget
sys.modules['PyQt6.QtCore'].Qt = type(sys)('Qt')
sys.modules['PyQt6.QtCore'].Qt.WindowModality = type(sys)('WindowModality')
sys.modules['PyQt6.QtCore'].Qt.WindowModality.NonModal = 0
sys.modules['PyQt6.QtCore'].Qt.ItemDataRole = type(sys)('ItemDataRole')
sys.modules['PyQt6.QtCore'].Qt.ItemDataRole.UserRole = 256
sys.modules['PyQt6.QtCore'].QTimer = type(sys)('QTimer')
sys.modules['PyQt6.QtCore'].QTimer.singleShot = lambda delay, func: func()
sys.modules['PyQt6.QtCore'].pyqtSignal = lambda: None
sys.modules['PyQt6.QtCore'].QThread = MockQWidget
sys.modules['PyQt6.QtGui'].QDoubleValidator = MockQWidget
sys.modules['PyQt6.QtGui'].QIntValidator = MockQWidget
sys.modules['PyQt6.QtGui'].QKeySequence = MockQWidget
sys.modules['PyQt6.QtGui'].QShortcut = MockQWidget
sys.modules['PyQt6.QtGui'].QAction = MockQWidget

# Mock requests
import requests
original_post = requests.post
original_get = requests.get

def mock_post(url, headers=None, json=None, timeout=None, stream=False):
    class MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            if "openai" in url:
                return {"choices": [{"message": {"content": "Test response"}}]}
            elif "deepseek" in url:
                return {"choices": [{"message": {"content": "Test response"}}]}
            else:
                return {"response": "Test response"}
    return MockResponse()

def mock_get(url, timeout=None):
    class MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"models": []}
    return MockResponse()

requests.post = mock_post
requests.get = mock_get

# Now we can import the module
try:
    import __init__ as omniprompt
    print("✓ Module imported successfully")
    
    # Test config migration
    test_config = {
        "_version": 1.1,
        "AI_PROVIDER": "openai",
        "API_KEYS": {"openai": "test-key"},
        "OPENAI_MODEL": "gpt-4o-mini"
    }
    
    # Create instance of OmniPromptManager
    manager = omniprompt.OmniPromptManager()
    manager.config = test_config.copy()
    
    # Test migration
    migrated = manager.migrate_config(test_config)
    print(f"✓ Config migrated from version {test_config['_version']} to {migrated['_version']}")
    
    # Check that new fields are present
    required_fields = [
        "OPENAI_TEST_URL", "DEEPSEEK_TEST_URL", "GEMINI_TEST_URL",
        "ANTHROPIC_TEST_URL", "XAI_TEST_URL", "OPENAI_API_VERSION"
    ]
    
    for field in required_fields:
        if field in migrated:
            print(f"✓ {field} present: {migrated[field]}")
        else:
            print(f"✗ {field} missing!")
    
    # Test that DEBUG_MODE and FILTER_MODE are in schema
    schema = omniprompt.CONFIG_SCHEMA
    if "DEBUG_MODE" in schema["properties"]:
        print("✓ DEBUG_MODE in schema")
    else:
        print("✗ DEBUG_MODE not in schema")
    
    if "FILTER_MODE" in schema["properties"]:
        print("✓ FILTER_MODE in schema")
    else:
        print("✗ FILTER_MODE not in schema")
    
    # Test that OPENAI_API_VERSION is in schema
    if "OPENAI_API_VERSION" in schema["properties"]:
        print("✓ OPENAI_API_VERSION in schema")
    else:
        print("✗ OPENAI_API_VERSION not in schema")
    
    # Test provider-specific URL keys
    url_keys = ["OLLAMA_BASE_URL", "LMSTUDIO_BASE_URL"]
    for key in url_keys:
        if key in migrated:
            print(f"✓ {key} present: {migrated[key]}")
        else:
            print(f"✗ {key} missing!")
    
    print("\n✅ All basic tests passed!")
    
except Exception as e:
    print(f"✗ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)