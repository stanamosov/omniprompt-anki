"""
OmniPrompt Anki Add‑on
Features:
- Non-modal dialog for "Update with OmniPrompt."
- Per-provider API keys (not per model).
- prompt_settings.json for storing each prompt's output field preference.
- QCompleter for searching saved prompts.
- CheckBox for "Append AI Output?" in the Update with OmniPrompt dialog.
"""

import requests, logging, os, time, socket, sys, json
from jsonschema import validate
from anki.errors import NotFoundError
from aqt.utils import showInfo, getText
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QDoubleValidator,
    QIntValidator,
    QKeySequence,
    QShortcut,
    QClipboard,
    QColor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QGroupBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QFormLayout,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QMenu,
    QCheckBox,
    QCompleter,
    QListWidget,
    QMessageBox,
    QSplitter,
    QProgressBar,
    QHeaderView,
    QTabWidget,
    QTabBar,
)
from aqt import mw, gui_hooks
from aqt.browser import Browser
from anki.hooks import addHook
from logging.handlers import RotatingFileHandler

# ----------------------------------------------------------------
# Constants & Config
# ----------------------------------------------------------------
AI_PROVIDERS = [
    "openai",
    "deepseek",
    "gemini",
    "anthropic",
    "xai",
    "ollama",
    "lmstudio",
]

DEFAULT_CONFIG = {
    "_version": 1.3,
    "AI_PROVIDER": "ollama",
    "OPENAI_MODEL": "gpt-4o-mini",
    "DEEPSEEK_MODEL": "deepseek-chat",
    "GEMINI_MODEL": "gemini-1.5-flash",
    "ANTHROPIC_MODEL": "claude-opus-4-latest",
    "XAI_MODEL": "grok-3-latest",
    "OLLAMA_MODEL": "llama3.2",
    "LMSTUDIO_MODEL": "local-model",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "LMSTUDIO_BASE_URL": "http://localhost:1234",
    # Provider test URLs (editable by user)
    "OPENAI_TEST_URL": "https://api.openai.com/v1/chat/completions",
    "DEEPSEEK_TEST_URL": "https://api.deepseek.com/chat/completions",
    "GEMINI_TEST_URL": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "ANTHROPIC_TEST_URL": "https://api.anthropic.com/v1/messages",
    "XAI_TEST_URL": "https://api.x.ai/v1/chat/completions",
    # OpenAI API version selector
    "OPENAI_API_VERSION": "modern",  # modern, legacy, or auto
    # Now includes all supported providers
    "API_KEYS": {
        # "openai": "...",
        # "deepseek": "...",
        # "gemini": "...",
        # "anthropic": "...",
        # "xai": "..."
    },
    "CUSTOM_MODELS": {
        "openai": [],
        "deepseek": [],
        "gemini": [],
        "anthropic": [],
        "xai": [],
        "ollama": [],
        "lmstudio": []
    },
    "TEMPERATURE": 0.2,
    "MAX_TOKENS": 500,
    "API_DELAY": 2,  # Delay (seconds) between API calls
    "TIMEOUT": 30,  # Request timeout
    "PROMPT": "Paste your prompt here.",
    "SELECTED_FIELDS": {"output_field": "Output"},
    "DEEPSEEK_STREAM": False,
    "APPEND_OUTPUT": False,
    "DEBUG_MODE": True,  # Show processing popups when enabled
    "FILTER_MODE": False,  # Skip notes where output field is filled
    "MULTI_FIELD_MODE": False,
    "AUTO_SEND_TO_CARD": True,  # New config key for auto-sending data
    # Note: Multi-field specific parameters removed for simplification
    # New GPT-5.4 specific parameters
    "OPENAI_REASONING_EFFORT": "none",  # none, low, medium, high, xhigh
    "OPENAI_VERBOSITY": "medium",  # low, medium, high
}

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "_version": {"type": "number"},
        "AI_PROVIDER": {"enum": AI_PROVIDERS},
        "OPENAI_MODEL": {"type": "string"},
        "DEEPSEEK_MODEL": {"type": "string"},
        "GEMINI_MODEL": {"type": "string"},
        "ANTHROPIC_MODEL": {"type": "string"},
        "XAI_MODEL": {"type": "string"},
        "OLLAMA_MODEL": {"type": "string"},
        "LMSTUDIO_MODEL": {"type": "string"},
        "OLLAMA_BASE_URL": {"type": "string"},
        "LMSTUDIO_BASE_URL": {"type": "string"},
        "OPENAI_TEST_URL": {"type": "string"},
        "DEEPSEEK_TEST_URL": {"type": "string"},
        "GEMINI_TEST_URL": {"type": "string"},
        "ANTHROPIC_TEST_URL": {"type": "string"},
        "XAI_TEST_URL": {"type": "string"},
        "OPENAI_API_VERSION": {"enum": ["modern", "legacy", "auto"]},
        "API_KEYS": {"type": "object"},
        "CUSTOM_MODELS": {"type": "object"},
        "TEMPERATURE": {"type": "number"},
        "MAX_TOKENS": {"type": "integer"},
        "API_DELAY": {"type": "number"},
        "TIMEOUT": {"type": "number"},
        "PROMPT": {"type": "string"},
        "DEEPSEEK_STREAM": {"type": "boolean"},
        "APPEND_OUTPUT": {"type": "boolean"},
        "DEBUG_MODE": {"type": "boolean"},
        "FILTER_MODE": {"type": "boolean"},
        "MULTI_FIELD_MODE": {"type": "boolean"},
        "AUTO_SEND_TO_CARD": {"type": "boolean"},
        "OPENAI_REASONING_EFFORT": {"enum": ["none", "low", "medium", "high", "xhigh"]},
        "OPENAI_VERBOSITY": {"enum": ["low", "medium", "high"]},
        "SELECTED_FIELDS": {
            "type": "object",
            "properties": {"output_field": {"type": "string"}},
        },
    },
    "required": ["AI_PROVIDER", "API_KEYS"],
}

PROMPT_SETTINGS_FILENAME = "prompt_settings.json"


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def safe_show_info(message: str) -> None:
    if omni_prompt_manager.config.get("DEBUG_MODE", True):
        QTimer.singleShot(0, lambda: showInfo(message))
    else:
        logger.info(f"Debug message (not shown to user): {message}")


def load_prompt_templates() -> dict:
    """Loads prompts from prompt_templates.txt using [[[Name]]] delimiters."""
    templates_path = os.path.join(os.path.dirname(__file__), "prompt_templates.txt")
    templates = {}
    if os.path.exists(templates_path):
        with open(templates_path, "r", encoding="utf-8") as file:
            current_key = None
            current_value = []
            for line in file:
                line = line.rstrip("\n")
                if line.startswith("[[[") and line.endswith("]]]"):
                    if current_key is not None:
                        templates[current_key] = "\n".join(current_value)
                    current_key = line[3:-3].strip()
                    current_value = []
                else:
                    current_value.append(line)
            if current_key is not None:
                templates[current_key] = "\n".join(current_value)
    return templates


def save_prompt_templates(templates: dict) -> None:
    templates_path = os.path.join(os.path.dirname(__file__), "prompt_templates.txt")
    os.makedirs(os.path.dirname(templates_path), exist_ok=True)
    with open(templates_path, "w", encoding="utf-8", newline="\n") as file:
        for key, value in sorted(templates.items()):
            # Strip trailing whitespace from the value before saving
            cleaned_value = value.rstrip()
            file.write(f"[[[{key}]]]\n{cleaned_value}\n")


def check_internet(provider: str = None) -> bool:
    """Check internet connectivity, but skip check for local providers."""
    # Skip internet check for local providers
    if provider and provider in ["ollama", "lmstudio"]:
        return True
    
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False


def get_prompt_settings_path() -> str:
    return os.path.join(os.path.dirname(__file__), PROMPT_SETTINGS_FILENAME)


def load_prompt_settings() -> dict:
    """Load each prompt’s extra settings from JSON (like outputField)."""
    path = get_prompt_settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"Failed to load prompt settings from {path}:")
        return {}


def save_prompt_settings(settings: dict) -> None:
    path = get_prompt_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.exception(f"Failed to save prompt settings to {path}:")


# ----------------------------------------------------------------
# CodeBlockParser
# ----------------------------------------------------------------
class CodeBlockParser:
    """Simple parser for code blocks ```FieldName\nContent``` with JSON fallback."""
    
    def __init__(self, target_note_fields: list = None):
        self.target_note_fields = target_note_fields or []

    def parse(self, text: str, target_note_fields: list = None) -> dict:
        """
        Returns: {field_name: content} dict
        Content: HTML-escaped (<br/> for \n).
        Simple regex parser for ```FieldName\nContent``` format.
        """
        import re
        
        text = text.strip()
        if not text:
            return {}
        
        # Use provided target fields or instance fields
        target_fields = target_note_fields or self.target_note_fields
        
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
            logger.debug(f"CodeBlockParser parsed {len(fields)} fields: {list(fields.keys())}")
        else:
            logger.debug(f"CodeBlockParser found no fields in text (length: {len(text)})")
        
        return fields

    def suggest_mappings(self, ai_fields: list, note_fields: list) -> dict:
        """Simple mapping: exact match or contains."""
        mappings = {}
        for ai in ai_fields:
            # Exact match
            if ai in note_fields:
                mappings[ai] = ai
            else:
                # Contains match (case-insensitive)
                matches = [nf for nf in note_fields if ai.lower() in nf.lower() or nf.lower() in ai.lower()]
                if matches:
                    mappings[ai] = matches[0]
                else:
                    mappings[ai] = ai  # Default 1:1 if no match
        return mappings


# ----------------------------------------------------------------
# Logger
# ----------------------------------------------------------------
def get_addon_dir() -> str:
    raw_dir = os.path.dirname(__file__)
    parent = os.path.dirname(raw_dir)
    base = os.path.basename(raw_dir).strip()
    return os.path.join(parent, base)


def setup_logger() -> logging.Logger:
    logger_obj = logging.getLogger("OmniPromptAnki")
    logger_obj.setLevel(logging.INFO)
    addon_dir = get_addon_dir()
    log_file = os.path.join(addon_dir, "omniprompt_anki.log")
    handler = SafeAnkiRotatingFileHandler(
        filename=log_file,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
        delay=True,
    )
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    if not logger_obj.handlers:
        logger_obj.addHandler(handler)
    return logger_obj


class SafeAnkiRotatingFileHandler(RotatingFileHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except Exception as e:
            print(f"Log write failed: {str(e)}")

    def shouldRollover(self, record) -> bool:
        try:
            return super().shouldRollover(record)
        except Exception as e:
            print(f"Log rotation check failed: {str(e)}")
            return False

    def doRollover(self):
        try:
            super().doRollover()
            print("Successfully rotated log file")
        except PermissionError:
            print("Couldn't rotate log - file in use")
        except Exception as e:
            print(f"Log rotation failed: {str(e)}")


def check_log_size():
    log_path = os.path.join(
        mw.addonManager.addonsFolder(), "omniprompt-anki", "omniprompt_anki.log"
    )
    try:
        size = os.path.getsize(log_path)
        if size > 4.5 * 1024 * 1024:
            print("Log file approaching maximum size")
    except Exception:
        pass


addHook("reset", check_log_size)
logger = setup_logger()


# ----------------------------------------------------------------
# Background Worker
# ----------------------------------------------------------------
class NoteProcessingWorker(QThread):
    progress_update = pyqtSignal(int, int)
    note_result = pyqtSignal(object, str)
    error_occurred = pyqtSignal(object, str)
    finished_processing = pyqtSignal(int, int, int)

    def __init__(self, note_prompts: list, generate_ai_response_callback, parent=None):
        super().__init__(parent)
        self.note_prompts = note_prompts
        self.generate_ai_response_callback = generate_ai_response_callback
        self._is_cancelled = False
        self.processed = 0
        self.error_count = 0

    def run(self) -> None:
        total = len(self.note_prompts)
        for i, (note, prompt) in enumerate(self.note_prompts):
            if self._is_cancelled:
                break
            self.progress_update.emit(i, 0)

            try:

                def per_chunk_progress(pct):
                    if pct >= 100:
                        pct = 99
                    self.progress_update.emit(i, pct)

                explanation = self.generate_ai_response_callback(
                    prompt, stream_progress_callback=per_chunk_progress
                )
                self.progress_update.emit(i, 100)
                self.note_result.emit(note, explanation)
            except Exception as e:
                self.error_count += 1
                logger.exception(f"Error processing note {note.id}")
                self.error_occurred.emit(note, str(e))

            self.processed += 1

        self.finished_processing.emit(self.processed, total, self.error_count)

    def cancel(self) -> None:
        self._is_cancelled = True


# ----------------------------------------------------------------
# OmniPromptManager
# ----------------------------------------------------------------
class OmniPromptManager:
    @property
    def addon_dir(self) -> str:
        return os.path.dirname(__file__)

    def __init__(self):
        self.config = self.load_config()
        mw.addonManager.setConfigAction(__name__, self.show_settings_dialog)

    def load_config(self) -> dict:
        raw_config = mw.addonManager.getConfig(__name__) or {}
        validated = self.validate_config(raw_config)
        return self.migrate_config(validated)

    def migrate_config(self, config: dict) -> dict:
        current_version = config.get("_version", 0)
        
        # If too old (pre-1.0), force full reset to new defaults (rare for v1.1 users)
        if current_version < 1.0:
            logger.info(f"Config too old (v{current_version}). Forcing reset to v1.3 defaults.")
            # Preserve API_KEYS if present to avoid total loss
            api_keys = config.get("API_KEYS", {})
            reset_config = DEFAULT_CONFIG.copy()
            reset_config["API_KEYS"] = api_keys  # Salvage old keys
            return reset_config

        # For v1.1 users: Preserve old values, add new fields without override
        if current_version < 1.2:
            # Add GPT-5 specific params (as in your original)
            config["OPENAI_REASONING_EFFORT"] = config.get("OPENAI_REASONING_EFFORT", "none")
            config["OPENAI_VERBOSITY"] = config.get("OPENAI_VERBOSITY", "medium")
            config["_version"] = 1.2
            logger.debug("Migrated v1.1 config to v1.2: Added GPT-5 params.")

        # For v1.2 users (or now v1.1 bumped to 1.2): Add v1.3 features
        if current_version < 1.3:
            # Preserve old AI_PROVIDER (e.g., "openai" from v1.1) – don't override with new "ollama" default
            old_provider = config.get("AI_PROVIDER", "openai")

            # Add new provider models/base URLs/test URLs with defaults, but only if missing
            new_keys = {
                "GEMINI_MODEL": "gemini-1.5-flash",
                "ANTHROPIC_MODEL": "claude-opus-4-latest",
                "XAI_MODEL": "grok-3-latest",
                "OLLAMA_MODEL": "llama3.2",
                "LMSTUDIO_MODEL": "local-model",
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "LMSTUDIO_BASE_URL": "http://localhost:1234",
                "OPENAI_TEST_URL": "https://api.openai.com/v1/chat/completions",
                "DEEPSEEK_TEST_URL": "https://api.deepseek.com/chat/completions",
                "GEMINI_TEST_URL": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                "ANTHROPIC_TEST_URL": "https://api.anthropic.com/v1/messages",
                "XAI_TEST_URL": "https://api.x.ai/v1/chat/completions",
                "OPENAI_API_VERSION": "modern",  # For GPT-5 support
                # New advanced toggles (default off/false to match old behavior)
                "FILTER_MODE": False,
                "MULTI_FIELD_MODE": False,
                "AUTO_SEND_TO_CARD": True,  # Sensible default
                # GPT-5 params (if not already added in 1.2)
                "OPENAI_REASONING_EFFORT": config.get("OPENAI_REASONING_EFFORT", "none"),
                "OPENAI_VERBOSITY": config.get("OPENAI_VERBOSITY", "medium"),
                # Custom models: Initialize empty for all (old has none)
                "CUSTOM_MODELS": {
                    "openai": config.get("CUSTOM_MODELS", {}).get("openai", []),
                    "deepseek": config.get("CUSTOM_MODELS", {}).get("deepseek", []),
                    "gemini": [],
                    "anthropic": [],
                    "xai": [],
                    "ollama": [],
                    "lmstudio": []
                }
            }
            
            # Merge new keys into config (preserves old, adds missing)
            for key, value in new_keys.items():
                if key not in config:
                    config[key] = value
            
            # Ensure AI_PROVIDER is preserved (old v1.1 value like "openai")
            config["AI_PROVIDER"] = old_provider
            
            config["_version"] = 1.3
            logger.info(f"Successfully migrated v{current_version} config to v1.3. Preserved old provider '{old_provider}' and added {len(new_keys)} new features (e.g., more providers, custom models).")
        
        # Note: Multi-field format migration removed for simplification

        # Final merge: Use new defaults for anything still missing, but preserve all old/existing values
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)  # Old values override defaults where present
        
        # Special: Ensure CUSTOM_MODELS is fully initialized (even if partial from old)
        if "CUSTOM_MODELS" not in merged:
            merged["CUSTOM_MODELS"] = DEFAULT_CONFIG["CUSTOM_MODELS"].copy()
        else:
            # Fill in empty lists for new providers if missing
            for prov in AI_PROVIDERS:
                if prov not in merged["CUSTOM_MODELS"]:
                    merged["CUSTOM_MODELS"][prov] = []
        
        return merged

    def validate_config(self, config: dict) -> dict:
        try:
            validate(instance=config, schema=CONFIG_SCHEMA)
            return config
        except Exception as e:
            logger.exception(f"Config validation error: {str(e)}")
            logger.info("Reverting to default configuration")
            return DEFAULT_CONFIG.copy()

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(mw)
        dialog.load_config(self.config)
        if dialog.exec():
            self.config = dialog.get_updated_config()
            self.save_config()

    def save_config(self) -> None:
        try:
            validated = self.validate_config(self.config)
            migrated = self.migrate_config(validated)
            logger.debug(
                f"Saving config: { {k: v for k, v in migrated.items() if k != 'API_KEYS'} }"
            )
            logger.debug(
                f"API_KEYS present: {'openai' in migrated.get('API_KEYS', {})}"
            )
            mw.addonManager.writeConfig(__name__, migrated)
            logger.info("Config saved successfully")
        except Exception as e:
            logger.exception(f"Config save failed: {str(e)}")
            pass

    def generate_ai_response(self, prompt: str, stream_progress_callback=None) -> str:
        provider = self.config.get("AI_PROVIDER", "openai")
        if provider == "openai":
            return self._make_openai_request(prompt, stream_progress_callback)
        elif provider == "deepseek":
            return self._make_deepseek_request(prompt, stream_progress_callback)
        elif provider == "gemini":
            return self._make_gemini_request(prompt, stream_progress_callback)
        elif provider == "anthropic":
            return self._make_anthropic_request(prompt, stream_progress_callback)
        elif provider == "xai":
            return self._make_xai_request(prompt, stream_progress_callback)
        elif provider == "ollama":
            return self._make_ollama_request(prompt, stream_progress_callback)
        elif provider == "lmstudio":
            return self._make_lmstudio_request(prompt, stream_progress_callback)
        else:
            logger.error(f"Invalid AI provider: {provider}")
            return "[Error: Invalid provider]"

    def _make_anthropic_request(self, prompt: str, stream_callback=None) -> str:
        api_key = self.config.get("API_KEYS", {}).get("anthropic", "")
        if not api_key:
            return "[Error: No Anthropic key found]"

        model = self.config.get("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": model,
            "max_tokens": self.config.get("MAX_TOKENS", 200),
            "temperature": self.config.get("TEMPERATURE", 0.2),
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.get("TIMEOUT", 20)
            )
            response.raise_for_status()
            response_json = response.json()

            if "content" in response_json and response_json["content"]:
                text = response_json["content"][0]["text"]
                return text.strip()
            return "[Error: Unexpected Anthropic response format]"

        except Exception as e:
            logger.exception("Anthropic API request failed:")
            return f"[Error: {str(e)}]"

    def _make_xai_request(self, prompt: str, stream_callback=None) -> str:
        api_key = self.config.get("API_KEYS", {}).get("xai", "")
        if not api_key:
            return "[Error: No xAI key found]"

        model = self.config.get("XAI_MODEL", "grok-1.5")
        url = "https://api.x.ai/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.get("TEMPERATURE", 0.2),
            "max_tokens": self.config.get("MAX_TOKENS", 200),
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.get("TIMEOUT", 20)
            )
            response.raise_for_status()
            response_json = response.json()

            if "choices" in response_json and response_json["choices"]:
                text = response_json["choices"][0]["message"]["content"]
                return text.strip()
            return "[Error: Unexpected xAI response format]"

        except Exception as e:
            logger.exception("xAI API request failed:")
            return f"[Error: {str(e)}]"

    def _make_gemini_request(self, prompt: str, stream_callback=None) -> str:
        api_key = self.config.get("API_KEYS", {}).get("gemini", "")
        if not api_key:
            return "[Error: No Gemini key found]"

        model = self.config.get("GEMINI_MODEL", "gemini-pro")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.config.get("TEMPERATURE", 0.2),
                "maxOutputTokens": self.config.get("MAX_TOKENS", 200),
            },
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.get("TIMEOUT", 20)
            )
            response.raise_for_status()
            response_json = response.json()

            if "candidates" in response_json and response_json["candidates"]:
                text = response_json["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            return "[Error: Unexpected Gemini response format]"

        except Exception as e:
            logger.exception("Gemini API request failed:")
            return f"[Error: {str(e)}]"

    def _make_openai_request(self, prompt: str, stream_callback=None) -> str:
            api_key = self.config.get("API_KEYS", {}).get("openai", "")
            if not api_key:
                return "[Error: No OpenAI key found]"

            model = self.config.get("OPENAI_MODEL", "gpt-4o-mini")
            api_version = self.config.get("OPENAI_API_VERSION", "modern")
            
            # Determine which API to use based on version selector
            if api_version == "modern":
                logger.info(f"Using modern API (GPT-5) for model: {model} (manual selection)")
                return self._make_gpt5_request(prompt, model, api_key, stream_callback)
            elif api_version == "legacy":
                logger.info(f"Using legacy API (Chat Completions) for model: {model} (manual selection)")
                return self._make_legacy_openai_request(prompt, model, api_key, stream_callback)
            else:  # "auto" - auto-detect based on model name
                # Check if using GPT-5 model family (new API endpoint)
                # Valid GPT-5.4 models from the documentation
                gpt5_models = ["gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5"]
                if any(model == m or model.startswith(f"{m}-") for m in gpt5_models):
                    logger.info(f"Using GPT-5 API for model: {model} (auto-detected)")
                    return self._make_gpt5_request(prompt, model, api_key, stream_callback)
                else:
                    # Use legacy API for older models
                    logger.info(f"Using legacy API for model: {model} (auto-detected)")
                    return self._make_legacy_openai_request(prompt, model, api_key, stream_callback)

    def _make_gpt5_request(self, prompt: str, model: str, api_key: str, stream_callback=None) -> str:
            """Make request using the new Responses API for GPT-5 models"""
            url = "https://api.openai.com/v1/responses"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            
            # Get reasoning effort from config, default to "none"
            reasoning_effort = self.config.get("OPENAI_REASONING_EFFORT", "none")
            
            # Validate reasoning effort
            valid_reasoning_efforts = ["none", "low", "medium", "high", "xhigh"]
            if reasoning_effort not in valid_reasoning_efforts:
                logger.warning(f"Invalid reasoning effort '{reasoning_effort}', defaulting to 'none'")
                reasoning_effort = "none"
            
            # Build request data for GPT-5.4
            # According to the OpenAI docs example, input can be a string
            data = {
                "model": model,
                "input": prompt,  # Just a string, not an array
                "max_output_tokens": self.config.get("MAX_TOKENS", 500),
            }
            
            # Handle parameters based on reasoning effort
            # GPT-5.4 models don't support temperature parameter
            if reasoning_effort != "none":
                # When reasoning effort is not "none", we use reasoning effort
                data["reasoning"] = {"effort": reasoning_effort}
                logger.info(f"Using reasoning.effort={reasoning_effort}")
            # Note: We don't add temperature at all for GPT-5.4 models
            
            # Add verbosity if specified (and not "medium")
            verbosity = self.config.get("OPENAI_VERBOSITY", "medium")
            valid_verbosity_levels = ["low", "medium", "high"]
            if verbosity in valid_verbosity_levels and verbosity != "medium":
                data["text"] = {"verbosity": verbosity}
                logger.info(f"Using text.verbosity={verbosity}")
            
            logger.info(f"Sending GPT-5 request to model: {model}")
            return self._send_gpt5_request(url, headers, data, stream_callback)

    def _make_legacy_openai_request(self, prompt: str, model: str, api_key: str, stream_callback=None) -> str:
        """Make request using legacy Chat Completions API for older models"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.get("MAX_TOKENS", 500),
            "temperature": self.config.get("TEMPERATURE", 0.2),
        }
        
        return self._send_request(url, headers, data)

    def _send_gpt5_request(self, url: str, headers: dict, data: dict, stream_callback=None) -> str:
        """Send request to GPT-5 Responses API"""
        retries = 3
        backoff_factor = 2
        timeout_val = self.config.get("TIMEOUT", 20)
        
        if not check_internet(self.config.get("AI_PROVIDER")):
            return "[Error: no internet connection]"
        
        # Dedented: The loop now runs after the internet check (whether it passes or fails, but since return exits early on failure, it's only for success)
        for attempt in range(retries):
            try:
                # Log request for debugging (without sensitive data)
                debug_data = data.copy()
                logger.info(f"GPT-5 request attempt {attempt+1}/{retries}")
                logger.debug(f"Request data: {debug_data}")
                
                resp = requests.post(
                    url, headers=headers, json=data, timeout=timeout_val
                )
                
                # Check for HTTP errors
                if resp.status_code != 200:
                    error_msg = f"HTTP {resp.status_code}: {resp.text}"
                    logger.error(f"GPT-5 API error: {error_msg}")
                    
                    # Try to parse OpenAI error message
                    try:
                        error_json = resp.json()
                        if "error" in error_json:
                            error_detail = error_json["error"]
                            if "message" in error_detail:
                                error_message = error_detail['message']
                                return f"[Error: OpenAI API - {error_message}]"
                    except:
                        pass
                    
                    return f"[Error: OpenAI API - {error_msg}]"
                
                # Get and log the raw response
                raw_response = resp.text
                logger.debug(f"RAW RESPONSE (full): {raw_response}")
                
                # Try to parse as JSON
                try:
                    resp_json = resp.json()
                    logger.debug(f"Parsed JSON response type: {type(resp_json)}")
                    logger.debug(f"Parsed JSON response keys: {list(resp_json.keys()) if isinstance(resp_json, dict) else 'Not a dict'}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response as JSON: {e}")
                    logger.error(f"Raw response was: {raw_response}")
                    # If it's not JSON, return the raw text
                    return raw_response.strip()
                
                time.sleep(self.config.get("API_DELAY", 1))
                
                # Parse the response
                result = self._parse_gpt5_response(resp_json)
                logger.info(f"GPT-5 response parsed successfully, length: {len(result)}")
                logger.debug(f"Parsed result: {result}")
                return result
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout. Retrying {attempt+1}/{retries}...")
                time.sleep(backoff_factor * (attempt + 1))
            except Exception as e:
                logger.exception(f"GPT-5 API error on attempt {attempt+1}:")
                if attempt == retries - 1:  # Last attempt
                    return f"[Error: {str(e)}]"
                time.sleep(backoff_factor * (attempt + 1))
        
        return "[Error: request failed after retries]"
        
    def _parse_gpt5_response(self, resp_json):
            """Parse GPT-5.4 response format - ULTRA SIMPLE VERSION"""
            logger.debug(f"GPT-5 response type: {type(resp_json)}")
            logger.debug(f"GPT-5 response: {resp_json}")
            
            # Convert to string first to handle all cases
            response_str = str(resp_json)
            
            # Look for the text field using regex
            import re
            
            # Pattern to match: text': '...' or text": "..." 
            # This handles both single and double quotes
            pattern = r"(?:'text'|\"text\")\s*:\s*['\"]([^'\"]*)['\"]"
            
            match = re.search(pattern, response_str)
            if match:
                text = match.group(1)
                logger.debug(f"Extracted text: {text}")
                return text.strip()
            
            # If no match, return the original string
            logger.warning(f"No 'text' field found in response: {response_str[:100]}...")
            return response_str.strip()

    def _make_deepseek_request(self, prompt: str, stream_callback=None) -> str:
        api_key = self.config.get("API_KEYS", {}).get("deepseek", "")
        if not api_key:
            return "[Error: No DeepSeek key found]"

        model = self.config.get("DEEPSEEK_MODEL", "deepseek-chat")
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.config.get("TEMPERATURE", 0.2),
            "max_tokens": self.config.get("MAX_TOKENS", 200),
            "stream": self.config.get("DEEPSEEK_STREAM", False),
        }
        timeout_val = self.config.get("TIMEOUT", 20)

        # (Same streaming logic as before)
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=timeout_val,
                stream=data["stream"],
            )
            response.raise_for_status()
        except Exception as e:
            logger.exception("DeepSeek request failed:")
            return "[Error: request failed]"

        if data["stream"]:
            final_msg = ""
            chunk_count = 0
            try:
                for line in response.iter_lines():
                    if self._is_empty_or_keepalive(line):
                        continue
                    chunk_count += 1
                    try:
                        json_line = json.loads(line.decode("utf-8"))
                        delta = (
                            json_line.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        final_msg += delta
                        if stream_callback:
                            approximate_pct = min(99, chunk_count * 5)
                            stream_callback(approximate_pct)
                    except Exception:
                        logger.exception("Error parsing a chunk from DeepSeek:")
                return final_msg if final_msg else "[Error: empty streamed response]"
            except Exception:
                logger.exception("Error reading DeepSeek stream:")
                return "[Error: streaming failure]"
        else:
            try:
                resp_json = response.json()
                if "choices" in resp_json and resp_json["choices"]:
                    txt = resp_json["choices"][0].get("message", {}).get("content", "")
                    return txt.strip() if txt else "[Error: empty response]"
                return "[Error: unexpected response format]"
            except Exception:
                logger.exception("DeepSeek non-stream parse error:")
                return "[Error: parse failure]"

    def _make_ollama_request(self, prompt: str, stream_callback=None) -> str:
        """Make request to local Ollama instance"""
        model = self.config.get("OLLAMA_MODEL", "llama3.2")
        base_url = self.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        url = f"{base_url}/api/generate"

        headers = {"Content-Type": "application/json"}

        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.get("TEMPERATURE", 0.2),
                "num_predict": self.config.get("MAX_TOKENS", 200),
            },
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.get("TIMEOUT", 60)
            )  # Longer timeout for local
            response.raise_for_status()
            response_json = response.json()

            if "response" in response_json:
                return response_json["response"].strip()
            return "[Error: Unexpected Ollama response format]"

        except requests.exceptions.ConnectionError:
            logger.exception("Cannot connect to Ollama. Is it running?")
            return "[Error: Cannot connect to Ollama. Make sure it's running on localhost:11434]"
        except Exception as e:
            logger.exception("Ollama API request failed:")
            return f"[Error: {str(e)}]"

    def _make_lmstudio_request(self, prompt: str, stream_callback=None) -> str:
        """Make request to local LM Studio instance"""
        model = self.config.get("LMSTUDIO_MODEL", "local-model")
        base_url = self.config.get("LMSTUDIO_BASE_URL", "http://localhost:1234")
        url = f"{base_url}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.get("TEMPERATURE", 0.2),
            "max_tokens": self.config.get("MAX_TOKENS", 200),
        }

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=self.config.get("TIMEOUT", 60)
            )  # Longer timeout for local
            response.raise_for_status()
            response_json = response.json()

            if "choices" in response_json and response_json["choices"]:
                text = response_json["choices"][0]["message"]["content"]
                return text.strip()
            return "[Error: Unexpected LM Studio response format]"

        except requests.exceptions.ConnectionError:
            logger.exception("Cannot connect to LM Studio. Is it running?")
            return "[Error: Cannot connect to LM Studio. Make sure it's running on localhost:1234]"
        except Exception as e:
            logger.exception("LM Studio API request failed:")
            return f"[Error: {str(e)}]"

    def _send_request(self, url: str, headers: dict, data: dict) -> str:
        retries = 3
        backoff_factor = 2
        timeout_val = self.config.get("TIMEOUT", 20)

        if not check_internet(self.config.get("AI_PROVIDER")):
            return "[Error: no internet connection]"

        for attempt in range(retries):
            try:
                safe_data = data.copy()
                if "Authorization" in headers:
                    safe_data["Authorization"] = "[REDACTED]"
                logger.info(f"Sending request attempt {attempt+1}: {safe_data}")
                resp = requests.post(
                    url, headers=headers, json=data, timeout=timeout_val
                )
                resp.raise_for_status()
                resp_json = resp.json()
                time.sleep(self.config.get("API_DELAY", 1))

                if "choices" in resp_json and resp_json["choices"]:
                    content = (
                        resp_json["choices"][0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if content:
                        return content
                    else:
                        return "[Error: empty response]"
                return "[Error: unexpected response format]"
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout. Retrying {attempt+1}/{retries}...")
                time.sleep(backoff_factor * (attempt + 1))
            except Exception as e:
                logger.exception("API error:")
                return f"[Error: request exception: {e}]"
        return "[Error: request failed after retries]"

    @staticmethod
    def _is_empty_or_keepalive(line: bytes) -> bool:
        if not line:
            return True
        text = line.decode("utf-8").strip()
        return (not text) or text.startswith("data: [DONE]") or text.startswith(":")


# ----------------------------------------------------------------
# SettingsDialog
# ----------------------------------------------------------------
class SettingsDialog(QDialog):
    """
    Single API key per provider.
    Changing the model won't affect the key field.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OmniPrompt Configuration")
        self.setMinimumWidth(500)
        self.config = None
        self.original_custom_models = None  # Track original custom models for change detection
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()

        # AI provider
        provider_group = QGroupBox("AI Provider Selection")
        provider_layout = QVBoxLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(AI_PROVIDERS)
        self.provider_combo.setToolTip("Select which AI provider to use (OpenAI, Ollama, etc.)")
        provider_layout.addWidget(QLabel("Select AI Provider:"))
        provider_layout.addWidget(self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Select or type model name. Use '+' to add custom models.")
        
        # "+" button for adding custom models
        self.add_custom_model_button = QPushButton("+")
        self.add_custom_model_button.setToolTip("Add current model as custom model")
        self.add_custom_model_button.clicked.connect(self.add_custom_model)
        
        # Horizontal layout for model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.add_custom_model_button)
        
        provider_layout.addLayout(model_layout)

        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Single "API Key" (one per provider)
        api_group = QGroupBox("API Settings")
        self.api_layout = QFormLayout()  # ← CHANGED: added self.

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter API key for the chosen provider")
        self.api_key_input.setToolTip("API key for the selected provider. Not needed for local providers like Ollama/LM Studio.")
        self.api_layout.addRow("API Key:", self.api_key_input)  # ← CHANGED: api_layout to self.api_layout

        self.temperature_input = QLineEdit()
        self.temperature_input.setValidator(QDoubleValidator(0.0, 2.0, 2))
        self.temperature_input.setToolTip("Controls randomness: 0.0 = deterministic, 2.0 = most random")
        self.api_layout.addRow("Temperature:", self.temperature_input)  # ← CHANGED

        self.max_tokens_input = QLineEdit()
        self.max_tokens_input.setValidator(QIntValidator(1, 4000))
        self.max_tokens_input.setToolTip("Maximum tokens in AI response (approx 1 token = 0.75 words)")
        self.api_layout.addRow("Max Tokens:", self.max_tokens_input)  # ← CHANGED

        api_group.setLayout(self.api_layout)  # ← CHANGED
        layout.addWidget(api_group)

        # Provider-specific settings (shown when provider selected)
        self.provider_settings_group = QGroupBox("Provider Settings")
        self.provider_settings_group.setVisible(False)  # Hidden by default
        provider_settings_layout = QVBoxLayout()
        
        # URL/Base URL field
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL/Base URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("API endpoint or base URL")
        self.url_input.setToolTip("API endpoint URL for cloud providers, or base URL for local providers like Ollama/LM Studio")
        url_layout.addWidget(self.url_input)
        provider_settings_layout.addLayout(url_layout)
        
        # Test connection button
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self.test_provider_connection)
        provider_settings_layout.addWidget(self.test_connection_button)
        
        # OpenAI-specific settings (only shown for OpenAI provider)
        self.openai_specific_group = QGroupBox("OpenAI-specific Settings")
        openai_layout = QVBoxLayout()
        
        # API version selector
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("API Version:"))
        self.api_version_combo = QComboBox()
        self.api_version_combo.addItems(["modern", "legacy", "auto"])
        version_layout.addWidget(self.api_version_combo)
        openai_layout.addLayout(version_layout)
        
        # Reasoning effort
        reasoning_layout = QHBoxLayout()
        reasoning_layout.addWidget(QLabel("Reasoning Effort:"))
        self.reasoning_effort_combo = QComboBox()
        self.reasoning_effort_combo.addItems(["none", "low", "medium", "high", "xhigh"])
        reasoning_layout.addWidget(self.reasoning_effort_combo)
        openai_layout.addLayout(reasoning_layout)
        
        # Verbosity
        verbosity_layout = QHBoxLayout()
        verbosity_layout.addWidget(QLabel("Verbosity:"))
        self.verbosity_combo = QComboBox()
        self.verbosity_combo.addItems(["low", "medium", "high"])
        verbosity_layout.addWidget(self.verbosity_combo)
        openai_layout.addLayout(verbosity_layout)
        
        self.openai_specific_group.setLayout(openai_layout)
        self.openai_specific_group.setVisible(False)  # Hidden by default
        provider_settings_layout.addWidget(self.openai_specific_group)
        
        # DeepSeek-specific settings (only shown for DeepSeek provider)
        self.deepseek_specific_group = QGroupBox("DeepSeek-specific Settings")
        deepseek_layout = QVBoxLayout()
        self.deepseek_stream_checkbox = QCheckBox("Enable Streaming")
        deepseek_layout.addWidget(self.deepseek_stream_checkbox)
        self.deepseek_specific_group.setLayout(deepseek_layout)
        self.deepseek_specific_group.setVisible(False)  # Hidden by default
        provider_settings_layout.addWidget(self.deepseek_specific_group)
        
        self.provider_settings_group.setLayout(provider_settings_layout)
        layout.addWidget(self.provider_settings_group)

        # Advanced settings
        self.advanced_button = QPushButton("Advanced Settings")
        self.advanced_button.clicked.connect(
            lambda: AdvancedSettingsDialog(self).exec()
        )
        layout.addWidget(self.advanced_button)

        # View log
        self.view_log_button = QPushButton("View Log")
        self.view_log_button.clicked.connect(self.show_log)
        layout.addWidget(self.view_log_button)

        # Save/Cancel
        btn_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connect
        self.provider_combo.currentIndexChanged.connect(self.update_model_options)
        self.model_combo.currentIndexChanged.connect(self.show_provider_key)

    def load_config(self, config: dict) -> None:
        self.config = config
        # Store original custom models for change detection
        self.original_custom_models = config.get("CUSTOM_MODELS", {}).copy()
        
        provider = config.get("AI_PROVIDER", "openai")
        self.provider_combo.setCurrentText(provider)
        self.update_model_options()

        if provider == "openai":
            self.model_combo.setCurrentText(config.get("OPENAI_MODEL", "gpt-4o-mini"))
        elif provider == "deepseek":
            self.model_combo.setCurrentText(
                config.get("DEEPSEEK_MODEL", "deepseek-chat")
            )
        elif provider == "gemini":
            self.model_combo.setCurrentText(config.get("GEMINI_MODEL", "gemini-pro"))
        elif provider == "anthropic":
            self.model_combo.setCurrentText(
                config.get("ANTHROPIC_MODEL", "claude-opus-4-latest")
            )
        elif provider == "xai":
            self.model_combo.setCurrentText(config.get("XAI_MODEL", "grok-3-latest"))
        elif provider == "ollama":
            self.model_combo.setCurrentText(config.get("OLLAMA_MODEL", "llama3.2"))
        elif provider == "lmstudio":
            self.model_combo.setCurrentText(config.get("LMSTUDIO_MODEL", "local-model"))

        # Show the key for whichever provider is selected
        self.show_provider_key()
        
        # Update provider-specific settings
        self.update_provider_specific_ui()

        self.temperature_input.setText(str(config.get("TEMPERATURE", 0.2)))
        self.max_tokens_input.setText(str(config.get("MAX_TOKENS", 200)))
        # Note: DEBUG_MODE and FILTER_MODE are now in AdvancedSettingsDialog

    def get_updated_config(self) -> dict:
        provider = self.provider_combo.currentText()
        if provider == "openai":
            self.config["OPENAI_MODEL"] = self.model_combo.currentText()
        elif provider == "deepseek":
            self.config["DEEPSEEK_MODEL"] = self.model_combo.currentText()
        elif provider == "gemini":
            self.config["GEMINI_MODEL"] = self.model_combo.currentText()
        elif provider == "anthropic":
            self.config["ANTHROPIC_MODEL"] = self.model_combo.currentText()
        elif provider == "xai":
            self.config["XAI_MODEL"] = self.model_combo.currentText()
        elif provider == "ollama":
            self.config["OLLAMA_MODEL"] = self.model_combo.currentText()
        elif provider == "lmstudio":
            self.config["LMSTUDIO_MODEL"] = self.model_combo.currentText()

        # Only store API key for non-local providers
        if provider not in ["ollama", "lmstudio"]:
            # Store the single key for this provider
            self.config.setdefault("API_KEYS", {})
            self.config["API_KEYS"][provider] = self.api_key_input.text()

        # Save provider-specific URL/base URL
        if provider in ["ollama", "lmstudio"]:
            # Custom models - base URL
            url_key = f"{provider.upper()}_BASE_URL"
            self.config[url_key] = self.url_input.text().strip()
        else:
            # Main providers - test URL
            url_key = f"{provider.upper()}_TEST_URL"
            self.config[url_key] = self.url_input.text().strip()

        # Save provider-specific settings
        if provider == "openai":
            self.config["OPENAI_API_VERSION"] = self.api_version_combo.currentText()
            self.config["OPENAI_REASONING_EFFORT"] = self.reasoning_effort_combo.currentText()
            self.config["OPENAI_VERBOSITY"] = self.verbosity_combo.currentText()
        elif provider == "deepseek":
            self.config["DEEPSEEK_STREAM"] = self.deepseek_stream_checkbox.isChecked()

        self.config["AI_PROVIDER"] = provider
        self.config["TEMPERATURE"] = float(self.temperature_input.text())
        self.config["MAX_TOKENS"] = int(self.max_tokens_input.text())
        # Note: DEBUG_MODE and FILTER_MODE are now saved from AdvancedSettingsDialog

        return self.config

    def get_current_model_for_provider(self, provider):
        """Get the current model for a provider from config"""
        provider_model_map = {
            "openai": "OPENAI_MODEL",
            "deepseek": "DEEPSEEK_MODEL", 
            "gemini": "GEMINI_MODEL",
            "anthropic": "ANTHROPIC_MODEL",
            "xai": "XAI_MODEL",
            "ollama": "OLLAMA_MODEL",
            "lmstudio": "LMSTUDIO_MODEL"
        }
        config_key = provider_model_map.get(provider)
        if config_key and self.config:
            return self.config.get(config_key, "")
        return ""

    def update_model_options(self):
        provider = self.provider_combo.currentText()
        self.model_combo.clear()
        
        # Default models for each provider
        default_models = []
        if provider == "openai":
            default_models = [
                "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o", 
                "gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano",
                "gpt-5",
                "o3-mini", "o1-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"
            ]
        elif provider == "deepseek":
            default_models = ["deepseek-chat", "deepseek-reasoner"]
        elif provider == "gemini":
            default_models = ["gemini-pro", "gemini-1.5-pro", "gemini-flash"]
        elif provider == "anthropic":
            default_models = [
                "claude-opus-4-latest",
                "claude-sonnet-4-latest",
                "claude-haiku-3.5-latest",
            ]
        elif provider == "xai":
            default_models = ["grok-3-latest", "grok-3-mini-latest"]
        elif provider == "ollama":
            default_models = [
                "llama3.2",
                "llama3.1",
                "llama2",
                "mistral",
                "mixtral",
                "codellama",
                "phi",
                "gemma",
                "qwen2.5",
            ]
        elif provider == "lmstudio":
            default_models = ["local-model"]
        
        # Get custom models for this provider
        custom_models = self.config.get("CUSTOM_MODELS", {}).get(provider, [])
        
        # Get current model from config for this provider
        current_model = self.get_current_model_for_provider(provider)
        
        # Combine all models: default + custom + current (if not in either)
        all_models = set()
        
        # Add default models
        for model in default_models:
            all_models.add(model)
        
        # Add custom models (excluding duplicates)
        for model in custom_models:
            all_models.add(model)
        
        # Add current model if not already in the list
        if current_model:
            all_models.add(current_model)
        
        # Sort all models alphabetically
        sorted_models = sorted(list(all_models), key=lambda x: x.lower())
        
        # Add sorted models to combobox
        self.model_combo.addItems(sorted_models)
        
        # Make combobox editable for ALL providers
        self.model_combo.setEditable(True)
        
        # Set current selection to the current model if it exists
        if current_model and current_model in sorted_models:
            self.model_combo.setCurrentText(current_model)
        self.show_provider_key()

    def add_custom_model(self):
        """Add current model to custom models list for the current provider"""
        provider = self.provider_combo.currentText()
        model_name = self.model_combo.currentText().strip()
        
        if not model_name:
            safe_show_info("Model name cannot be empty.")
            return
            
        # Ensure CUSTOM_MODELS exists in config
        if "CUSTOM_MODELS" not in self.config:
            self.config["CUSTOM_MODELS"] = {
                "openai": [],
                "deepseek": [],
                "gemini": [],
                "anthropic": [],
                "xai": [],
                "ollama": [],
                "lmstudio": []
            }
        
        # Get custom models for this provider
        custom_models = self.config["CUSTOM_MODELS"].get(provider, [])
        
        # Check if model already exists
        if model_name in custom_models:
            safe_show_info(f"Model '{model_name}' is already in custom models.")
            return
            
        # Add to custom models and sort alphabetically
        custom_models.append(model_name)
        custom_models.sort(key=lambda x: x.lower())
        self.config["CUSTOM_MODELS"][provider] = custom_models
        
        # Update the combobox to include the new model
        if model_name not in [self.model_combo.itemText(i) for i in range(self.model_combo.count())]:
            self.model_combo.addItem(model_name)
        
        # Show confirmation
        safe_show_info(f"Added '{model_name}' to custom models for {provider}.")
        
        # Set the combobox to the newly added model
        self.model_combo.setCurrentText(model_name)
        
        # Refresh the model dropdown to reflect sorted order
        self.update_model_options()

    def show_provider_key(self):
        provider = self.provider_combo.currentText()

        # Hide API key field for local providers
        if provider in ["ollama", "lmstudio"]:
            self.api_key_input.setVisible(False)
            # Find the label by iterating through the form layout
            if hasattr(self, "api_layout") and isinstance(self.api_layout, QFormLayout):
                label = self.api_layout.labelForField(self.api_key_input)
                if label:
                    label.setVisible(False)
        else:
            self.api_key_input.setVisible(True)
            # Show the label
            if hasattr(self, "api_layout") and isinstance(self.api_layout, QFormLayout):
                label = self.api_layout.labelForField(self.api_key_input)
                if label:
                    label.setVisible(True)
            key = self.config.get("API_KEYS", {}).get(provider, "")
            self.api_key_input.setText(key)
        
        # Also update provider-specific UI
        self.update_provider_specific_ui()

    def show_log(self) -> None:
        log_path = os.path.join(os.path.dirname(__file__), "omniprompt_anki.log")
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log_content = f.read()
        except Exception as e:
            safe_show_info(f"Failed to load log file: {e}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("OmniPrompt Anki Log")
        dlg.setMinimumSize(600, 400)
        lay = QVBoxLayout(dlg)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(log_content)
        lay.addWidget(txt)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn)

        dlg.exec()
    
    def update_provider_specific_ui(self):
        """Update provider-specific settings UI based on selected provider"""
        provider = self.provider_combo.currentText()
        
        # Show/hide provider settings group
        self.provider_settings_group.setVisible(True)
        
        # Get appropriate URL for the provider
        if provider in ["ollama", "lmstudio"]:
            # Custom models - base URL
            url_key = f"{provider.upper()}_BASE_URL"
            placeholder = f"Base URL for {provider.capitalize()}"
        else:
            # Main providers - test URL
            url_key = f"{provider.upper()}_TEST_URL"
            placeholder = f"Test URL for {provider.capitalize()}"
        
        # Set URL input
        url_value = self.config.get(url_key, "")
        self.url_input.setText(url_value)
        self.url_input.setPlaceholderText(placeholder)
        
        # Show/hide provider-specific groups
        self.openai_specific_group.setVisible(provider == "openai")
        self.deepseek_specific_group.setVisible(provider == "deepseek")
        
        # Load OpenAI-specific settings if OpenAI is selected
        if provider == "openai":
            self.api_version_combo.setCurrentText(
                self.config.get("OPENAI_API_VERSION", "modern")
            )
            self.reasoning_effort_combo.setCurrentText(
                self.config.get("OPENAI_REASONING_EFFORT", "none")
            )
            self.verbosity_combo.setCurrentText(
                self.config.get("OPENAI_VERBOSITY", "medium")
            )
        
        # Load DeepSeek-specific settings if DeepSeek is selected
        if provider == "deepseek":
            self.deepseek_stream_checkbox.setChecked(
                self.config.get("DEEPSEEK_STREAM", False)
            )
    
    def test_provider_connection(self):
        """Test connection for the selected provider"""
        provider = self.provider_combo.currentText()
        api_key = self.api_key_input.text().strip()
        
        logger.info(f"Testing connection for provider: {provider}")
        
        # First check internet connectivity
        if not check_internet(provider):
            safe_show_info("No internet connection. Please check your network.")
            logger.warning(f"No internet connection for provider: {provider}")
            return
        
        # Show testing message
        safe_show_info(f"Testing connection for {provider}...")
        logger.info(f"Starting connection test for {provider}")
        
        # Test based on provider type
        if provider in ["ollama", "lmstudio"]:
            # Custom models - test base URL
            url_key = f"{provider.upper()}_BASE_URL"
            test_url = self.url_input.text().strip() or self.config.get(url_key, "")
            if not test_url:
                safe_show_info(f"Please enter a valid base URL for {provider}.")
                return
            
            try:
                logger.info(f"Testing {provider} connection to URL: {test_url}")
                # Simple health check
                endpoint = f"{test_url.rstrip('/')}/api/tags" if provider == "ollama" else f"{test_url.rstrip('/')}/v1/models"
                logger.info(f"Requesting endpoint: {endpoint}")
                response = requests.get(endpoint, timeout=10)
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    safe_show_info(f"✅ {provider.capitalize()} connection successful!")
                    # For Ollama/LM Studio, also fetch and display available models
                    try:
                        # Try to parse JSON response
                        raw_response_text = response.text
                        models_data = response.json()
                        
                        # Log raw response (first 500 chars) for debugging
                        logger.debug(f"Raw response (first 500 chars): {raw_response_text[:500]}")
                        
                        # Extract model names with flexible parsing
                        model_names = []
                        
                        if provider == "ollama":
                            # Try multiple possible JSON structures for Ollama
                            if isinstance(models_data, dict):
                                if "models" in models_data and isinstance(models_data["models"], list):
                                    for model in models_data["models"]:
                                        if isinstance(model, dict) and "name" in model:
                                            model_names.append(model["name"])
                                        elif isinstance(model, str):
                                            model_names.append(model)
                                elif "data" in models_data and isinstance(models_data["data"], list):
                                    for model in models_data["data"]:
                                        if isinstance(model, dict) and "name" in model:
                                            model_names.append(model["name"])
                                        elif isinstance(model, str):
                                            model_names.append(model)
                                # Fallback: if root is a list
                                elif isinstance(models_data, list):
                                    for model in models_data:
                                        if isinstance(model, dict) and "name" in model:
                                            model_names.append(model["name"])
                                        elif isinstance(model, str):
                                            model_names.append(model)
                        
                        elif provider == "lmstudio":
                            # Try multiple possible JSON structures for LM Studio
                            if isinstance(models_data, dict):
                                if "data" in models_data and isinstance(models_data["data"], list):
                                    for model in models_data["data"]:
                                        if isinstance(model, dict):
                                            # Try various ID fields
                                            for field in ["id", "model_id", "name", "model"]:
                                                if field in model and model[field]:
                                                    model_names.append(model[field])
                                                    break
                                        elif isinstance(model, str):
                                            model_names.append(model)
                                elif "models" in models_data and isinstance(models_data["models"], list):
                                    for model in models_data["models"]:
                                        if isinstance(model, dict):
                                            for field in ["id", "model_id", "name", "model"]:
                                                if field in model and model[field]:
                                                    model_names.append(model[field])
                                                    break
                                        elif isinstance(model, str):
                                            model_names.append(model)
                                # Fallback: if root is a list
                                elif isinstance(models_data, list):
                                    for model in models_data:
                                        if isinstance(model, dict):
                                            for field in ["id", "model_id", "name", "model"]:
                                                if field in model and model[field]:
                                                    model_names.append(model[field])
                                                    break
                                        elif isinstance(model, str):
                                            model_names.append(model)
                        
                        # Remove duplicates and empty strings
                        model_names = list({name for name in model_names if name and isinstance(name, str)})
                        
                        if model_names:
                            logger.info(f"Available {provider.capitalize()} models ({len(model_names)}): {', '.join(model_names[:10])}{'...' if len(model_names) > 10 else ''}")
                            # Update model combo box with available models
                            self.update_model_combo_with_list(model_names)
                            # Show success message with model count
                            safe_show_info(f"✅ Found {len(model_names)} models for {provider.capitalize()}!")
                        else:
                            logger.warning(f"No models found in {provider.capitalize()} response. JSON structure may have changed.")
                            logger.debug(f"Full response JSON: {models_data}")
                            safe_show_info(f"✅ Connection successful but no models found. JSON structure may have changed.")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from {provider.capitalize()} response: {e}")
                        logger.error(f"Raw response (first 500 chars): {raw_response_text[:500]}")
                        safe_show_info(f"✅ Connection successful but could not parse model list. Check logs for details.")
                    except Exception as e:
                        logger.exception(f"Error processing {provider.capitalize()} model list:")
                        safe_show_info(f"✅ Connection successful but error processing model list: {str(e)[:100]}")
                else:
                    logger.warning(f"{provider.capitalize()} connection failed with status: {response.status_code}")
                    safe_show_info(f"❌ {provider.capitalize()} connection failed: HTTP {response.status_code}")
            except Exception as e:
                logger.exception(f"{provider.capitalize()} connection failed with exception:")
                safe_show_info(f"❌ {provider.capitalize()} connection failed: {str(e)}")
        
        else:
            # Main providers - test API key with minimal request
            if not api_key:
                safe_show_info(f"Please enter an API key for {provider}.")
                return
            
            url_key = f"{provider.upper()}_TEST_URL"
            test_url = self.url_input.text().strip() or self.config.get(url_key, "")
            
            # Prepare test request based on provider
            headers = {"Content-Type": "application/json"}
            if provider == "openai":
                headers["Authorization"] = f"Bearer {api_key}"
                test_data = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}]}
            elif provider == "deepseek":
                headers["Authorization"] = f"Bearer {api_key}"
                test_data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": "test"}]}
            elif provider == "gemini":
                # Gemini uses API key in URL
                model = self.config.get("GEMINI_MODEL", "gemini-pro")
                test_url = test_url.format(model=model)
                test_url = f"{test_url}?key={api_key}"
                test_data = {"contents": [{"parts": [{"text": "test"}]}]}
            elif provider == "anthropic":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
                test_data = {"model": "claude-3-haiku-20240307", "max_tokens": 5, "messages": [{"role": "user", "content": "test"}]}
            elif provider == "xai":
                headers["Authorization"] = f"Bearer {api_key}"
                test_data = {"model": "grok-3-mini-latest", "messages": [{"role": "user", "content": "test"}]}
            else:
                safe_show_info(f"Provider {provider} not supported for connection testing.")
                return
            
            try:
                # Make minimal test request
                response = requests.post(test_url, headers=headers, json=test_data, timeout=15)
                if response.status_code == 200:
                    safe_show_info(f"✅ {provider.capitalize()} API key is valid!")
                elif response.status_code == 401:
                    safe_show_info(f"❌ {provider.capitalize()} API key is invalid.")
                else:
                    safe_show_info(f"❌ {provider.capitalize()} connection failed: HTTP {response.status_code}")
            except Exception as e:
                safe_show_info(f"❌ {provider.capitalize()} connection failed: {str(e)}")
    
    def update_model_combo_with_list(self, model_names: list):
        """Update model combo box with fetched list of available models"""
        if not model_names:
            logger.warning("Empty model list received")
            return
        
        provider = self.provider_combo.currentText()
        current_model = self.model_combo.currentText()
        
        # Store custom models for this provider
        if "CUSTOM_MODELS" not in self.config:
            self.config["CUSTOM_MODELS"] = {
                "openai": [],
                "deepseek": [],
                "gemini": [],
                "anthropic": [],
                "xai": [],
                "ollama": [],
                "lmstudio": []
            }
        
        # Get existing custom models
        custom_models = self.config["CUSTOM_MODELS"].get(provider, [])
        
        # Combine fetched models with custom models (remove duplicates)
        all_models = set()
        for model in model_names:
            if model:  # Skip empty strings
                all_models.add(model)
        for model in custom_models:
            if model:
                all_models.add(model)
        
        # Keep current model in the list if it exists
        if current_model and current_model not in all_models:
            all_models.add(current_model)
        
        # Sort alphabetically
        sorted_models = sorted(list(all_models), key=lambda x: x.lower())
        
        # Update the combo box
        self.model_combo.clear()
        self.model_combo.addItems(sorted_models)
        self.model_combo.setEditable(True)
        
        # Try to restore previous selection
        if current_model in sorted_models:
            self.model_combo.setCurrentText(current_model)
        
        # Update tooltip to show all available models
        tooltip_text = f"Available models for {provider}:\n"
        for i, model in enumerate(sorted_models, 1):
            tooltip_text += f"{i}. {model}\n"
        
        # Limit tooltip length if too many models
        if len(sorted_models) > 50:
            tooltip_text = f"Available models for {provider}:\n"
            for i, model in enumerate(sorted_models[:50], 1):
                tooltip_text += f"{i}. {model}\n"
            tooltip_text += f"... and {len(sorted_models) - 50} more models"
        
        self.model_combo.setToolTip(tooltip_text.strip())
        logger.info(f"Updated model list for {provider} with {len(sorted_models)} models")
    
    def reject(self):
        """Override reject to check for unsaved model changes."""
        # Check if custom models have changed
        current_custom_models = self.config.get("CUSTOM_MODELS", {})
        
        if self.original_custom_models is not None and current_custom_models != self.original_custom_models:
            # Prompt user to save changes
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Save Fetched Models?")
            msg.setText("Save fetched models to custom models list?")
            msg.setInformativeText(
                "You have fetched new models that haven't been saved to your custom models list. "
                "If you don't save, these models will be lost when you close this dialog."
            )
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            result = msg.exec()
            
            if result == QMessageBox.StandardButton.Cancel:
                return  # Don't close dialog
            
            if result == QMessageBox.StandardButton.Yes:
                # Save config through the manager
                try:
                    from __init__ import omni_prompt_manager
                    omni_prompt_manager.config = self.config
                    omni_prompt_manager.save_config()
                    logger.info("Saved fetched models to config after user confirmation")
                except Exception as e:
                    logger.exception("Failed to save config after user confirmation:")
                    QMessageBox.critical(
                        self, 
                        "Save Failed", 
                        f"Failed to save config: {str(e)}"
                    )
                    return  # Don't close on save failure
        
        # Call parent reject to close dialog
        super().reject()


# ----------------------------------------------------------------
# AdvancedSettingsDialog
# ----------------------------------------------------------------
class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setMinimumWidth(400)
        self.config = omni_prompt_manager.config
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # API Delay
        self.api_delay_input = QLineEdit()
        self.api_delay_input.setValidator(QDoubleValidator(0.0, 60.0, 2, self))
        self.api_delay_input.setText(str(self.config.get("API_DELAY", 1)))
        form_layout.addRow("API Delay (seconds):", self.api_delay_input)

        # API Timeout
        self.timeout_input = QLineEdit()
        self.timeout_input.setValidator(QDoubleValidator(0.0, 300.0, 1, self))
        self.timeout_input.setText(str(self.config.get("TIMEOUT", 20)))
        form_layout.addRow("API Timeout (seconds):", self.timeout_input)

        # Debug Mode (Show processing popups)
        self.debug_mode_checkbox = QCheckBox("Show processing popups (Debug Mode)")
        self.debug_mode_checkbox.setChecked(self.config.get("DEBUG_MODE", True))
        form_layout.addRow(self.debug_mode_checkbox)

        # Filter Mode (Skip notes where output field is filled)
        self.filter_mode_checkbox = QCheckBox(
            "Skip notes where output field is filled (Filter Mode)"
        )
        self.filter_mode_checkbox.setChecked(self.config.get("FILTER_MODE", False))
        form_layout.addRow(self.filter_mode_checkbox)


        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(save_button)
        btn_layout.addWidget(cancel_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def accept(self) -> None:
        try:
            delay = float(self.api_delay_input.text())
            timeout_val = float(self.timeout_input.text())
        except ValueError:
            safe_show_info("Invalid numeric input.")
            return

        self.config["API_DELAY"] = delay
        self.config["TIMEOUT"] = timeout_val
        self.config["DEBUG_MODE"] = self.debug_mode_checkbox.isChecked()
        self.config["FILTER_MODE"] = self.filter_mode_checkbox.isChecked()

        omni_prompt_manager.save_config()
        super().accept()

# ----------------------------------------------------------------
# UpdateOmniPromptDialog
# ----------------------------------------------------------------
class UpdateOmniPromptDialog(QDialog):
    def __init__(self, notes, manager: OmniPromptManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update with OmniPrompt")
        self.notes = notes
        self.manager = manager
        self.worker = None
        self.setMinimumSize(800, 600)  # Set your desired minimum width and height
        # You could also use self.resize(800, 600) if you want it to open at a fixed size

        self.setWindowModality(Qt.WindowModality.NonModal)
        self.multi_field_mode = self.manager.config.get(
            "MULTI_FIELD_MODE", False
        )  # Initialize from config
        self.auto_detect_fields = []  # Store auto-detected field names
        # Multi-field UI elements
        self.multi_field_field_selector = None
        # Note type status
        self.note_type_status_label = None
        # Global progress tracking
        self.total_notes = 0
        self.global_progress_indeterminate = False
        
        # Simplified multi-field parser and state
        self.parser = None
        self.target_note_fields = []
        self.selected_field_checkboxes = {}
        self.field_checkbox_widgets = []
        
        # Warning tracking (once per session)
        self.field_warning_shown = False
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Create tab widget for left side
        self.tab_widget = QTabWidget()
        
        # Tab 1: Prompt & Settings
        self.prompt_tab = QWidget()
        prompt_tab_layout = QVBoxLayout(self.prompt_tab)
        
        # Note type status label
        self.note_type_status_label = QLabel("")
        self.update_note_type_status()
        prompt_tab_layout.addWidget(self.note_type_status_label)
        prompt_tab_layout.addSpacing(10)  # Add some spacing

        # Saved Prompts
        prompt_tab_layout.addWidget(QLabel("Saved Prompts:"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.setEditable(True)
        self.prompt_completer = QCompleter(self)
        self.prompt_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.prompt_combo.setCompleter(self.prompt_completer)
        prompt_tab_layout.addWidget(self.prompt_combo)

        # Prompt Template
        prompt_tab_layout.addWidget(QLabel("Prompt Template:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.prompt_edit.setPlainText(self.manager.config.get("PROMPT", ""))
        prompt_tab_layout.addWidget(self.prompt_edit)

        # Save Prompt
        self.save_prompt_button = QPushButton("Save Current Prompt")
        prompt_tab_layout.addWidget(self.save_prompt_button)

        # Insert Field Template button
        self.insert_field_template_button = QPushButton("Insert Field Template")
        self.insert_field_template_button.clicked.connect(self.import_fields_to_prompt)
        self.insert_field_template_button.setToolTip("Insert note field names into prompt at cursor position")
        prompt_tab_layout.addWidget(self.insert_field_template_button)

        # Output Field
        prompt_tab_layout.addWidget(QLabel("Output Field:"))
        self.output_field_combo = QComboBox()
        if self.notes:
            first_note = self.notes[0]
            model = mw.col.models.get(first_note.mid)
            if model:
                fields = mw.col.models.field_names(model)
                self.output_field_combo.addItems(fields)
        prompt_tab_layout.addWidget(self.output_field_combo)

        # Append CheckBox
        self.append_checkbox = QCheckBox("Append Output")
        self.append_checkbox.setChecked(self.manager.config.get("APPEND_OUTPUT", False))
        self.append_checkbox.setToolTip("Append adds to existing content without overwriting")
        self.append_checkbox.stateChanged.connect(self.on_append_checkbox_changed)
        prompt_tab_layout.addWidget(self.append_checkbox)

        # Add Multi-field Mode checkbox
        self.multi_field_checkbox = QCheckBox("Multi-field output")
        self.multi_field_checkbox.setChecked(
            self.manager.config.get("MULTI_FIELD_MODE", False)
        )
        self.multi_field_checkbox.stateChanged.connect(self.toggle_multi_field_mode)
        prompt_tab_layout.addWidget(self.multi_field_checkbox)

        # NEW: Auto Send Data to Card Checkbox
        self.auto_send_checkbox = QCheckBox("Automatically Send Data to Card")
        self.auto_send_checkbox.setChecked(
            self.manager.config.get("AUTO_SEND_TO_CARD", True)
        )
        self.auto_send_checkbox.stateChanged.connect(self.on_auto_send_checkbox_changed)
        prompt_tab_layout.addWidget(self.auto_send_checkbox)

        # Start / Stop / Save Edits
        self.start_button = QPushButton("Start")
        self.start_button.setMinimumSize(80, 30)  # Make it slightly bigger
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.save_changes_button = QPushButton("Send Data To Card")
        prompt_tab_layout.addWidget(self.start_button)
        prompt_tab_layout.addWidget(self.stop_button)
        prompt_tab_layout.addWidget(self.save_changes_button)
        
        # Add stretch to push everything up
        prompt_tab_layout.addStretch()
        
        # Tab 2: Field Configuration
        self.field_config_tab = QWidget()
        self.field_config_layout = QVBoxLayout(self.field_config_tab)
        
        # Field configuration placeholder
        self.field_config_placeholder = QLabel("Enable 'Multi-field output' to configure fields")
        self.field_config_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.field_config_placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.field_config_layout.addWidget(self.field_config_placeholder)
        
        # Format reminder note
        self.format_reminder_label = QLabel("Expected format in prompt: ```Field Name\nContent```")
        self.format_reminder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.format_reminder_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        self.format_reminder_label.hide()  # Hidden by default, shown when multi-field mode enabled
        self.field_config_layout.addWidget(self.format_reminder_label)
        
        # Parse Prompt button
        self.parse_prompt_button = QPushButton("Parse Prompt")
        self.parse_prompt_button.clicked.connect(self.parse_prompt_for_field_names)
        self.parse_prompt_button.setToolTip("Extract field names from prompt text and update checkbox selection")
        self.parse_prompt_button.hide()  # Hidden by default
        self.field_config_layout.addWidget(self.parse_prompt_button)
        
        # Field selector group box (will be populated when multi-field mode is enabled)
        self.multi_field_field_selector = QGroupBox("Select Fields to Update")
        self.field_selector_layout = QVBoxLayout()
        self.multi_field_field_selector.setLayout(self.field_selector_layout)
        self.multi_field_field_selector.hide()  # Hidden by default
        self.field_config_layout.addWidget(self.multi_field_field_selector)
        
        # Parse button
        self.parse_all_button = QPushButton("Parse Fields")
        self.parse_all_button.clicked.connect(self.parse_all_rows)
        self.parse_all_button.setToolTip("Manually parse raw AI output into field columns for all notes (auto-parsing happens automatically when each note completes)")
        self.parse_all_button.hide()  # Hidden by default
        self.field_config_layout.addWidget(self.parse_all_button)
        
        self.field_config_layout.addStretch()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.prompt_tab, "Prompt & Settings")
        self.tab_widget.addTab(self.field_config_tab, "Field Configuration")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget, 1)

        # Table with global progress bar
        table_container = QVBoxLayout()
        
        # Global progress bar (hidden by default, shown for >10 notes)
        self.global_progress_container = QWidget()
        global_progress_layout = QHBoxLayout(self.global_progress_container)
        self.global_progress_label = QLabel("Overall Progress:")
        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setRange(0, 100)
        self.global_progress_bar.setValue(0)
        global_progress_layout.addWidget(self.global_progress_label)
        global_progress_layout.addWidget(self.global_progress_bar)
        self.global_progress_container.setVisible(False)  # Hidden by default
        table_container.addWidget(self.global_progress_container)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Progress", "Original", "Generated"])
        self.table.horizontalHeader().setStretchLastSection(True)

        # Increase default row height
        self.table.verticalHeader().setDefaultSectionSize(35)  # Default is around 25-30
        # Increase default column width for better horizontal spacing
        self.table.horizontalHeader().setDefaultSectionSize(150)  # Adjust as needed
        # You can also set a minimum section size for more consistent spacing
        self.table.horizontalHeader().setMinimumSectionSize(100)
        self.table.verticalHeader().setMinimumSectionSize(30)
        table_container.addWidget(self.table)
        
        # Add table container to main layout with stretch factor 3
        main_layout.addLayout(table_container, 3)

        self.setLayout(main_layout)

        # Connect signals
        self.save_prompt_button.clicked.connect(self.save_current_prompt)
        self.start_button.clicked.connect(self.start_processing)
        self.stop_button.clicked.connect(self.stop_processing)
        self.save_changes_button.clicked.connect(self.save_manual_edits)

        self.load_prompts()
        if self.prompt_combo.currentText():
            self.load_selected_prompt(self.prompt_combo.currentText())
        self.prompt_combo.currentTextChanged.connect(self.load_selected_prompt)

        # Shortcut for Start
        sc = QShortcut(QKeySequence("Ctrl+Return"), self)
        sc.activated.connect(self.start_processing)

        # Apply initial multi-field mode state
        self.toggle_multi_field_mode(self.manager.config.get("MULTI_FIELD_MODE", False))

    def parse_fields_for_selected(self):
        """Parse generated text for selected rows into fields using new parser."""
        if not self.multi_field_mode or not self.parser:
            safe_show_info("Multi-field mode not active or parser not initialized.")
            return
        
        selected_rows = [
            idx.row() for idx in self.table.selectionModel().selectedRows()
        ]
        if not selected_rows:
            safe_show_info("Please select at least one row.")
            return

        total_parsed = 0
        for row in selected_rows:
            # In multi-field mode, generated rows are even rows (0, 2, 4...)
            if row % 2 == 1:
                row -= 1  # Convert to generated row
            
            raw_item = self.table.item(row, 1)  # Raw output column
            if not raw_item:
                continue

            explanation = raw_item.text()
            if not explanation.strip():
                continue
            
            # Save current state to undo stack
            current_state = {}
            for col in range(2, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    current_state[col] = item.text()
            
            if current_state:
                self.undo_stack.append((row, current_state))
                self.undo_button.setEnabled(True)
            
            # Parse with new parser
            fields, strategy, confidence = self.parser.parse(explanation, self.target_note_fields)
            
            # Apply field mappings
            if self.mapping_combo and self.mapping_combo.currentText() == "Auto-Map (Fuzzy Match)":
                mappings = self.parser.suggest_mappings(list(fields.keys()), self.target_note_fields)
            else:
                mappings = {k: k for k in fields.keys()}  # 1:1 mapping
            
            # Update table cells
            for ai_field, content in fields.items():
                target_field = mappings.get(ai_field, ai_field)
                # Find column for this field
                for col in range(2, self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col)
                    if header and header.text() == target_field:
                        # Create or update cell
                        if self.table.item(row, col) is None:
                            self.table.setItem(row, col, QTableWidgetItem())
                        self.table.item(row, col).setText(content)
                        
                        # Apply confidence-based color coding using QColor
                        if confidence > 0.8:
                            self.table.item(row, col).setBackground(QColor(200, 255, 200))  # Light green
                            self.table.item(row, col).setToolTip(f"High confidence ({confidence:.2f}) - {strategy}")
                        elif confidence > 0.5:
                            self.table.item(row, col).setBackground(QColor(255, 255, 200))  # Light yellow
                            self.table.item(row, col).setToolTip(f"Medium confidence ({confidence:.2f}) - {strategy}")
                        else:
                            self.table.item(row, col).setBackground(QColor(255, 200, 200))  # Light red
                            self.table.item(row, col).setToolTip(f"Low confidence ({confidence:.2f}) - {strategy}")
                        break
            
            total_parsed += 1
        
        safe_show_info(f"Parsed {total_parsed} selected row(s).")

    def on_append_checkbox_changed(self, state: int):
        logger.info(f"on_append_checkbox_changed start: state={state}")
        # Properly handle Qt.CheckState (0=Unchecked, 2=Checked)
        is_checked = bool(state)  # Convert Qt.CheckState to boolean
        logger.info(f"is_checked = {is_checked}")
        self.manager.config["APPEND_OUTPUT"] = is_checked
        logger.info(
            f"post-assign, config[APPEND_OUTPUT]={self.manager.config['APPEND_OUTPUT']}"
        )
        try:
            self.manager.save_config()
            # Verify config was saved by reloading
            reloaded_config = self.manager.load_config()
            logger.info(
                f"Reloaded config APPEND_OUTPUT={reloaded_config.get('APPEND_OUTPUT')}"
            )
            # Update checkbox to match saved state
            self.append_checkbox.setChecked(
                bool(reloaded_config.get("APPEND_OUTPUT", False))
            )
        except Exception as e:
            logger.exception("Failed to save/reload config:")
        logger.info(f"done saving config")

    def on_auto_send_checkbox_changed(self, state: int):
        is_checked = bool(state)
        self.manager.config["AUTO_SEND_TO_CARD"] = is_checked
        try:
            self.manager.save_config()
        except Exception as e:
            logger.exception("Failed to save auto-send to card setting:")
            if self.manager.config.get("DEBUG_MODE", False):
                safe_show_info(f"Failed to save setting: {str(e)}")

    def load_prompts(self):
        prompts = load_prompt_templates()
        self.prompt_combo.clear()
        for title in sorted(prompts.keys()):
            self.prompt_combo.addItem(title)
        self.prompt_completer.setModel(self.prompt_combo.model())

    def load_selected_prompt(self, text: str):
        prompts = load_prompt_templates()
        if text in prompts:
            self.prompt_edit.setPlainText(prompts[text])
        # Check if there's a saved outputField
        ps = load_prompt_settings()
        if text in ps:
            out_field = ps[text].get("outputField")
            if out_field and out_field in [
                self.output_field_combo.itemText(i)
                for i in range(self.output_field_combo.count())
            ]:
                self.output_field_combo.setCurrentText(out_field)

    def save_current_prompt(self):
        current_name = self.prompt_combo.currentText().strip()
        name, ok = getText("Enter a name for the prompt:", default=current_name)
        if ok and name:
            p = load_prompt_templates()
            p[name] = self.prompt_edit.toPlainText()
            save_prompt_templates(p)

            ps = load_prompt_settings()
            ps.setdefault(name, {})
            ps[name]["outputField"] = self.output_field_combo.currentText()
            save_prompt_settings(ps)

            self.load_prompts()
            self.prompt_combo.setCurrentText(name)
            showInfo("Prompt saved.")

    def toggle_multi_field_mode(self, state):
        """Enable/disable multi-field output mode with simplified UI."""
        is_checked = bool(state)
        self.multi_field_mode = is_checked

        # Save to config with error handling
        self.manager.config["MULTI_FIELD_MODE"] = is_checked
        try:
            self.manager.save_config()
        except Exception as e:
            logger.exception("Failed to save multi-field mode setting:")
            if self.manager.config.get("DEBUG_MODE", False):
                safe_show_info(f"Failed to save setting: {str(e)}")

        # Update UI controls
        self.output_field_combo.setEnabled(not self.multi_field_mode)
        self.append_checkbox.setEnabled(not self.multi_field_mode)

        # Clear the table when switching modes to prevent an inconsistent state
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        if not is_checked:
            # Single-field mode cleanup: Restore "Original" column
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Progress", "Original", "Generated"])

            # Hide field configuration placeholder and show field selector
            self.field_config_placeholder.show()
            if self.multi_field_field_selector:
                self.multi_field_field_selector.hide()
            
            # Hide parse buttons
            if self.parse_all_button:
                self.parse_all_button.hide()
            if self.parse_prompt_button:
                self.parse_prompt_button.hide()
            
            # Reset parser and state
            self.parser = None
            self.target_note_fields = []
            self.selected_field_checkboxes = {}
            self.field_checkbox_widgets = []
            return

        # --- SIMPLIFIED MULTI-FIELD MODE SETUP ---
        # Determine target note fields (excluding meta fields)
        if self.notes:
            first_note = self.notes[0]
            model = mw.col.models.get(first_note.mid)
            if model:
                all_fields = mw.col.models.field_names(model)
                self.target_note_fields = [f for f in all_fields if f not in ['Tags', 'Guid', 'Note Type']]

        if not self.target_note_fields:
            safe_show_info("No suitable fields found in note model. Multi-field disabled.")
            self.multi_field_mode = False
            self.multi_field_checkbox.setChecked(False)
            return

        # Initialize parser with target fields
        self.parser = CodeBlockParser(self.target_note_fields)

        # Clear existing widgets from field selector layout
        while self.field_selector_layout.count():
            child = self.field_selector_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Create checkboxes for each field
        self.selected_field_checkboxes = {}
        self.field_checkbox_widgets = []
        
        for field_name in self.target_note_fields:
            checkbox = QCheckBox(field_name)
            checkbox.setChecked(True)  # Default to selected
            self.selected_field_checkboxes[field_name] = checkbox
            self.field_checkbox_widgets.append(checkbox)
            self.field_selector_layout.addWidget(checkbox)
        
        # Select all/none buttons
        select_buttons_layout = QHBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(lambda: self._select_all_fields(True))
        select_none_button = QPushButton("Select None")
        select_none_button.clicked.connect(lambda: self._select_all_fields(False))
        select_buttons_layout.addWidget(select_all_button)
        select_buttons_layout.addWidget(select_none_button)
        select_buttons_layout.addStretch()
        self.field_selector_layout.addLayout(select_buttons_layout)
        
        # Show field selector, parse buttons, and format reminder
        self.field_config_placeholder.hide()
        self.multi_field_field_selector.show()
        self.parse_all_button.show()
        self.parse_prompt_button.show()
        self.format_reminder_label.show()
        
        # Update note type status
        self.update_note_type_status()
        
        safe_show_info(f"Multi-field enabled. {len(self.target_note_fields)} fields available. Select which fields to update.")

    def _select_all_fields(self, select_all):
        """Select or deselect all field checkboxes."""
        for checkbox in self.field_checkbox_widgets:
            checkbox.setChecked(select_all)

    def parse_all_rows(self):
        """Parse AI output for all rows into selected fields."""
        if not self.multi_field_mode or not self.parser:
            safe_show_info("Multi-field mode not active or parser not initialized.")
            return
        
        if not hasattr(self, 'selected_field_checkboxes'):
            safe_show_info("No fields selected for parsing.")
            return
        
        # Get selected fields
        selected_fields = []
        for field_name, checkbox in self.selected_field_checkboxes.items():
            if checkbox.isChecked():
                selected_fields.append(field_name)
        
        if not selected_fields:
            safe_show_info("No fields selected. Please check at least one field.")
            return
        
        # Ensure table has correct columns
        if self.table.columnCount() != 2 + len(selected_fields):
            self.table.setColumnCount(2 + len(selected_fields))
            headers = ["Progress", "Raw Output"] + selected_fields
            self.table.setHorizontalHeaderLabels(headers)
            
            # Adjust column widths
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 80)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for i in range(2, self.table.columnCount()):
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(i, 150)
        
        total_parsed = 0
        for row in range(self.table.rowCount()):
            raw_item = self.table.item(row, 1)  # Raw output column
            if not raw_item:
                continue
            
            explanation = raw_item.text()
            if not explanation.strip():
                continue
            
            # Parse with current parser
            fields = self.parser.parse(explanation, selected_fields)
            
            # Update table cells for selected fields
            for field_name, content in fields.items():
                if field_name in selected_fields:
                    # Find column index for this field
                    col_index = selected_fields.index(field_name) + 2
                    
                    # Create or update cell
                    if self.table.item(row, col_index) is None:
                        self.table.setItem(row, col_index, QTableWidgetItem())
                    self.table.item(row, col_index).setText(content)
            
            total_parsed += 1
        
        if total_parsed > 0:
            safe_show_info(f"Parsed {total_parsed} row(s) into selected fields.")
        else:
            safe_show_info("No rows with content to parse.")


    def test_parse_single_note(self):
        """Test parse on the first note only, showing preview and warnings"""
        if not self.notes:
            safe_show_info("No notes available for testing.")
            return
        
        if not self.multi_field_mode:
            safe_show_info("Enable 'Auto-detect multiple output fields' first.")
            return
        
        # Get the first note
        note = self.notes[0]
        prompt_template = self.prompt_edit.toPlainText()
        
        # Format prompt with note fields
        try:
            formatted_prompt = prompt_template.format(**note)
        except KeyError as e:
            safe_show_info(f"Missing field {e} in note {note.id}")
            return
        
        # Generate AI response for this single note
        try:
            explanation = self.manager.generate_ai_response(formatted_prompt)
        except Exception as e:
            safe_show_info(f"Failed to generate AI response: {str(e)}")
            return
        
        # Parse the output
        field_map = self.parse_multi_field_output(explanation)
        
        if not field_map:
            safe_show_info("No structure found—check prompt format.")
            return
        
        # Show preview
        preview_text = f"Parsed {len(field_map)} fields from AI output:\n\n"
        for field_name, content in field_map.items():
            preview_text += f"{field_name}: {content[:100]}...\n" if len(content) > 100 else f"{field_name}: {content}\n"
        
        safe_show_info(preview_text)

    def start_processing(self):
        note_prompts = []
        prompt_template = self.prompt_edit.toPlainText()
        output_field = self.output_field_combo.currentText().strip()

        # Only require output field if not in multi-field mode
        if not self.multi_field_mode and not output_field:
            safe_show_info("Please select an output field or enable multi-field mode.")
            return

        filter_mode = self.manager.config.get("FILTER_MODE", False)
        skipped_count = 0

        # Note type consistency check (for multi-field mode)
        if self.multi_field_mode and len(self.notes) > 1:
            unique_model_ids = set(note.mid for note in self.notes)
            if len(unique_model_ids) > 1:
                # Count notes per model
                model_counts = {}
                for note in self.notes:
                    model_counts[note.mid] = model_counts.get(note.mid, 0) + 1
                
                # Find most common model
                common_mid = max(model_counts, key=model_counts.get)
                common_count = model_counts[common_mid]
                total_count = len(self.notes)
                
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Multiple Note Types Detected")
                msg.setText(f"Selected notes use multiple types ({len(unique_model_ids)} total).")
                msg.setInformativeText(
                    f"Multi-field works best on one type to avoid field mismatches.\n\n"
                    f"Proceed with all {total_count} notes, or filter to the most common "
                    f"({common_count} notes of type {common_mid})?"
                )
                
                # Add custom buttons
                proceed_btn = msg.addButton("Proceed with all", QMessageBox.ButtonRole.YesRole)
                filter_btn = msg.addButton(f"Filter to {common_count} notes", QMessageBox.ButtonRole.NoRole)
                cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                
                msg.exec()
                
                clicked = msg.clickedButton()
                
                if clicked == cancel_btn:
                    return  # User cancelled
                elif clicked == filter_btn:
                    # Filter to most common model
                    self.notes = [n for n in self.notes if n.mid == common_mid]
                    if len(self.notes) == 0:
                        safe_show_info("No notes remaining after filtering.")
                        return

        for note in self.notes:
            try:
                # Skip note if filter mode is on and output field is not empty
                if (
                    filter_mode
                    and not self.multi_field_mode
                    and note[output_field].strip()
                ):
                    skipped_count += 1
                    continue
                
                # Apply custom format instructions for multi-field mode if enabled
                current_prompt_template = prompt_template
                if self.multi_field_mode:
                    # Always add default format instructions for multi-field mode
                    format_instructions = "\n\nTo fill multiple fields, use output in this format: ```Field Name\nGenerated Content to fill in the field```"
                    current_prompt_template = prompt_template + format_instructions
                
                formatted_prompt = current_prompt_template.format(**note)
            except KeyError as e:
                safe_show_info(f"Missing field {e} in note {note.id}")
                continue
            note_prompts.append((note, formatted_prompt))

        if filter_mode and skipped_count > 0:
            logger.info(
                f"Filter mode skipped {skipped_count} notes with filled output fields"
            )
            if self.manager.config.get("DEBUG_MODE", True):
                safe_show_info(
                    f"Skipped {skipped_count} notes with filled output fields"
                )

        if not note_prompts:
            safe_show_info("No valid notes to process.")
            return

        self.auto_detect_fields = []  # Clear auto-detect fields when starting
        
        # Global progress bar logic
        self.total_notes = len(note_prompts)
        
        # Show global progress bar for >10 notes
        if self.total_notes > 10:
            self.global_progress_container.setVisible(True)
            # Start in indeterminate mode (animated)
            self.global_progress_bar.setRange(0, 0)
            self.global_progress_indeterminate = True
        else:
            # Ensure it's hidden for small batches
            self.global_progress_container.setVisible(False)
            self.global_progress_indeterminate = False

        if self.multi_field_mode:
            # Simplified: single row per note
            self.table.setRowCount(len(note_prompts))
            for row, (note, _) in enumerate(note_prompts):
                progress_item = QTableWidgetItem("0%")
                progress_item.setData(Qt.ItemDataRole.UserRole, note.id)
                self.table.setItem(row, 0, progress_item)
                
                # Raw output column
                self.table.setItem(row, 1, QTableWidgetItem(""))
                
                # Create columns for selected fields only
                if hasattr(self, 'selected_field_checkboxes'):
                    selected_fields = []
                    for field_name, checkbox in self.selected_field_checkboxes.items():
                        if checkbox.isChecked():
                            selected_fields.append(field_name)
                    
                    # Validate that selected fields exist in note model
                    if selected_fields and self.notes:
                        first_note = self.notes[0]
                        model = mw.col.models.get(first_note.mid)
                        if model:
                            note_fields = mw.col.models.field_names(model)
                            invalid_fields = [f for f in selected_fields if f not in note_fields]
                            if invalid_fields:
                                # Show warning once per session
                                if not self.field_warning_shown:
                                    msg = QMessageBox(self)
                                    msg.setIcon(QMessageBox.Icon.Warning)
                                    msg.setWindowTitle("Field Warning")
                                    msg.setText(f"The following fields in your prompt don't exist in the note model: {', '.join(invalid_fields)}.")
                                    msg.setInformativeText("These may be formatting examples. They will be ignored during processing.")
                                    msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
                                    msg.setDefaultButton(QMessageBox.StandardButton.Ok)
                                    
                                    result = msg.exec()
                                    if result == QMessageBox.StandardButton.Cancel:
                                        return  # User cancelled
                                    
                                    self.field_warning_shown = True
                                
                                # Filter out invalid fields from selected_fields
                                selected_fields = [f for f in selected_fields if f in note_fields]
                    
                    # Set table columns: Progress, Raw Output, selected fields...
                    if self.table.columnCount() != 2 + len(selected_fields):
                        self.table.setColumnCount(2 + len(selected_fields))
                        headers = ["Progress", "Raw Output"] + selected_fields
                        self.table.setHorizontalHeaderLabels(headers)
                        
                        # Adjust column widths
                        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
                        self.table.setColumnWidth(0, 80)
                        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                        for i in range(2, self.table.columnCount()):
                            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                            self.table.setColumnWidth(i, 150)
                else:
                    # Fallback: all fields
                    if self.table.columnCount() != 3:
                        self.table.setColumnCount(3)
                        self.table.setHorizontalHeaderLabels(["Progress", "Original", "Generated"])
        else:
            # Original single-field mode: one row per note
            self.table.setRowCount(len(note_prompts))
            for row, (note, _) in enumerate(note_prompts):
                progress_item = QTableWidgetItem("0%")
                original_text = (
                    note[output_field] if output_field and output_field in note else ""
                )
                original_item = QTableWidgetItem(original_text)
                original_item.setData(Qt.ItemDataRole.UserRole, note.id)
                self.table.setItem(row, 0, progress_item)
                self.table.setItem(row, 1, original_item)
                self.table.setItem(row, 2, QTableWidgetItem(""))

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.worker = NoteProcessingWorker(note_prompts, self._generate_with_progress)
        self.worker.progress_update.connect(
            self.update_progress_cell, Qt.ConnectionType.QueuedConnection
        )
        self.worker.note_result.connect(
            self.update_note_result, Qt.ConnectionType.QueuedConnection
        )
        self.worker.finished_processing.connect(
            self.processing_finished, Qt.ConnectionType.QueuedConnection
        )
        self.worker.start()

    def parse_multi_field_output(self, explanation: str) -> dict:
        """Parse AI output using simple regex for ```FieldName\nContent``` format."""
        if not self.multi_field_mode:
            return {}  # Not in multi-field mode
        
        if self.parser:
            # Use CodeBlockParser if available
            return self.parser.parse(explanation, self.target_note_fields)
        
        # Fallback simple regex parsing
        import re
        field_map = {}
        pattern = r"```\s*([^`\n]+?)\s*\n([\s\S]*?)\s*```"
        matches = re.findall(pattern, explanation, re.DOTALL)
        
        for field_name, field_content in matches:
            field_name = field_name.strip()
            field_content = field_content.strip().replace('\n', '<br/>')  # Anki HTML
            if field_name and field_content:
                field_map[field_name] = field_content
        
        return field_map

    def update_note_result(self, note, explanation: str):
        """Handles a single AI response, updating the table and optionally auto-saving."""
        auto_send = self.manager.config.get("AUTO_SEND_TO_CARD", True)

        if self.multi_field_mode:
            # Find the generated row (even rows) for this note
            for row in range(0, self.table.rowCount(), 2):
                progress_item = self.table.item(row, 0)
                if (
                    progress_item
                    and progress_item.data(Qt.ItemDataRole.UserRole) == note.id
                ):
                    progress_item.setText("100%")
                    self.table.item(row, 1).setText(
                        explanation
                    )  # Generated content in column 1
                    logger.info(
                        f"Multi-field: Stored raw explanation for note {note.id}."
                    )
                    
                    # Auto-parse the raw output for this note with 100ms delay
                    QTimer.singleShot(100, lambda r=row, e=explanation: self._auto_parse_note_output(r, e))
                    break
        else:  # Single-field mode
            for row in range(self.table.rowCount()):
                original_item = self.table.item(row, 1)
                if (
                    original_item
                    and original_item.data(Qt.ItemDataRole.UserRole) == note.id
                ):
                    self.table.item(row, 0).setText("100%")
                    self.table.item(row, 2).setText(
                        explanation
                    )  # Generated content in column 2

                    if auto_send:
                        output_field = self.output_field_combo.currentText().strip()
                        append_mode = self.manager.config.get("APPEND_OUTPUT", False)
                        logger.info(
                            f"Single-field: Auto-sending to note {note.id} in {'append' if append_mode else 'replace'} mode."
                        )

                        if append_mode:
                            original_field_text = note[output_field]
                            note[output_field] = (
                                (original_field_text + "\n\n" + explanation)
                                if original_field_text
                                else explanation
                            )
                        else:
                            note[output_field] = explanation

                        try:
                            mw.col.update_note(note)
                            logger.info(f"Successfully auto-updated note {note.id}")
                        except Exception as e:
                            logger.exception(f"Error auto-updating note {note.id}: {e}")
                    else:
                        logger.info(
                            f"Single-field: Auto-send is off for note {note.id}."
                        )
                    break
    
    def _auto_parse_note_output(self, row: int, explanation: str):
        """Auto-parse a single note's raw output when it reaches 100% progress."""
        if not self.multi_field_mode or not self.parser:
            return
        
        if not hasattr(self, 'selected_field_checkboxes'):
            return
        
        # Get selected fields
        selected_fields = []
        for field_name, checkbox in self.selected_field_checkboxes.items():
            if checkbox.isChecked():
                selected_fields.append(field_name)
        
        if not selected_fields:
            return
        
        # Ensure table has correct columns
        if self.table.columnCount() != 2 + len(selected_fields):
            self.table.setColumnCount(2 + len(selected_fields))
            headers = ["Progress", "Raw Output"] + selected_fields
            self.table.setHorizontalHeaderLabels(headers)
            
            # Adjust column widths
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 80)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for i in range(2, self.table.columnCount()):
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(i, 150)
        
        # Parse with current parser
        fields = self.parser.parse(explanation, selected_fields)
        
        # Update table cells for selected fields
        for field_name, content in fields.items():
            if field_name in selected_fields:
                # Find column index for this field
                col_index = selected_fields.index(field_name) + 2
                
                # Create or update cell
                if self.table.item(row, col_index) is None:
                    self.table.setItem(row, col_index, QTableWidgetItem())
                self.table.item(row, col_index).setText(content)
        
        logger.info(f"Auto-parsed note output for row {row}")

    def stop_processing(self):
        if self.worker:
            self.worker.cancel()
            self.stop_button.setEnabled(False)
            # Reset and hide global progress bar
            self.global_progress_bar.setValue(0)
            self.global_progress_container.setVisible(False)
            self.global_progress_indeterminate = False

    def _generate_with_progress(self, prompt, stream_progress_callback=None):
        return self.manager.generate_ai_response(prompt, stream_progress_callback)

    def update_progress_cell(self, note_index: int, pct: int):
        # In multi-field mode, progress is on the 'generated' row (even rows)
        row_index = note_index * 2 if self.multi_field_mode else note_index
        item = self.table.item(row_index, 0)
        if item:
            item.setText(f"{pct}%")
        
        # Also update global progress bar if visible
        self.update_global_progress(note_index, pct)

    def update_global_progress(self, note_index: int, pct: int):
        """Update the global progress bar with overall progress."""
        # Only update if the container is visible (>10 notes)
        if not self.global_progress_container.isVisible():
            return
        
        # Switch from indeterminate to determinate on first progress
        if self.global_progress_indeterminate:
            self.global_progress_bar.setRange(0, 100)
            self.global_progress_indeterminate = False
        
        # Calculate overall progress (0-100)
        if self.total_notes > 0:
            overall = int((note_index * 100 + pct) / self.total_notes)
            self.global_progress_bar.setValue(min(overall, 100))

    def save_manual_edits(self):
        """Saves the current content from the table cells to the Anki notes."""
        if self.multi_field_mode:
            # Check for mismatches before saving
            mismatched_notes = 0
            total_notes = 0
            
            # First pass: count mismatches
            for row in range(0, self.table.rowCount(), 2):
                progress_item = self.table.item(row, 0)
                if not progress_item:
                    continue
                
                total_notes += 1
                note_id = progress_item.data(Qt.ItemDataRole.UserRole)
                note = mw.col.get_note(note_id)
                
                # Count mismatches (fields with content but not in note)
                for col, field_name in enumerate(self.auto_detect_fields, start=2):
                    if col < self.table.columnCount():
                        item = self.table.item(row, col)
                        if item and item.text().strip() and field_name not in note:
                            mismatched_notes += 1
                            break  # Count note once if any mismatch
            
            # Show confirmation if mismatches > 0
            if mismatched_notes > 0:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Question)
                msg.setWindowTitle("Confirm Save")
                msg.setText(f"Save changes?")
                msg.setInformativeText(
                    f"{mismatched_notes} notes have partial field matches. "
                    f"Fields not in note model will be skipped."
                )
                msg.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if msg.exec() != QMessageBox.StandardButton.Yes:
                    return
            
            # Second pass: save data
            saved_count = 0
            skipped_fields_total = 0
            
            for row in range(0, self.table.rowCount(), 2):
                progress_item = self.table.item(row, 0)
                if not progress_item:
                    continue

                note_id = progress_item.data(Qt.ItemDataRole.UserRole)
                note = mw.col.get_note(note_id)
                
                saved_note = False
                skipped_fields_note = 0

                # Update each detected field (starting from column 2)
                for col, field_name in enumerate(self.auto_detect_fields, start=2):
                    if col < self.table.columnCount():
                        item = self.table.item(row, col)
                        if item and item.text().strip():
                            if field_name in note:
                                # Apply append logic if append mode is enabled
                                if self.append_checkbox.isChecked():
                                    original_text = note[field_name]
                                    note[field_name] = (original_text + "\n\n--- AI Generated ---\n" + item.text()) if original_text else item.text()
                                else:
                                    note[field_name] = item.text()
                                saved_note = True
                            else:
                                skipped_fields_note += 1
                                logger.info(f"Note {note_id}: Skipped '{field_name}'—no matching note field.")
                
                if saved_note:
                    try:
                        mw.col.update_note(note)
                        saved_count += 1
                        logger.info(f"Successfully saved multi-field edits for note {note_id}")
                    except Exception as e:
                        logger.exception(f"Error saving manual multi-field edit for note {note_id}: {e}")
                
                skipped_fields_total += skipped_fields_note
            
            # Show summary
            summary_msg = f"Saved: {saved_count}/{total_notes} notes."
            if skipped_fields_total > 0:
                summary_msg += f" {skipped_fields_total} fields skipped due to mismatches."
            safe_show_info(summary_msg)
        else:
            # Original single-field save logic
            output_field = self.output_field_combo.currentText().strip()
            if not output_field:
                safe_show_info("Please select an output field to save changes.")
                return

            for row in range(self.table.rowCount()):
                original_item = self.table.item(row, 1)
                if not original_item:
                    continue

                note_id = original_item.data(Qt.ItemDataRole.UserRole)
                note = mw.col.get_note(note_id)
                new_text = self.table.item(row, 2).text()

                try:
                    note[output_field] = new_text
                    mw.col.update_note(note)
                    logger.info(
                        f"Successfully saved single-field edit for note {note_id}"
                    )
                except Exception as e:
                    logger.exception(
                        f"Error saving manual single-field edit for note {note_id}: {e}"
                    )
            safe_show_info("All single-field edits saved to notes.")

    def processing_finished(self, processed: int, total: int, error_count: int):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Update global progress bar to 100% and hide it
        self.global_progress_bar.setValue(100)
        self.global_progress_container.setVisible(False)
        self.global_progress_indeterminate = False

        auto_send = self.manager.config.get("AUTO_SEND_TO_CARD", True)

        # In multi-field mode, parse all results now that they are complete
        if self.multi_field_mode:
            self.parse_fields_for_all_rows(save_to_notes=auto_send)
            if auto_send:
                safe_show_info(
                    "Processing finished. Multi-field data has been automatically sent to cards."
                )
            else:
                safe_show_info(
                    "Processing finished. Press 'Send Data To Card' to save changes."
                )
        else:  # Single-field mode
            message = f"Processing finished. Processed: {processed}/{total} notes."
            if error_count > 0:
                message += f" Errors: {error_count}."
            if not auto_send:
                message += " Press 'Send Data To Card' to save changes."
            safe_show_info(message)

    def parse_fields_for_all_rows(self, save_to_notes: bool = False):
        """Parse generated text for all notes into fields, updating the table layout.
        If save_to_notes is True, also saves changes to the Anki notes.
        """
        if not self.multi_field_mode:
            return

        # 1. Get selected fields from checkboxes (if available)
        selected_fields = []
        if hasattr(self, 'selected_field_checkboxes'):
            for field_name, checkbox in self.selected_field_checkboxes.items():
                if checkbox.isChecked():
                    selected_fields.append(field_name)
        
        # If no fields selected, fall back to auto-detection from AI output
        auto_detect_mode = len(selected_fields) == 0
        
        # 2. Collect field maps from 'Generated' rows
        all_fields = set()
        note_field_maps = []
        note_models = {}  # Store note_id -> model for consistency check
        for row in range(0, self.table.rowCount(), 2):
            explanation = (
                self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            )
            field_map = self.parse_multi_field_output(explanation)
            note_field_maps.append(field_map)
            all_fields.update(field_map.keys())
            
            # Store note model for consistency check
            progress_item = self.table.item(row, 0)
            if progress_item:
                note_id = progress_item.data(Qt.ItemDataRole.UserRole)
                note = mw.col.get_note(note_id)
                note_models[note_id] = note.mid

        # 3. Determine which fields to use for table columns
        if auto_detect_mode:
            # Auto-detection mode: use fields from AI output
            self.auto_detect_fields = sorted(list(all_fields))
        else:
            # User-selected mode: use selected fields
            self.auto_detect_fields = selected_fields
        
        # 4. Update table structure with the determined fields
        new_column_count = 2 + len(self.auto_detect_fields)
        # Only update columns if they don't already match
        if self.table.columnCount() != new_column_count:
            self.table.setColumnCount(new_column_count)
            self.table.setHorizontalHeaderLabels(
                ["Progress", "Raw Output"] + self.auto_detect_fields
            )
            
            # Adjust column widths
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 80)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for i in range(2, self.table.columnCount()):
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(i, 150)

        # 2a. Field mismatch handling (if we have notes)
        field_mapping = {}  # parsed_field -> note_field mapping
        skipped_fields = set()
        if self.notes and all_fields:
            # Get fields from first note's model (assume consistent model)
            first_note = self.notes[0]
            first_model = mw.col.models.get(first_note.mid)
            if first_model:
                note_fields = set(mw.col.models.field_names(first_model))
                parsed_fields = set(self.auto_detect_fields)
                
                # Calculate mismatch percentage
                if parsed_fields:
                    mismatches = parsed_fields - note_fields
                    mismatch_percent = len(mismatches) / len(parsed_fields) * 100
                    
                    if mismatch_percent > 20:  # More than 20% mismatch
                        # Show popup with options
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Icon.Warning)
                        msg.setWindowTitle("Field Mismatches Detected")
                        
                        parsed_text = ", ".join(sorted(parsed_fields))
                        note_text = ", ".join(sorted(note_fields))
                        msg.setText(f"Field mismatches detected:\n\nParsed: {parsed_text}\nAvailable in note: {note_text}")
                        msg.setInformativeText("Auto-map similar names?")
                        
                        # Add custom buttons
                        auto_map_btn = msg.addButton("Auto-map similar names", QMessageBox.ButtonRole.YesRole)
                        exact_only_btn = msg.addButton("Save only exact matches", QMessageBox.ButtonRole.NoRole)
                        manual_btn = msg.addButton("Manual Map", QMessageBox.ButtonRole.ActionRole)
                        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                        
                        msg.exec()
                        
                        clicked = msg.clickedButton()
                        
                        if clicked == cancel_btn:
                            return  # User cancelled
                        elif clicked == auto_map_btn:
                            # Auto-map using simple fuzzy matching
                            for parsed_field in parsed_fields:
                                matched = False
                                # Try exact match first
                                if parsed_field in note_fields:
                                    field_mapping[parsed_field] = parsed_field
                                    matched = True
                                else:
                                    # Try substring matching (case-insensitive)
                                    for note_field in note_fields:
                                        if parsed_field.lower() in note_field.lower():
                                            field_mapping[parsed_field] = note_field
                                            matched = True
                                            break
                                    # Try starts-with as fallback
                                    if not matched:
                                        for note_field in note_fields:
                                            if note_field.lower().startswith(parsed_field.lower()[:3]):
                                                field_mapping[parsed_field] = note_field
                                                matched = True
                                                break
                                if not matched:
                                    skipped_fields.add(parsed_field)
                        elif clicked == exact_only_btn:
                            # Only map exact matches
                            for parsed_field in parsed_fields:
                                if parsed_field in note_fields:
                                    field_mapping[parsed_field] = parsed_field
                                else:
                                    skipped_fields.add(parsed_field)
                        elif clicked == manual_btn:
                            # Simple manual mapping - for now just use exact matches
                            # TODO: Could implement more sophisticated dialog
                            for parsed_field in parsed_fields:
                                if parsed_field in note_fields:
                                    field_mapping[parsed_field] = parsed_field
                                else:
                                    skipped_fields.add(parsed_field)
                    else:
                        # Minor mismatches, auto-map with fuzzy logic
                        for parsed_field in parsed_fields:
                            if parsed_field in note_fields:
                                field_mapping[parsed_field] = parsed_field
                            else:
                                # Try fuzzy matching
                                matched = False
                                for note_field in note_fields:
                                    if parsed_field.lower() in note_field.lower():
                                        field_mapping[parsed_field] = note_field
                                        matched = True
                                        break
                                if not matched:
                                    skipped_fields.add(parsed_field)
                else:
                    # No parsed fields - show warning
                    if len(self.notes) > 0 and self.manager.config.get("DEBUG_MODE", False):
                        safe_show_info("No fields detected in AI output. Check prompt format.")
        
        # 2b. Calculate parse success rate
        total_notes = len(note_field_maps)
        if total_notes > 0:
            total_fields = sum(len(fm) for fm in note_field_maps)
            avg_fields = total_fields / total_notes if total_notes > 0 else 0
            
            # Show warning if parse success <50%
            if avg_fields < 0.5 and total_notes >= 3:
                warning_msg = f"Low parse success (average {avg_fields:.1f} fields per note across {total_notes} notes).\n"
                warning_msg += "Try JSON mode, refine prompt, or check AI output format."
                if self.manager.config.get("DEBUG_MODE", False):
                    safe_show_info(warning_msg)
                logger.warning(warning_msg)

        # 3. Populate all rows (generated and original) with data
        for i, field_map in enumerate(note_field_maps):
            gen_row, orig_row = i * 2, i * 2 + 1
            progress_item = self.table.item(gen_row, 0)
            if not progress_item:
                continue

            note_id = progress_item.data(Qt.ItemDataRole.UserRole)
            note = mw.col.get_note(note_id)

            # Ensure the 'Original' label spans the new column count correctly
            self.table.setSpan(orig_row, 0, 1, 2)

            for col_idx, field_name in enumerate(self.auto_detect_fields):
                target_col = 2 + col_idx
                
                # Use mapped field name if available
                mapped_field = field_mapping.get(field_name, field_name) if field_mapping else field_name
                
                # Only populate if field exists in note (or we have mapping)
                should_populate = mapped_field in note or (field_name in field_map and field_name not in skipped_fields)
                
                if should_populate:
                    # Populate generated row with parsed content
                    content = field_map.get(field_name, "")
                    self.table.setItem(gen_row, target_col, QTableWidgetItem(content))

                    # Populate original row with content from the note
                    original_content = note[mapped_field] if mapped_field in note else ""
                    self.table.setItem(orig_row, target_col, QTableWidgetItem(original_content))
                else:
                    # Clear the cell
                    self.table.setItem(gen_row, target_col, QTableWidgetItem(""))
                    self.table.setItem(orig_row, target_col, QTableWidgetItem(""))

            # 4. Conditionally save the new content to the Anki note
            if save_to_notes:
                save_count = 0
                skip_count = 0
                for field_name, content in field_map.items():
                    mapped_field = field_mapping.get(field_name, field_name) if field_mapping else field_name
                    if mapped_field in note:
                        # Apply append logic if append mode is enabled
                        if self.append_checkbox.isChecked():
                            original_text = note[mapped_field]
                            note[mapped_field] = (original_text + "\n\n--- AI Generated ---\n" + content) if original_text else content
                        else:
                            note[mapped_field] = content
                        save_count += 1
                    else:
                        skip_count += 1
                        if field_name not in skipped_fields:
                            logger.info(f"Skipped '{field_name}'—no matching note field.")
                
                try:
                    if save_count > 0:
                        mw.col.update_note(note)
                        logger.info(f"Auto-saved {save_count} fields for note {note_id} (skipped {skip_count})")
                except Exception as e:
                    logger.exception(f"Error auto-saving multi-field note {note_id}: {e}")
                    
                # Add warning for missing fields
                if skip_count > 0 and self.manager.config.get("DEBUG_MODE", False):
                    missing_fields = [f for f in field_map.keys() if field_mapping.get(f, f) not in note]
                    if missing_fields:
                        safe_show_info(f"Note {note_id}: Fields not in note model: {', '.join(missing_fields)}. Content skipped unless mapped.")


    def import_fields_to_prompt(self):
        """Copy formatted field list to clipboard and insert into prompt at cursor position."""
        if not self.notes:
            safe_show_info("No notes available.")
            return
        
        first_note = self.notes[0]
        model = mw.col.models.get(first_note.mid)
        if not model:
            safe_show_info("Could not get note model.")
            return
        
        fields = mw.col.models.field_names(model)
        if not fields:
            safe_show_info("No fields found in note model.")
            return
        
        # Format fields for prompt as individual code blocks
        # Format: ```Field Name\nContent``` (one per field, separated by newlines)
        formatted_fields = "\n\n".join([f"```{field}\nContent```" for field in fields])
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(formatted_fields)
        
        # Insert at cursor position in prompt edit
        cursor = self.prompt_edit.textCursor()
        cursor.insertText(formatted_fields)
        
        safe_show_info(f"Copied {len(fields)} fields to clipboard and inserted into prompt as individual code blocks.")

    def update_note_type_status(self):
        """Update note type status label based on selected notes."""
        if not self.notes:
            self.note_type_status_label.setText("No notes selected.")
            return
        
        # Get unique note types
        model_names = set()
        model_ids = set()
        
        for note in self.notes:
            model = mw.col.models.get(note.mid)
            if model:
                model_ids.add(note.mid)
                model_names.add(model['name'])
        
        if len(model_ids) == 0:
            self.note_type_status_label.setText("Note type: Unknown")
        elif len(model_ids) == 1:
            model = mw.col.models.get(self.notes[0].mid)
            if model:
                self.note_type_status_label.setText(f"Note type of selected notes: {model['name']}")
            else:
                self.note_type_status_label.setText(f"Note type: ID {list(model_ids)[0]}")
        else:
            # Multiple note types - show warning
            if len(model_names) == 1:
                # Same name but different IDs (clones?)
                self.note_type_status_label.setText(f"Note type: {list(model_names)[0]} (multiple IDs - clones?)")
            else:
                self.note_type_status_label.setText(f"Multiple note types ({len(model_ids)} types). Select one note type for multi-field mode.")
    
    def inject_code_block_template(self, force=False):
        """Inject code block template into prompt based on format selection."""
        if not self.multi_field_mode:
            return
        
        format_type = "json" if self.format_combo and self.format_combo.currentText().startswith("JSON") else "code_blocks"
        self.manager.config["MULTI_FIELD_FORMAT_TYPE"] = format_type
        self.manager.save_config()
        
        # Only inject if structure checkbox is checked or force=True
        if (self.structure_checkbox and self.structure_checkbox.isChecked()) or force:
            if format_type == "json":
                template = "\n\nOutput as valid JSON: {\"Field1\": \"content\", \"Field2\": \"{example here}\"}. No extra text or HTML outside values."
            else:
                template = "\n\nTo fill multiple fields, use output in this format: ```Field Name\nGenerated Content to fill in the field```"
            
            current_text = self.prompt_edit.toPlainText()
            # Remove previous template if present
            if "Output as valid JSON:" in current_text or "To fill multiple fields" in current_text:
                # Simple removal of known patterns
                import re
                current_text = re.sub(r'\n\nOutput as valid JSON:.*?(?=\n\n|$)', '', current_text, flags=re.DOTALL)
                current_text = re.sub(r'\n\nTo fill multiple fields.*?(?=\n\n|$)', '', current_text, flags=re.DOTALL)
                current_text = current_text.rstrip()
            
            # Add new template
            new_text = current_text + template
            self.prompt_edit.setPlainText(new_text)
    
    def preview_single_note(self):
        """Enhanced preview with confidence visualization and mapping suggestions."""
        if not self.notes:
            safe_show_info("No notes available for testing.")
            return
        
        if not self.multi_field_mode:
            safe_show_info("Enable 'Auto-detect multiple output fields' first.")
            return
        
        # Get the first note
        note = self.notes[0]
        prompt_template = self.prompt_edit.toPlainText()
        
        # Format prompt with note fields
        try:
            formatted_prompt = prompt_template.format(**note)
        except KeyError as e:
            safe_show_info(f"Missing field {e} in note {note.id}")
            return
        
        # Generate AI response
        try:
            explanation = self.manager.generate_ai_response(formatted_prompt)
        except Exception as e:
            safe_show_info(f"Failed to generate AI response: {str(e)}")
            return
        
        if not self.parser:
            safe_show_info("Parser not initialized.")
            return
        
        # Parse with confidence
        fields, strategy, confidence = self.parser.parse(explanation, self.target_note_fields)
        
        # Create preview dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Preview Parse Results")
        dlg.setMinimumSize(500, 400)
        layout = QVBoxLayout(dlg)
        
        # Summary info
        summary = QLabel(f"<b>Strategy:</b> {strategy} | <b>Confidence:</b> {confidence:.2f} | <b>Fields Found:</b> {len(fields)}")
        layout.addWidget(summary)
        
        # Field mapping preview
        mapping_label = QLabel("<b>Field Mapping:</b>")
        layout.addWidget(mapping_label)
        
        if fields:
            # Create table for field mapping
            table = QTableWidget(len(fields), 3)
            table.setHorizontalHeaderLabels(["AI Field", "Suggested Note Field", "Content Preview"])
            table.horizontalHeader().setStretchLastSection(True)
            
            row = 0
            for ai_field, content in fields.items():
                # Suggest mapping
                suggested = self.parser.suggest_mappings([ai_field], self.target_note_fields).get(ai_field, ai_field)
                
                table.setItem(row, 0, QTableWidgetItem(ai_field))
                table.setItem(row, 1, QTableWidgetItem(suggested))
                preview = content[:100] + "..." if len(content) > 100 else content
                table.setItem(row, 2, QTableWidgetItem(preview))
                
                # Color coding based on confidence using QColor
                if confidence > 0.8:
                    table.item(row, 0).setBackground(QColor(200, 255, 200))  # Light green
                elif confidence > 0.5:
                    table.item(row, 0).setBackground(QColor(255, 255, 200))  # Light yellow
                else:
                    table.item(row, 0).setBackground(QColor(255, 200, 200))  # Light red
                
                row += 1
            
            table.resizeColumnsToContents()
            layout.addWidget(table)
        else:
            layout.addWidget(QLabel("No fields detected."))
        
        # Raw output preview
        raw_label = QLabel("<b>Raw Output (first 500 chars):</b>")
        layout.addWidget(raw_label)
        raw_text = QTextEdit()
        raw_text.setPlainText(explanation[:500] + ("..." if len(explanation) > 500 else ""))
        raw_text.setMaximumHeight(100)
        raw_text.setReadOnly(True)
        layout.addWidget(raw_text)
        
        # Confidence indicator
        if confidence < 0.5:
            warning = QLabel(f"⚠️ Low confidence parse ({confidence:.2f}). Consider refining prompt or format.")
            warning.setStyleSheet("color: orange; font-weight: bold;")
            layout.addWidget(warning)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        
        dlg.exec()
    
    def parse_rows(self, all_rows=True):
        """Parse raw output for rows, with undo stack support."""
        if not self.multi_field_mode or not self.parser:
            safe_show_info("Multi-field mode not active.")
            return
        
        # Determine which rows to parse
        rows_to_parse = []
        if all_rows:
            rows_to_parse = list(range(0, self.table.rowCount(), 2))  # Generated rows
        else:
            selected_rows = [idx.row() for idx in self.table.selectionModel().selectedRows()]
            rows_to_parse = [r for r in selected_rows if r % 2 == 0]  # Only generated rows
        
        if not rows_to_parse:
            safe_show_info("No rows selected for parsing.")
            return
        
        total_parsed = 0
        for row in rows_to_parse:
            raw_item = self.table.item(row, 1)  # Raw output column
            if not raw_item:
                continue
            
            explanation = raw_item.text()
            if not explanation.strip():
                continue
            
            # Save current state to undo stack
            current_state = {}
            for col in range(2, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    current_state[col] = item.text()
            
            if current_state:
                self.undo_stack.append((row, current_state))
                self.undo_button.setEnabled(True)
            
            # Parse with current parser
            fields, strategy, confidence = self.parser.parse(explanation, self.target_note_fields)
            
            # Apply field mappings
            if self.mapping_combo and self.mapping_combo.currentText() == "Auto-Map (Fuzzy Match)":
                mappings = self.parser.suggest_mappings(list(fields.keys()), self.target_note_fields)
            else:
                mappings = {k: k for k in fields.keys()}  # 1:1 mapping
            
            # Update table cells
            for ai_field, content in fields.items():
                target_field = mappings.get(ai_field, ai_field)
                # Find column for this field
                for col in range(2, self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col)
                    if header and header.text() == target_field:
                        # Create or update cell
                        if self.table.item(row, col) is None:
                            self.table.setItem(row, col, QTableWidgetItem())
                        self.table.item(row, col).setText(content)
                        
                        # Apply confidence-based color coding using QColor
                        if confidence > 0.8:
                            self.table.item(row, col).setBackground(QColor(200, 255, 200))  # Light green
                            self.table.item(row, col).setToolTip(f"High confidence ({confidence:.2f}) - {strategy}")
                        elif confidence > 0.5:
                            self.table.item(row, col).setBackground(QColor(255, 255, 200))  # Light yellow
                            self.table.item(row, col).setToolTip(f"Medium confidence ({confidence:.2f}) - {strategy}")
                        else:
                            self.table.item(row, col).setBackground(QColor(255, 200, 200))  # Light red
                            self.table.item(row, col).setToolTip(f"Low confidence ({confidence:.2f}) - {strategy}")
                        break
            
            total_parsed += 1
        
        safe_show_info(f"Parsed {total_parsed} row(s).")
    
    def apply_mappings(self, mapping_text):
        """Apply field mappings based on combo selection."""
        if not self.multi_field_mode or not self.parser:
            return
        
        if mapping_text == "Manual Map...":
            # TODO: Implement manual mapping dialog
            safe_show_info("Manual mapping not yet implemented. Using auto-mapping.")
            return
        
        # Auto-mapping already handled in parse_rows
        # This just triggers re-parse of all rows with new mapping
        if self.table.rowCount() > 0:
            self.parse_rows(all_rows=True)
    
    def undo_last_parse(self):
        """Undo the last parse operation."""
        if not self.undo_stack:
            return
        
        row, old_state = self.undo_stack.pop()
        
        # Restore old state
        for col, text in old_state.items():
            if col < self.table.columnCount():
                if self.table.item(row, col) is None:
                    self.table.setItem(row, col, QTableWidgetItem())
                self.table.item(row, col).setText(text)
                self.table.item(row, col).setBackground(QColor("white"))  # Clear color
        
        # Update undo button state
        self.undo_button.setEnabled(bool(self.undo_stack))
        
        safe_show_info(f"Undo applied to row {row//2 + 1}.")
    
    def update_start_processing_with_custom_instructions(self):
        """Helper method to update start_processing to use custom instructions."""
        # This method will be called to ensure start_processing uses custom instructions
        pass
    
    def parse_prompt_for_field_names(self):
        """Extract field names from prompt text and update checkbox states."""
        if not self.multi_field_mode:
            safe_show_info("Enable multi-field mode first.")
            return
        
        prompt_text = self.prompt_edit.toPlainText()
        if not prompt_text.strip():
            safe_show_info("Prompt is empty.")
            return
        
        import re
        
        # Extract field names from code blocks: ```FieldName\n
        code_block_pattern = r"```\s*([^`\n]+?)\s*\n"
        code_block_fields = re.findall(code_block_pattern, prompt_text, re.DOTALL)
        
        # Extract field names from plain text lines that look like field names
        # Look for lines that are not full sentences (no ending punctuation, not too long)
        plain_text_fields = []
        lines = prompt_text.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines, lines with code block markers, lines that are too long (>100 chars)
            if not line or '```' in line or len(line) > 100:
                continue
            # Look for lines that appear to be field names (capitalized, not ending with punctuation)
            if (line[0].isupper() if line else False) and not line.endswith(('.', '!', '?', ':', ';', ',')):
                # Check if it looks like a sentence (contains common sentence words)
                sentence_indicators = [' the ', ' a ', ' an ', ' is ', ' are ', ' was ', ' were ', ' in ', ' on ', ' at ']
                if not any(indicator in line.lower() for indicator in sentence_indicators):
                    plain_text_fields.append(line)
        
        # Combine and deduplicate field names
        extracted_fields = set()
        for field in code_block_fields:
            field = field.strip()
            if field:
                extracted_fields.add(field)
        for field in plain_text_fields:
            field = field.strip()
            if field:
                extracted_fields.add(field)
        
        if not extracted_fields:
            safe_show_info("No field names found in prompt. Try using 'Insert Field Template' button.")
            return
        
        # Filter extracted fields to only those that exist in note model
        fields_in_note_model = set(self.target_note_fields)  # These are fields from the note model
        fields_in_prompt_and_model = []
        fields_in_prompt_not_in_model = []
        
        for field in extracted_fields:
            if field in fields_in_note_model:
                fields_in_prompt_and_model.append(field)
            else:
                fields_in_prompt_not_in_model.append(field)
        
        # Show warning for fields in prompt but not in note model (once per session)
        if fields_in_prompt_not_in_model and not self.field_warning_shown:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Field Warning")
            msg.setText(f"The following fields in your prompt don't exist in the note model: {', '.join(sorted(fields_in_prompt_not_in_model))}.")
            msg.setInformativeText("These may be formatting examples. They will be ignored during processing.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            self.field_warning_shown = True
        
        # Update checkbox states (don't delete any checkboxes)
        # Check fields found in prompt AND in note model
        # Uncheck fields in note model but NOT found in prompt
        for field_name, checkbox in self.selected_field_checkboxes.items():
            if field_name in fields_in_prompt_and_model:
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)
        
        # Show success message
        if fields_in_prompt_and_model:
            safe_show_info(f"Found {len(fields_in_prompt_and_model)} field(s) in prompt that exist in note model: {', '.join(sorted(fields_in_prompt_and_model))}. Checkboxes updated.")
        else:
            safe_show_info("No fields from prompt exist in note model. All checkboxes unchecked.")

# ----------------------------------------------------------------
# ManagePromptsDialog
# ----------------------------------------------------------------
class ManagePromptsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Saved Prompts")
        self.setMinimumSize(600, 500)
        self.init_ui()
        self.load_prompts()

    def init_ui(self):
        # Main splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - prompt list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.prompt_list = QListWidget()
        self.prompt_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.prompt_list.itemSelectionChanged.connect(self.update_preview)
        left_layout.addWidget(QLabel("Saved Prompts:"))
        left_layout.addWidget(self.prompt_list)

        # Right panel - preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.preview_name = QLabel("Select a prompt to preview")
        self.preview_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.preview_name)

        self.preview_content = QTextEdit()
        self.preview_content.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        right_layout.addWidget(QLabel("Prompt Content:"))
        right_layout.addWidget(self.preview_content)

        self.field_info = QLabel()
        right_layout.addWidget(QLabel("Field Mapping:"))
        right_layout.addWidget(self.field_info)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 350])

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_changes)
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected)
        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_button)
        btn_layout.addWidget(self.delete_button)
        btn_layout.addWidget(self.cancel_button)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)
        main_layout.addLayout(btn_layout)

    def load_prompts(self):
        prompts = load_prompt_templates()
        self.prompt_list.clear()
        for title in sorted(prompts.keys()):
            self.prompt_list.addItem(title)

    def update_preview(self):
        selected = self.prompt_list.selectedItems()
        if not selected:
            self.preview_name.setText("Select a prompt to preview")
            self.preview_content.clear()
            self.field_info.clear()
            return

        prompt_name = selected[0].text()
        prompts = load_prompt_templates()
        prompt_settings = load_prompt_settings()

        self.preview_name.setText(f"Preview: {prompt_name}")
        self.preview_content.setPlainText(prompts.get(prompt_name, ""))

        # Show field mapping if exists
        field = prompt_settings.get(prompt_name, {}).get("outputField", "Not set")
        self.field_info.setText(f"Output field: {field}")

    def save_changes(self):
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            return

        prompt_name = selected_items[0].text()
        new_content = self.preview_content.toPlainText()

        prompts = load_prompt_templates()
        if prompt_name in prompts:
            prompts[prompt_name] = new_content
            save_prompt_templates(prompts)
            showInfo("Prompt changes saved successfully.")
        else:
            showInfo("Error: Prompt not found")

    def delete_selected(self):
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            return

        # Enhanced confirmation dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Confirm Deletion")

        if len(selected_items) == 1:
            prompt_name = selected_items[0].text()
            content = load_prompt_templates().get(prompt_name, "")
            msg.setText(f"Delete prompt '{prompt_name}'?")
            msg.setInformativeText(
                f"Prompt length: {len(content)} characters\n"
                "This action cannot be undone."
            )
        else:
            msg.setText(f"Delete {len(selected_items)} selected prompts?")
            msg.setInformativeText("This action cannot be undone.")

        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        prompts = load_prompt_templates()
        prompt_settings = load_prompt_settings()

        deleted_count = 0
        for item in selected_items:
            prompt_name = item.text()
            if prompt_name in prompts:
                del prompts[prompt_name]
                deleted_count += 1
            if prompt_name in prompt_settings:
                del prompt_settings[prompt_name]

        save_prompt_templates(prompts)
        save_prompt_settings(prompt_settings)
        self.load_prompts()
        self.update_preview()
        showInfo(f"Deleted {deleted_count} prompt(s).")


# ----------------------------------------------------------------
# AboutDialog
# ----------------------------------------------------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About OmniPrompt Anki")
        layout = QVBoxLayout(self)
        about_text = (
            "<h2>OmniPrompt Anki Add‑on</h2>"
            "<p>Version: 1.1.5</p>"
            "<p><a href='https://ankiweb.net/shared/review/1383162606'>Rate add-on on AnkiWeb</a></p>"
            "<p>For documentation, visit:</p>"
            "<p><a href='https://github.com/stanamosov/omniprompt-anki'>GitHub Repository</a></p>"
            "<p><a href='https://codeberg.org/stanamosov/omniprompt-anki'>Codeberg Repository</a></p>"
            "<p><b>User Guide:</b> See docs/user-guide.md in the add-on folder</p>"
            "<p>Credits: Stanislav Amosov</p>"
        )
        lbl = QLabel(about_text)
        lbl.setOpenExternalLinks(True)
        layout.addWidget(lbl)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)


# ----------------------------------------------------------------
# Tools Menu
# ----------------------------------------------------------------
def setup_omniprompt_menu():
    tools_menu = mw.form.menuTools
    omni_menu = QMenu("OmniPrompt", mw)

    settings_action = QAction("Settings", mw)
    settings_action.triggered.connect(
        lambda: omni_prompt_manager.show_settings_dialog()
    )
    omni_menu.addAction(settings_action)

    manage_action = QAction("Manage Prompts", mw)
    manage_action.triggered.connect(lambda: ManagePromptsDialog(mw).exec())
    omni_menu.addAction(manage_action)

    about_action = QAction("About", mw)
    about_action.triggered.connect(lambda: AboutDialog(mw).exec())
    omni_menu.addAction(about_action)

    tools_menu.addMenu(omni_menu)


# ----------------------------------------------------------------
# Browser Context
# ----------------------------------------------------------------
def on_browser_context_menu(browser: Browser, menu):
    note_ids = browser.selectedNotes()
    if note_ids:
        action = QAction("Update with OmniPrompt", browser)
        action.triggered.connect(lambda: update_notes_with_omniprompt(note_ids))
        menu.addAction(action)


gui_hooks.browser_will_show_context_menu.append(on_browser_context_menu)


def update_notes_with_omniprompt(note_ids: list):
    notes = [mw.col.get_note(nid) for nid in note_ids]
    dialog = UpdateOmniPromptDialog(notes, omni_prompt_manager, parent=mw)
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    dialog.show()


# ----------------------------------------------------------------
# Instantiate & Setup
# ----------------------------------------------------------------
omni_prompt_manager = OmniPromptManager()
setup_omniprompt_menu()


def shortcut_update_notes():
    logger.info("Global shortcut activated.")
    browser = mw.app.activeWindow()
    if isinstance(browser, Browser):
        note_ids = browser.selectedNotes()
        if note_ids:
            update_notes_with_omniprompt(note_ids)
        else:
            showInfo("No notes selected in the browser.")
    else:
        showInfo("Browser not available.")
    print("Shortcut activated!")


shortcut_ctrl = QShortcut(QKeySequence("Ctrl+Shift+O"), mw)
shortcut_ctrl.setContext(Qt.ShortcutContext.ApplicationShortcut)
shortcut_ctrl.activated.connect(shortcut_update_notes)

shortcut_meta = QShortcut(QKeySequence("Meta+Shift+O"), mw)
shortcut_meta.setContext(Qt.ShortcutContext.ApplicationShortcut)
shortcut_meta.activated.connect(shortcut_update_notes)