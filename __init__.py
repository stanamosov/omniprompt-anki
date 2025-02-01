import requests
import logging
import os
import time
import socket
from aqt import mw
from aqt.qt import (
    QAction, QDialog, QVBoxLayout, QGroupBox, QComboBox, QLabel,
    QLineEdit, QDoubleValidator, QIntValidator, QFormLayout,
    QPushButton, QTextEdit, QHBoxLayout, QMessageBox, QProgressDialog, Qt
)
from aqt.browser import Browser
from anki.hooks import addHook
from aqt.utils import showInfo, getText
from PyQt6.QtCore import Qt
from logging.handlers import RotatingFileHandler
from PyQt6.QtGui import QTextOption
import json
from jsonschema import validate
import sys

AI_PROVIDERS = ["openai", "deepseek"]

DEFAULT_CONFIG = {
    "_version": 1.1,
    "AI_PROVIDER": "openai",
    "OPENAI_API_KEY": "",
    "DEEPSEEK_API_KEY": "",
    "API_ENDPOINT": "api.openai.com",
    "OPENAI_MODEL": "gpt-4o-mini",
    "DEEPSEEK_MODEL": "deepseek-chat",
    "OPENAI_TEMPERATURE": 0.2,
    "DEEPSEEK_TEMPERATURE": 0.2,
    "OPENAI_MAX_TOKENS": 200,
    "DEEPSEEK_MAX_TOKENS": 200,
    "note_type_id": None,
    "PROMPT": "Paste your prompt here.",
    "SELECTED_FIELDS": {
        "output_field": "Output"
    }
}

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "_version": {"type": "number"},
        "AI_PROVIDER": {"enum": AI_PROVIDERS},
        "OPENAI_API_KEY": {"type": "string"},
        "DEEPSEEK_API_KEY": {"type": "string"},
        "OPENAI_MODEL": {"type": "string"},
        "DEEPSEEK_MODEL": {"type": "string"},
        "OPENAI_TEMPERATURE": {"type": "number"},
        "DEEPSEEK_TEMPERATURE": {"type": "number"},
        "OPENAI_MAX_TOKENS": {"type": "integer"},
        "DEEPSEEK_MAX_TOKENS": {"type": "integer"},
        "note_type_id": {"type": ["number", "null"]},
        "PROMPT": {"type": "string"},
        "SELECTED_FIELDS": {
            "type": "object",
            "properties": {
                "output_field": {"type": "string"}
            }
        }
    },
    "required": ["AI_PROVIDER", "note_type_id"]
}

def _this_addon_dir():
    return os.path.dirname(__file__)

def load_prompt_templates():
    templates_path = os.path.join(_this_addon_dir(), "prompt_templates.txt")

def save_prompt_templates(templates):
    templates_path = os.path.join(_this_addon_dir(), "prompt_templates.txt")

def setup_logger():
    logger = logging.getLogger("OmniPromptAnki")
    logger.setLevel(logging.INFO)

    addon_dir = os.path.dirname(__file__) 
    log_file = os.path.join(addon_dir, "omnPrompt-anki.log")

    handler = SafeAnkiRotatingFileHandler(
        filename=log_file,
        mode='a',
        maxBytes=5*1024*1024,
        backupCount=2,
        encoding='utf-8',
        delay=True
    )

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger

class SafeAnkiRotatingFileHandler(RotatingFileHandler):
    """Custom handler for Anki environment compatibility"""
    def emit(self, record):
        try:
            super().emit(record)
        except Exception as e:
            print(f"Log write failed: {str(e)}")

    def shouldRollover(self, record):
        try:
            return super().shouldRollover(record)
        except Exception as e:
            print(f"Log rotation check failed: {str(e)}")
            return 0
            
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
        mw.addonManager.addonsFolder(),
        "omniprompt-anki",
        "omnPrompt-anki.log"
    )
    
    try:
        size = os.path.getsize(log_path)
        if size > 4.5 * 1024 * 1024:  # 4.5MB warning
            print("Log file approaching maximum size")
    except:
        pass

# Run check periodically (every 100 card updates)
addHook("reset", check_log_size)

# Initialize logger at module level
logger = setup_logger()
logger.setLevel(logging.INFO)

def load_prompt_templates():
    templates_path = os.path.join(os.path.dirname(__file__), "prompt_templates.txt")
    templates = {}

    if os.path.exists(templates_path):
        with open(templates_path, "r", encoding="utf-8") as file:
            current_key = None
            current_value = []
            for line in file:
                # Only remove trailing newlines, preserve all other whitespace
                line = line.rstrip('\n')  # Changed from line.rstrip()
                
                if line.startswith("[") and line.endswith("]"):
                    if current_key is not None:
                        templates[current_key] = "\n".join(current_value)
                    current_key = line[1:-1]
                    current_value = []
                else:
                    current_value.append(line)

            if current_key is not None:
                templates[current_key] = "\n".join(current_value)

    return templates

def save_prompt_templates(templates):
    templates_path = os.path.join(os.path.dirname(__file__), "prompt_templates.txt")

    # Optionally create the file if missing
    # or just open in "w" which creates it automatically.
    # But if the directory doesn’t exist, you need:
    os.makedirs(os.path.dirname(templates_path), exist_ok=True)

    with open(templates_path, "w", encoding="utf-8", newline="\n") as file:
        for key, value in sorted(templates.items()):
            # Preserve exact content without stripping
            file.write(f"[{key}]\n{value}\n\n")  # Removed .rstrip()

def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

class GPTGrammarExplainer:
    @property
    def addon_dir(self):
        return os.path.dirname(__file__)

    def __init__(self):
        self.logger = logging.getLogger("OmniPromptAnki")
        self.config = self.load_config()
        addHook("browser.setupMenus", self.on_browser_will_show)
        mw.addonManager.setConfigAction(__name__, self.show_settings_dialog)

    def save_config(self):
        try:
            validated = self.validate_config(self.config)
            # **Apply migrations** so that our config's _version is up-to-date
            migrated = self.migrate_config(validated)

            if migrated.get("_version") != DEFAULT_CONFIG["_version"]:
                # Only if you want to be strict about matching exactly the default
                # version, but typically you'd allow >= required version or
                # remove this check.
                self.emergency_log_cleanup()
                showInfo("Configuration version mismatch. Reset to defaults.")
                return

            mw.addonManager.writeConfig(__name__, migrated)
        except Exception as e:
            self.logger.error(f"Config save failed: {str(e)}")
            self.restore_config()

    def emergency_log_cleanup(self):
        """Safer log recovery with fallbacks"""
        try:
            # Clear existing handlers
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
                handler.close()
                
            # Reset log file
            log_path = os.path.join(self.addon_dir, "omnPrompt-anki.log")
            with open(log_path, 'w') as f:
                f.truncate()
                
            # Reinitialize logging
            new_handler = SafeAnkiRotatingFileHandler(
                filename=log_path,
                mode='a',
                maxBytes=5*1024*1024,
                backupCount=2,
                encoding='utf-8',
                delay=True
            )
            new_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(new_handler)
            
        except Exception as e:
            print(f"Emergency cleanup failed: {str(e)}")
            # Fallback to stdout logging
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def make_openai_request(self, prompt):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['OPENAI_API_KEY']}"
        }
        data = {
            "model": self.config["OPENAI_MODEL"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config["OPENAI_MAX_TOKENS"],
            "temperature": self.config["OPENAI_TEMPERATURE"]
        }
        return self.send_request(url, headers, data)

    def make_deepseek_request(self, prompt):
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config['DEEPSEEK_API_KEY']}"
        }
        data = {
            "model": self.config["DEEPSEEK_MODEL"],
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        return self.send_request(url, headers, data)

    def send_request(self, url, headers, data):
        """Generalized API request function with retry mechanism"""
        retries = 3
        backoff_factor = 2
        timeout = 20

        if not check_internet():
            logger.error("No internet connection.")
            showInfo("No internet connection. Please check your network and try again.")
            return "[Error: No internet]"

        for attempt in range(retries):
            try:
                safe_data = data.copy()
                safe_data["Authorization"] = "[REDACTED]"
                logger.info(f"Sending API request: {safe_data}")

                response = requests.post(url, headers=headers, json=data, timeout=timeout)
                response.raise_for_status()
                response_json = response.json()

                # ✅ Fix: Extract only the content from the first choice
                if "choices" in response_json and response_json["choices"]:
                    message = response_json["choices"][0].get("message", {}).get("content", "").strip()
                    if message:
                        logger.info(f"API response content: {message}")
                        return message  # ✅ Return only the extracted text
                    else:
                        logger.error(f"Empty response message: {response_json}")
                        return "[Error: Empty response message]"

                logger.error(f"Invalid API response structure: {response_json}")
                return "[Error: Unexpected response format]"

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout error. Retrying attempt {attempt + 1}/{retries}...")
                time.sleep(backoff_factor * (attempt + 1))
            except requests.exceptions.RequestException as e:
                logger.error(f"API error: {e}")
                showInfo(f"API error: {e}")
                return "[Error: API request failed]"

        return "[Error: API request failed after multiple attempts]"

    def generate_ai_response(self, prompt):
        provider = self.config.get("AI_PROVIDER", "openai")

        if provider == "openai":
            return self.make_openai_request(prompt)
        elif provider == "deepseek":
            if not self.config.get("DEEPSEEK_MODEL"):
                return "[Error: No DeepSeek model selected]"
            return self.make_deepseek_request(prompt)
        else:
            logger.error(f"Invalid AI provider: {provider}")
            return "[Error: Invalid AI provider]"

    def show_settings_dialog(self):
        dialog = SettingsDialog(mw)
        dialog.load_config(self.config)
        if dialog.exec():
            self.config = dialog.get_updated_config()
            self.save_config()

    def load_config(self):
        raw_config = mw.addonManager.getConfig(__name__) or {}
        validated = self.validate_config(raw_config)
        return self.migrate_config(validated)

    def migrate_config(self, config):
    # Start with default config
        migrated = DEFAULT_CONFIG.copy()
        
        # Merge existing config values
        migrated.update(config)
        
        # Version-specific migrations
        if migrated["_version"] < 1.1:
            migrated.setdefault("SELECTED_FIELDS", DEFAULT_CONFIG["SELECTED_FIELDS"])
            migrated["_version"] = 1.1
        
        return migrated

    def validate_config(self, config):
        try:
            validate(instance=config, schema=CONFIG_SCHEMA)
            return config
        except Exception as e:
            self.logger.error(f"Config validation error: {str(e)}")
            self.logger.info("Reverting to default configuration")
            return DEFAULT_CONFIG.copy()  # Return a fresh copy
        
    def backup_config(self):
        backup_path = os.path.join(self.addon_dir, "config_backup.json")
        with open(backup_path, "w") as f:
            json.dump(self.config, f)

    def restore_config(self):
        backup_path = os.path.join(self.addon_dir, "config_backup.json")
        if os.path.exists(backup_path):
            with open(backup_path, "r") as f:
                self.config = json.load(f)
            self.save_config()

    def save_config(self):
        try:
            validated = self.validate_config(self.config)
            validated = self.migrate_config(validated)  # ensure version is correct
            if validated.get("_version") != DEFAULT_CONFIG["_version"]:
                self.emergency_log_cleanup()
                showInfo("Configuration version mismatch. Reset to defaults.")
                return
                
            mw.addonManager.writeConfig(__name__, validated)
        except Exception as e:
            self.logger.error(f"Config save failed: {str(e)}")
            self.restore_config()

    def on_browser_will_show(self, browser):
        menu = browser.form.menuEdit
        self.action = QAction("Update cards with OmniPrompt", browser)
        self.action.triggered.connect(lambda: self.update_selected_notes(browser))
        menu.addAction(self.action)

    def update_selected_notes(self, browser):
        selected_notes = list(set(browser.selectedNotes()))
        note_type_id = self.config.get("note_type_id", None)

        if note_type_id is None:
            showInfo("No note type selected! Please configure the note type in settings.")
            return

        target_field, ok = getText(
            "Enter the field name where the generated data should be saved:",
            default=self.config.get("SELECTED_FIELDS", {}).get("output_field", "Output")
        )
        if not ok:
            return

        self.config["SELECTED_FIELDS"]["output_field"] = target_field

        progress = QProgressDialog("Updating cards with OmniPrompt...", "Cancel", 0, len(selected_notes), mw)
        progress.setWindowTitle("OmniPrompt Processing")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        processed_notes = 0
        modified_fields = 0
        error_count = 0
        MAX_ERROR_REPORTS = 5  # Limit error popups to prevent spamming

        for i, note_id in enumerate(selected_notes):
            if progress.wasCanceled():
                break

            progress.setValue(i)
            note = mw.col.get_note(note_id)

            if note.note_type()['id'] != note_type_id:
                continue

            try:
                # Generate AI response
                prompt = self.config["PROMPT"].format(**note)
                explanation = self.generate_ai_response(prompt)
                target_field = self.config["SELECTED_FIELDS"]["output_field"]

                # Update note field
                if explanation and isinstance(explanation, str):
                    if note[target_field] != explanation:
                        note[target_field] = explanation
                        mw.col.update_note(note)
                        modified_fields += 1
                else:
                    error_count += 1
                    if error_count <= MAX_ERROR_REPORTS:
                        showInfo(f"Invalid AI response for note {note.id}. Check logs.")
                    self.logger.error(f"Invalid explanation received: {explanation}")

                processed_notes += 1

                # Safe logging with emergency fallback
                try:
                    self.logger.info(f"Processed note {note_id}")
                except Exception as log_error:
                    print(f"Logging system failure: {log_error}")
                    self.emergency_log_cleanup()

            except KeyError as e:
                error_count += 1
                self.logger.error(f"Missing field {e} in note {note.id}")
                if error_count <= MAX_ERROR_REPORTS:
                    showInfo(f"Missing field {e} in note {note.id}")
            except Exception as e:
                error_count += 1
                self.logger.error(f"Critical error processing note {note.id}: {str(e)}")
                if error_count <= MAX_ERROR_REPORTS:
                    showInfo(f"Error processing note {note.id}")

        progress.setValue(len(selected_notes))
        
        # Final error summary
        if error_count > MAX_ERROR_REPORTS:
            showInfo(f"{error_count - MAX_ERROR_REPORTS} additional errors occurred. Check logs for details.")
        
        self.show_result(processed_notes, len(selected_notes), modified_fields)

    def show_result(self, processed, total, modified_fields):
        if processed:
            QMessageBox.information(
                mw, "Complete", 
                f"Updated {processed}/{total} notes.\nModified {modified_fields} fields."
            )
        else:
            QMessageBox.warning(mw, "Error", "No notes processed. Check fields/config.")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OmniPrompt Configuration")
        self.setMinimumWidth(500)
        self.config = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # AI Provider Selection
        provider_group = QGroupBox("AI Provider Selection")
        provider_layout = QVBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(AI_PROVIDERS)
        provider_layout.addWidget(QLabel("Select AI Provider:"))
        provider_layout.addWidget(self.provider_combo)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Note Type Selection
        type_group = QGroupBox("Note Type Selection")
        type_layout = QFormLayout()
        self.note_type_combo = QComboBox()
        type_layout.addRow("Note Type:", self.note_type_combo)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # API Settings
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter API key")
        api_layout.addRow("API Key:", self.api_key_input)
        
        self.model_combo = QComboBox()
        api_layout.addRow("Model:", self.model_combo)
        
        self.temperature_input = QLineEdit()
        self.temperature_input.setValidator(QDoubleValidator(0.0, 2.0, 2))
        api_layout.addRow("Temperature:", self.temperature_input)
        
        self.max_tokens_input = QLineEdit()
        self.max_tokens_input.setValidator(QIntValidator(100, 4000))
        api_layout.addRow("Max Tokens:", self.max_tokens_input)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Field Settings
        field_group = QGroupBox("Note Fields")
        field_layout = QFormLayout()
        
        self.explanation_field_combo = QComboBox()
        field_layout.addRow("Output Field:", self.explanation_field_combo)
        
        field_group.setLayout(field_layout)
        layout.addWidget(field_group)

        # Prompt Management
        prompt_group = QGroupBox("Prompt Templates")
        prompt_layout = QVBoxLayout()

        self.prompt_combo = QComboBox()
        self.prompt_combo.setEditable(True)
        prompt_layout.addWidget(QLabel("Saved Prompts:"))
        prompt_layout.addWidget(self.prompt_combo)

        self.save_prompt_button = QPushButton("Save Current Prompt")
        self.delete_prompt_button = QPushButton("Delete Selected Prompt")
        prompt_layout.addWidget(self.save_prompt_button)
        prompt_layout.addWidget(self.delete_prompt_button)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Use Shift+Enter for new lines")
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.prompt_edit.document().setDocumentMargin(12)
        prompt_layout.addWidget(QLabel("Prompt Template:"))
        prompt_layout.addWidget(self.prompt_edit)

        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Event Listeners
        self.note_type_combo.currentIndexChanged.connect(self.load_fields_for_selected_note_type)
        self.save_prompt_button.clicked.connect(self.save_prompt)
        self.delete_prompt_button.clicked.connect(self.delete_prompt)
        self.provider_combo.currentIndexChanged.connect(self.update_api_options)
        self.prompt_combo.currentIndexChanged.connect(self.update_prompt_from_template)

        # Load prompts
        self.load_prompts()

    def update_api_options(self):
        provider = self.provider_combo.currentText()
        self.model_combo.clear()

        if provider == "openai":
            self.api_key_input.setPlaceholderText("Enter OpenAI API Key")
            self.model_combo.addItems(["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"])
        elif provider == "deepseek":
            self.api_key_input.setPlaceholderText("Enter DeepSeek API Key")
            self.model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])

    def update_prompt_from_template(self):
        selected_template = self.prompt_combo.currentText()
        templates = load_prompt_templates()
        if selected_template in templates:
            self.prompt_edit.setPlainText(templates[selected_template])

    def load_config(self, config):
        self.config = config
        self.provider_combo.setCurrentText(self.config["AI_PROVIDER"])

        if self.config["AI_PROVIDER"] == "openai":
            self.api_key_input.setText(self.config.get("OPENAI_API_KEY", ""))
            self.model_combo.setCurrentText(self.config.get("OPENAI_MODEL", ""))
            self.temperature_input.setText(str(self.config.get("OPENAI_TEMPERATURE", 0.2)))
            self.max_tokens_input.setText(str(self.config.get("OPENAI_MAX_TOKENS", 200)))
        else:
            self.api_key_input.setText(self.config.get("DEEPSEEK_API_KEY", ""))
            self.model_combo.setCurrentText(self.config.get("DEEPSEEK_MODEL", ""))
            self.temperature_input.setText(str(self.config.get("DEEPSEEK_TEMPERATURE", 0.2)))
            self.max_tokens_input.setText(str(self.config.get("DEEPSEEK_MAX_TOKENS", 200)))

        # Load note types
        self.note_type_combo.clear()
        for model in mw.col.models.all():
            self.note_type_combo.addItem(model['name'], userData=model['id'])

        # Set selected note type
        current_id = self.config.get("note_type_id")
        if current_id:
            index = self.note_type_combo.findData(current_id)
            if index >= 0:
                self.note_type_combo.setCurrentIndex(index)

        # Load fields
        self.load_fields_for_selected_note_type()

        # Load prompts
        self.load_prompts()
        self.prompt_edit.setPlainText(self.config.get("PROMPT", ""))
        self.update_prompt_from_template()

    def load_fields_for_selected_note_type(self):
        model_id = self.note_type_combo.currentData()
        if model_id:
            note_type = mw.col.models.get(model_id)
            if note_type:
                fields = mw.col.models.field_names(note_type)
                self.explanation_field_combo.clear()
                self.explanation_field_combo.addItems(fields)

                current_output = self.config["SELECTED_FIELDS"].get("output_field", "")
                if current_output in fields:
                    self.explanation_field_combo.setCurrentText(current_output)

    def load_prompts(self):
        self.prompt_combo.clear()
        prompts = load_prompt_templates()
        for name in prompts.keys():
            self.prompt_combo.addItem(name)

    def save_prompt(self):
        name, ok = getText("Enter a name for the prompt:")
        if ok and name:
            prompts = load_prompt_templates()
            prompts[name] = self.prompt_edit.toPlainText()
            save_prompt_templates(prompts)
            self.prompt_combo.setCurrentText(name)
            self.load_prompts()

    def delete_prompt(self):
        name = self.prompt_combo.currentText()
        prompts = load_prompt_templates()
        if name in prompts:
            del prompts[name]
            save_prompt_templates(prompts)
            self.load_prompts()
            self.prompt_edit.clear()

    def get_updated_config(self):
        selected_note_type_index = self.note_type_combo.currentIndex()
        selected_note_type_id = self.note_type_combo.itemData(selected_note_type_index)

        return {
            "AI_PROVIDER": self.provider_combo.currentText(),
            "OPENAI_API_KEY": self.api_key_input.text() if self.provider_combo.currentText() == "openai" else "",
            "DEEPSEEK_API_KEY": self.api_key_input.text() if self.provider_combo.currentText() == "deepseek" else "",
            "OPENAI_MODEL": self.model_combo.currentText() if self.provider_combo.currentText() == "openai" else "",
            "DEEPSEEK_MODEL": self.model_combo.currentText() if self.provider_combo.currentText() == "deepseek" else "",
            "OPENAI_TEMPERATURE": float(self.temperature_input.text()) if self.provider_combo.currentText() == "openai" else self.config["OPENAI_TEMPERATURE"],
            "DEEPSEEK_TEMPERATURE": float(self.temperature_input.text()) if self.provider_combo.currentText() == "deepseek" else self.config["DEEPSEEK_TEMPERATURE"],
            "OPENAI_MAX_TOKENS": int(self.max_tokens_input.text()) if self.provider_combo.currentText() == "openai" else self.config["OPENAI_MAX_TOKENS"],
            "DEEPSEEK_MAX_TOKENS": int(self.max_tokens_input.text()) if self.provider_combo.currentText() == "deepseek" else self.config["DEEPSEEK_MAX_TOKENS"],
            "note_type_id": selected_note_type_id,
            "PROMPT": self.prompt_edit.toPlainText(),
            "SELECTED_FIELDS": {
                "output_field": self.explanation_field_combo.currentText()
            }
        }

gpt_grammar_explainer = GPTGrammarExplainer()
