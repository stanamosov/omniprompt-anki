# OmniPrompt Anki User Guide — v1.1.5

## Table of Contents
- [Installation](#installation)
  - [From AnkiWeb](#from-ankiweb)
  - [From Codeberg or GitHub](#from-codeberg-or-github)
- [Setup](#setup)
- [User Interface](#user-interface)
  - [Find Add-on Settings](#find-add-on-settings)
  - [Settings Menu](#settings-menu)
  - [Advanced Settings](#advanced-settings)
  - [Manage Saved Prompts](#manage-saved-prompts)
  - [Update with OmniPrompt](#update-with-omniprompt)
  - [Batch Processing Window](#batch-processing-window)
- [How It Works](#how-it-works)
- [Core Features](#core-features)
  - [Single-field Processing](#single-field-processing)
  - [Multi-field Output](#multi-field-output)
  - [Batch Processing](#batch-processing)
  - [Filter Mode](#filter-mode)
  - [Debug Mode](#debug-mode)
  - [Auto-send to Card](#auto-send-to-card)
- [AI Providers & Configuration](#ai-providers--configuration)
  - [OpenAI](#openai)
  - [DeepSeek](#deepseek)
  - [Google Gemini](#google-gemini)
  - [Anthropic (Claude)](#anthropic-claude)
  - [xAI (Grok)](#xai-grok)
  - [Ollama (Local)](#ollama-local)
  - [LM Studio (Local)](#lm-studio-local)
  - [OpenAI API Version Selector](#openai-api-version-selector)
  - [GPT-5.4 Specific Settings](#gpt-54-specific-settings)
- [Custom Models per Provider](#custom-models-per-provider)
- [Connection Testing](#connection-testing)
- [Prompt Templates & Management](#prompt-templates--management)
  - [Using Field Placeholders](#using-field-placeholders)
  - [Saving and Loading Prompts](#saving-and-loading-prompts)
  - [Multi-field Prompt Example](#multi-field-prompt-example)
- [Advanced Settings](#advanced-settings-1)
  - [API Delay](#api-delay)
  - [Timeout](#timeout)
  - [Debug Mode / Filter Mode](#debug-mode--filter-mode)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting & Logging](#troubleshooting--logging)
- [Examples of Use](#examples-of-use)
  - [Language Translation](#language-translation)
  - [Word Definitions](#word-definitions)
  - [Synonyms & Vocabulary Expansion](#synonyms--vocabulary-expansion)
  - [Text Formatting & Cleanup](#text-formatting--cleanup)
  - [Example Sentence Generation](#example-sentence-generation)
  - [Grammar & Verb Conjugation](#grammar--verb-conjugation)
  - [Medical Term Explanation](#medical-term-explanation)
- [Customizing Prompts with Note Fields](#customizing-prompts-with-note-fields)
- [Frequently Asked Questions](#frequently-asked-questions)

---

## Installation

### From AnkiWeb
1. Open Anki and go to **Tools → Add-ons → Get Add-ons**.
2. Enter the add-on code:
   ```
   1383162606
   ```
3. Restart Anki to complete the installation.

### From Codeberg or GitHub
#### 1️⃣ Clone the Repository
```sh
# Codeberg
git clone https://codeberg.org/stanamosov/omniprompt-anki.git

# GitHub
git clone https://github.com/stanamosov/omniprompt-anki.git
```
#### 2️⃣ Install the Add-on
1. Navigate to your Anki add-ons directory:
   - **macOS/Linux**: `~/.local/share/Anki2/addons21/`
   - **Windows**: `%APPDATA%\Anki2\addons21\`
2. Copy the `omniprompt-anki` folder into the add-ons directory.
3. Restart Anki.

---

## Setup
1. Open Anki and go to **Tools → OmniPrompt-Anki → Settings**.
2. Select your AI provider and enter your **API key** (if required).
3. Choose the **AI model** appropriate for your provider.
4. Configure **Temperature** and **Max Tokens** as needed.
5. Click **Save** and start using the add-on!

---

## User Interface

### Find Add-on Settings
Open Anki and go to **Tools → OmniPrompt-Anki → Settings**.
![Settings](user_interface/settings.jpg)

### Settings Menu
Configure API Provider (OpenAI, Gemini, etc.), API Key, Model, Temperature, Max Tokens, and manage custom models with **+** / **−** buttons. Test connection to your provider. Configure provider-specific options (OpenAI API version, reasoning effort, DeepSeek streaming).
![Settings](user_interface/settings.jpg)

The settings dialog now includes:
- **Model +/− buttons**: Add/remove custom model names for any provider
- **URL/Base URL field**: Edit the API endpoint URL (for cloud providers) or base URL (for local providers)
- **Test Connection button**: Verify API connectivity and fetch available models for Ollama/LM Studio
- **OpenAI-specific settings** (shown only for OpenAI): API Version selector, Reasoning Effort, Verbosity
- **DeepSeek-specific settings** (shown only for DeepSeek): Streaming checkbox

### Advanced Settings
Click **Advanced Settings** in the configuration window to modify API Delay, Timeout, Debug Mode, and Filter Mode.
![Advanced Settings](user_interface/advanced_settings.jpg)

### Manage Saved Prompts
View, edit, or delete saved prompt presets in a dedicated UI panel.
![Manage Prompts](user_interface/prompts_menu.jpg)

### Update with OmniPrompt
Right-click in the Anki Browser to update notes using AI.
![Context Menu](user_interface/context_menu.jpg)

### Batch Processing Window
Track generation progress and view original content alongside AI output during bulk updates. For batches larger than 10 notes, a **global progress bar** appears at the top of the table for high-level progress tracking.
![Batch Processing](user_interface/main_ui.jpg)

---

## How It Works
1. **Select notes** in the Anki Browser.
2. **Right-click → Update with OmniPrompt**.
3. **Pick the output field** where AI-generated responses will be stored.
4. **Choose a prompt** from templates and customize it using placeholders from note fields.
5. **Click Start** – AI generates and saves content into the selected notes.
6. **Edit manually** if needed before finalizing, click "Send Data To Card" to save your edits.
7. **Enjoy enhanced flashcards!**

---

## Core Features

### Single-field Processing
The standard workflow where AI output is saved to a single field. You can choose to append to existing content or replace it.

### Multi-field Output
OmniPrompt can parse AI responses into multiple fields automatically with **confidence scoring** and **smart field mapping**. Enable "Multi-field output" in the Update with OmniPrompt dialog.

**How to Use Multi-field Mode:**

1. **Enable multi-field mode**: Check "Multi-field output" in the Update with OmniPrompt dialog
2. **Configure fields**: Switch to the **"Field Configuration"** tab to select which fields to update. Use **Select All / Select None** buttons to quickly toggle field selection
3. **Parse prompt fields**: Click **"Parse Prompt"** to automatically extract field names from your prompt text and update checkbox selection
4. **Craft your prompt**: Include field placeholders (e.g., `{Front}`) and specify the desired output format. Use the **"Insert Field Template"** button to quickly insert all available field names as code block templates
5. **Start processing**: As each note completes, the AI response is **auto-parsed** into selected fields with confidence-based color coding:
   - 🟢 Green background = High confidence (>80%)
   - 🟡 Yellow background = Medium confidence (>50%)
   - 🔴 Red background = Low confidence (≤50%)
6. **Review and save**: Check the parsed fields, make edits if needed, then save to notes

**Supported Output Format:**
- **Code blocks**: `` `FieldName\nContent` `` (recommended — works with all AI models)

**In-App Guidance:**
- **Format reminder label**: Shows the expected code block format at the top of the Field Configuration tab
- **Note type status**: Displays the note type of selected notes at the top of the dialog
- **Multiple note type detection**: If notes of different types are selected, a filtering dialog offers to restrict processing to the most common type

**Advanced Multi-field Features:**
- **Confidence scoring**: Each parsed field gets a confidence score (0.0–1.0) based on match quality with available note fields
- **Auto-parsing**: Results are automatically parsed into field columns as each note completes
- **Field mismatch handling**: When parsed fields don't match note fields, a dialog offers:
  - **Auto-map similar names** — fuzzy matching to find closest field names
  - **Save only exact matches** — skip unmatched fields
  - **Manual map** — manually map fields (future enhancement)
- **Append mode**: When enabled (via the "Append Output" checkbox even in multi-field mode), AI content is appended to existing field content with a separator
- **Parse prompt button**: Extracts field names from ```` ```FieldName\n ``` `` patterns in your prompt and auto-selects matching checkboxes
- **Global progress bar**: Appears automatically when processing more than 10 notes

**Tips for Best Results:**
- Include explicit format instructions in your prompt (e.g., "Output each section in a code block with the field name")
- Test with a single note first before processing large batches
- Use the "Insert Field Template" button to get the exact code block format into your prompt

### Batch Processing
Process multiple notes simultaneously with real-time progress tracking. Each note's status is displayed in the progress table. For batches with more than 10 notes, a **global progress bar** appears at the top for overall progress visibility.

### Filter Mode
When enabled, OmniPrompt will skip notes where the output field is already filled. This prevents overwriting existing content.

### Debug Mode
When enabled, shows processing popups and detailed feedback. Disable for cleaner operation during batch processing.

### Auto-send to Card
When enabled, generated content is automatically saved to the card without requiring manual confirmation. Disable if you prefer to review and edit content before saving.

---

## AI Providers & Configuration

### OpenAI
- **API Key**: Required from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Supported Models**: `gpt-4o-mini`, `gpt-3.5-turbo`, `gpt-4o`, `gpt-5.4`, `gpt-5.4-pro`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5`, `o3-mini`, `o1-mini`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- **Custom Models**: Add any OpenAI-compatible model via the "+" button in settings
- **API Version**: Choose between modern (GPT-5 Responses API), legacy (Chat Completions), or auto-detect

### DeepSeek
- **API Key**: Required from [DeepSeek Platform](https://platform.deepseek.com/api_keys)
- **Supported Models**: `deepseek-chat`, `deepseek-reasoner`
- **Streaming**: Optional real-time response streaming (enable in provider settings)

### Google Gemini
- **API Key**: Required from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Supported Models**: `gemini-pro`, `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.0-flash-thinking`

### Anthropic (Claude)
- **API Key**: Required from [Anthropic Console](https://console.anthropic.com/)
- **Supported Models**: `claude-opus-4-latest`, `claude-sonnet-4-latest`, `claude-haiku-3.5-latest`

### xAI (Grok)
- **API Key**: Required from [xAI Platform](https://console.x.ai/)
- **Supported Models**: `grok-3-latest`, `grok-3-mini-latest`

### Ollama (Local)
- **No API Key Required**
- **Base URL**: `http://localhost:11434` (default, editable)
- **Supported Models**: Any Ollama model (`llama3.2`, `llama3.1`, `llama2`, `mistral`, `mixtral`, `codellama`, `phi`, `gemma`, `qwen2.5`, etc.)
- **Requirement**: Ollama must be running locally
- **Connection Testing**: Use "Test Connection" to verify connectivity and **fetch available models** directly from your Ollama instance

### LM Studio (Local)
- **No API Key Required**
- **Base URL**: `http://localhost:1234` (default, editable)
- **Supported Models**: Any model loaded in LM Studio
- **Requirement**: LM Studio must be running with server enabled
- **Connection Testing**: Use "Test Connection" to verify connectivity and **fetch available models** from your LM Studio instance

### OpenAI API Version Selector
When using OpenAI as your provider, you can choose which API version to use via a dropdown in the provider settings:

| Option | Description |
|--------|-------------|
| **modern** | Use the new **Responses API** (required for GPT-5 / GPT-5.4 models) |
| **legacy** | Use the classic **Chat Completions API** (for GPT-4 and older models) |
| **auto** | Automatically select based on the model name (recommended) |

The **auto** mode detects GPT-5 models (any model containing `gpt-5`, `gpt-5.4`, etc.) and uses the modern API, while all other models use the legacy Chat Completions API.

### GPT-5.4 Specific Settings
For GPT-5.4 models (`gpt-5.4`, `gpt-5.4-pro`, `gpt-5.4-mini`, `gpt-5.4-nano`), additional settings are available:

- **Reasoning Effort**: Controls how much "thinking" the model does before responding:
  - `none` — Standard response, no extra reasoning
  - `low` — Minimal reasoning
  - `medium` — Moderate reasoning
  - `high` — Extensive reasoning
  - `xhigh` — Maximum reasoning

- **Verbosity**: Controls response detail level:
  - `low` — Concise responses
  - `medium` — Balanced (default)
  - `high` — Detailed responses

> **Note**: GPT-5.4 models do **not** support the `temperature` parameter. Verbosity and reasoning effort replace it for controlling output. Temperature is sent to the model only when using the legacy Chat Completions API.

---

## Custom Models per Provider
You can add and remove custom model names for any AI provider directly from the Settings dialog:

1. Select your desired **AI Provider**
2. In the **Model** field, type or select a model name
3. Click the **+** button to add it to the provider's custom models list
4. Click the **−** button to remove it from custom models

Custom models appear alongside the default model list in the dropdown and are persisted across sessions.

> **Tip**: Use "Test Connection" with Ollama/LM Studio to automatically fetch and populate available models from your local instance.

---

## Connection Testing
OmniPrompt provides a **Test Connection** button for every provider, accessible from the Settings dialog:

1. Open **Tools → OmniPrompt-Anki → Settings**
2. Select your AI provider
3. Click **Test Connection** in the Provider Settings section
4. View the result — green checkmark for success, red cross for failure

**What happens during testing:**
- **Cloud providers** (OpenAI, DeepSeek, Gemini, Anthropic, xAI): A minimal API request is made to verify your API key is valid
- **Local providers** (Ollama, LM Studio): The base URL is pinged to verify the service is running. On success, available models are **automatically fetched** and added to your model dropdown

---

## Prompt Templates & Management

### Using Field Placeholders
Use **any field** from your note type in prompts. Field names are **case-sensitive**. You can use **multiple fields** in your prompt and even use your **Output field** for input — this makes it possible to change formatting of existing fields!

**Example Using Multiple Fields**:
```
Generate a detailed explanation for "{Japanese Word}". Include this example: "{Sentence}".
```

### Saving and Loading Prompts
1. Create or modify a prompt in the "Update with OmniPrompt" dialog
2. Click "Save Current Prompt" to store it with a name
3. Saved prompts appear in the dropdown for quick selection
4. Use **Tools → OmniPrompt → Manage Prompts** to edit or delete saved prompts

### Multi-field Prompt Example
Here's an example prompt for generating content into multiple fields:

```
"{Simplified} ({Pinyin})" can be used in different ways, give 2-4 example sentences.
Follow this formatting, output in code blocks:

```Sentences_Hanyu
句子1<br/>句子2...
```
```Sentences_Pinyin
Jùzǐ1<br/>Jùzǐ2...
```
```Sentences_English
literal translation1<br/>literal translation2...
```

Try to use words that are similar in HSK level. Try to output fewer sentences if the word is simple/self explanatory. Include one complex sentence or colloquial slang.

Do not explain or provide additional output. Don't number or label the sentences.
```

This prompt will generate Chinese example sentences with Pinyin and English translations, automatically parsed into three separate fields.

---

## Advanced Settings

Access these settings via **Tools → OmniPrompt → Settings → Advanced Settings**.

### API Delay
Adds a short pause between consecutive requests to avoid rate limits. Recommended: 1-2 seconds for most providers.

### Timeout
Adjusts how long the add-on waits for each API request to finish. Increase for slower connections, complex queries, or larger token responses. Default: 30 seconds.

### Debug Mode / Filter Mode
- **Debug Mode**: Show/hide processing popups and informational messages. Helpful for troubleshooting, but can be disabled for cleaner batch processing.
- **Filter Mode**: When enabled, notes where the output field already contains content will be skipped. Useful for updating only empty fields without overwriting existing data.

---

## Keyboard Shortcuts

### Global Shortcut (Anki-wide)
| Shortcut | Action |
|----------|--------|
| **Ctrl+Shift+O** (Win/Linux) / **Cmd+Shift+O** (macOS) | Open the **Update with OmniPrompt** dialog from the browser |

### Dialog Shortcuts (inside "Update with OmniPrompt" window)
| Shortcut | Action | Equivalent Button |
|----------|--------|-------------------|
| **Ctrl+Return** | Start processing selected notes | Start |
| **Ctrl+S** | Save the current prompt | Save Current Prompt |
| **Ctrl+D** | Send data to the Anki cards | Send Data To Card |
| **Ctrl+I** | Insert field template at cursor position | Insert Field Template |
| **Ctrl+P** | Parse fields (Field Configuration tab) | Parse Fields |
| **Ctrl+Shift+P** | Parse prompt for field names | Parse Prompt |
| **Escape** | Stop processing | Stop |

> **💡 Tip:** The **Saved Prompts** dropdown can be navigated with the **Up/Down arrow keys** for quick prompt switching without a mouse.

A shortcut hint is also visible at the bottom of the dialog window for quick reference.

---

## Troubleshooting & Logging

OmniPrompt-Anki maintains a log file (**omniprompt_anki.log**) inside the add-ons folder to track API requests, responses, and potential errors. This helps with troubleshooting issues like API connection failures, timeouts, or unexpected responses. The log file is capped at **5MB**, with up to **two backups** to prevent excessive disk usage.

To access logs:
1. Open **Tools → OmniPrompt → Settings**
2. Click **View Log** to inspect recent activity

Common issues and solutions:

1. **API Connection Failed**
   - Check your internet connection
   - Verify API key is correct and has sufficient credits
   - Ensure the selected model is available for your account
   - Use the **Test Connection** button in Settings to diagnose

2. **Local Models Not Working (Ollama/LM Studio)**
   - Verify Ollama/LM Studio is running
   - Check base URL matches your local setup
   - Confirm model name is correct
   - Use **Test Connection** to diagnose and auto-fetch available models

3. **No Response from AI**
   - Increase timeout in Advanced Settings
   - Check log file for error details
   - Try a simpler prompt to test connectivity

4. **Field Placeholders Not Working**
   - Ensure field names match exactly (case-sensitive)
   - Check that notes have values in the referenced fields

5. **Multi-field Fields Not Parsing**
   - Verify your prompt outputs the correct code block format: `` `FieldName\nContent` ``
   - Try the "Insert Field Template" button to get the exact format
   - Check the **Raw Output** column to see what the AI actually returned
   - Use "Parse Fields" button to manually retry parsing

---

## Examples of Use

### Language Translation
**Prompt:**
```plaintext
Translate this French word "{French Word}" to English. Answer with translation only.
```

### Word Definitions
**Prompt:**
```plaintext
Explain this Polish word "{Polish Word}". Answer with definition only, do not add any other comments.
```

### Synonyms & Vocabulary Expansion
**Prompt:**
```plaintext
What are synonyms for this French word "{French Word}". Answer with a list of synonyms only.
```

### Text Formatting & Cleanup
**Prompt:**
```plaintext
Format this text "{Explanation}" in markdown. Answer with formatted text only, do not add any comments.
```

### Example Sentence Generation
**Prompt:**
```plaintext
Generate two example sentences for language learners at the B1-B2 level using the word "{Word}".
```

### Grammar & Verb Conjugation
**Prompt:**
```plaintext
What is the correct form of the French verb "{Verb}" in {Tense} for {Person}? Explain the conjugation rule.
```

### Medical Term Explanation
**Prompt:**
```plaintext
Explain the medical term "{Term}" in simple language. Include its symptoms, causes, and treatments.
```

---

## Customizing Prompts with Note Fields

You can reference any field from your note type using `{FieldName}` syntax. The add-on automatically replaces these placeholders with the actual field values before sending to the AI.

**Tips:**
- Field names are case-sensitive: `{Word}` ≠ `{word}`
- Use multiple fields in a single prompt
- You can reference the output field itself to reformat existing content
- For missing fields, the placeholder will remain unchanged (e.g., `{MissingField}`)

**Advanced Example:**
```
Create a comprehensive study note for "{Term}".

Include:
1. Definition: {Definition}
2. Examples: {Example1}, {Example2}
3. Related terms: {RelatedTerms}

Format the output as a markdown table comparing {Term} with {SimilarTerm}.
```

---

## Frequently Asked Questions

**Q: Can I use OmniPrompt without an internet connection?**
A: Yes, with local models (Ollama or LM Studio). You'll need to download models in advance.

**Q: How much does it cost to use?**
A: OmniPrompt itself is free. You pay only for API usage with cloud providers (OpenAI, Anthropic, etc.) according to their pricing. Local models are free.

**Q: Can I use multiple AI providers at once?**
A: You can switch between providers in settings, but only one provider is active at a time.

**Q: Is my data sent to AI providers?**
A: Yes, when using cloud providers. For local models (Ollama/LM Studio), data stays on your computer.

**Q: How do I update to the latest version?**
A: Via AnkiWeb (automatic updates) or manually update from Codeberg/GitHub.

**Q: Can I contribute new features or report bugs?**
A: Yes! See the [Contributing section](https://github.com/stanamosov/omniprompt-anki#-contributing) in the main README.

**Q: What's new in v1.1.5?**
A: Major improvements include: enhanced multi-field output with confidence scoring and auto-parsing, custom models per provider with +/- buttons, connection testing with model fetching for Ollama/LM Studio, OpenAI API version selector (modern/legacy/auto), GPT-5.4 reasoning effort and verbosity settings, note type consistency checking, field mismatch detection with auto-mapping, Parse Prompt button, and global progress bar for large batches.

---

*Need more help? Open an issue on [Codeberg](https://codeberg.org/stanamosov/omniprompt-anki) or [GitHub](https://github.com/stanamosov/omniprompt-anki).*
