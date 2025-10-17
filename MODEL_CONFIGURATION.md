# Model Configuration Guide

All model names are now configurable via environment variables in your `.env` file.

## Environment Variables

### `AVAILABLE_MODELS`
**Required:** No (defaults to standard GPT models)
**Format:** Comma-separated list of model IDs
**Purpose:** Defines which models are available and returned by `/v1/models` endpoint

**Example:**
```bash
AVAILABLE_MODELS=custom-gpt4,custom-gpt4-turbo,custom-llama,custom-mistral
```

This list will be returned when clients call `GET /v1/models`.

---

### `DEFAULT_MODEL`
**Required:** No (defaults to `gpt-4`)
**Format:** Single model ID
**Purpose:**
- Default model for placeholder responses
- Primary model for Claude Code CLI
- Fallback when request doesn't specify a model

**Example:**
```bash
DEFAULT_MODEL=custom-gpt4
```

---

### `DEFAULT_SMALL_MODEL`
**Required:** No (defaults to `gpt-3.5-turbo`)
**Format:** Single model ID
**Purpose:**
- Smaller/faster model for minor tasks
- Used by Claude Code for quick operations
- Fallback for text completions without specified model

**Example:**
```bash
DEFAULT_SMALL_MODEL=custom-gpt3.5
```

---

## Complete Example Configuration

```bash
# .env file

# Define all available models (returned by /v1/models)
AVAILABLE_MODELS=rbc-gpt4-advanced,rbc-gpt4-turbo,rbc-gpt35-fast,rbc-llama-70b

# Primary model for main tasks
DEFAULT_MODEL=rbc-gpt4-advanced

# Fast model for quick tasks
DEFAULT_SMALL_MODEL=rbc-gpt35-fast
```

---

## How Models Are Used

### 1. `/v1/models` Endpoint
Returns all models from `AVAILABLE_MODELS`:

```json
{
  "object": "list",
  "data": [
    {"id": "rbc-gpt4-advanced", "object": "model", ...},
    {"id": "rbc-gpt4-turbo", "object": "model", ...},
    {"id": "rbc-gpt35-fast", "object": "model", ...},
    {"id": "rbc-llama-70b", "object": "model", ...}
  ]
}
```

### 2. `/v1/models/{model_id}` Endpoint
Returns details for a specific model from `AVAILABLE_MODELS`:

```bash
GET /v1/models/rbc-gpt4-advanced
```

### 3. Chat Completions (Placeholder Mode)
When `USE_PLACEHOLDER_MODE=true`, uses `DEFAULT_MODEL` if request doesn't specify one:

```json
{
  "model": "rbc-gpt4-advanced",  // From DEFAULT_MODEL
  "choices": [...]
}
```

### 4. Text Completions (Placeholder Mode)
Uses `DEFAULT_SMALL_MODEL` if request doesn't specify one.

### 5. Claude Code CLI
The `launch-claude.py` script automatically sets:
- `ANTHROPIC_MODEL` → `DEFAULT_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL` → `DEFAULT_SMALL_MODEL`

---

## Migration from Hardcoded Models

**Before:** Models were hardcoded in `request_handler.py`
```python
MODELS = [
    {"id": "gpt-4", ...},
    {"id": "gpt-3.5-turbo", ...},
]
```

**After:** Models are loaded from environment variables
```python
self.models = self._build_models_list()  # Reads from config.available_models
```

---

## Testing with Custom Models

1. **Update your `.env`:**
   ```bash
   AVAILABLE_MODELS=my-custom-model-1,my-custom-model-2
   DEFAULT_MODEL=my-custom-model-1
   DEFAULT_SMALL_MODEL=my-custom-model-2
   ```

2. **Restart the proxy:**
   ```bash
   ./run-dev.sh
   ```

3. **Verify models are available:**
   ```bash
   curl http://localhost:3000/v1/models \
     -H "Authorization: Bearer YOUR_PROXY_TOKEN"
   ```

4. **Test with custom model:**
   ```bash
   curl http://localhost:3000/v1/chat/completions \
     -H "Authorization: Bearer YOUR_PROXY_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "my-custom-model-1",
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

---

## Notes

- **All model names are preserved:** When forwarding to `TARGET_ENDPOINT`, the proxy passes the exact model name from the request
- **Placeholder mode only:** `DEFAULT_MODEL` and `DEFAULT_SMALL_MODEL` only apply in placeholder mode
- **Claude Code compatibility:** Standard model names like `gpt-4` help Claude Code estimate costs correctly, but any name works
- **Validation:** The proxy does NOT validate that requested models exist in `AVAILABLE_MODELS` - it forwards all requests to the target

---

## Environment Variable Defaults

If you don't set these variables, the proxy uses these defaults:

```bash
AVAILABLE_MODELS=gpt-4,gpt-4-turbo,gpt-4o,gpt-4o-mini,gpt-3.5-turbo
DEFAULT_MODEL=gpt-4
DEFAULT_SMALL_MODEL=gpt-3.5-turbo
```

These defaults provide OpenAI-compatible behavior out of the box.
