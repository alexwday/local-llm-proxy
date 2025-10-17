# Response Validation & Normalization

This document explains how the proxy validates and normalizes responses from your target LLM endpoint to ensure they match the OpenAI API format exactly.

## Overview

When you configure the proxy to forward requests to your actual LLM endpoint (by setting `usePlaceholderMode: false` in [src/config.ts](src/config.ts)), the proxy will:

1. **Forward** the request to your target endpoint
2. **Validate** the response format
3. **Normalize** the response to match OpenAI's exact format
4. **Return** the properly formatted response to the client

This ensures that **even if your LLM endpoint returns a slightly different format**, clients will always receive valid OpenAI-compatible responses.

## Configuration

### Enabling Target Forwarding

Edit [src/config.ts](src/config.ts):

```typescript
export const config = {
  targetEndpoint: 'https://your-llm-endpoint.com/v1',  // Your actual endpoint
  targetApiKey: 'your-api-key-here',                    // Optional: if required
  usePlaceholderMode: false,                             // Set to false to enable forwarding
};
```

## Validation Process

### Chat Completions (`/v1/chat/completions`)

The validator checks for:

#### Required Fields
- **`choices`** array must exist and not be empty
- Each choice must have either:
  - `message` object (non-streaming) with `role` and `content`
  - OR `delta` object (streaming)

#### Optional Fields (auto-filled if missing)
- **`id`**: Generated as `chatcmpl-{uuid}` if missing
- **`object`**: Set to `chat.completion` if missing
- **`created`**: Set to current timestamp if missing
- **`model`**: Uses requested model if missing
- **`system_fingerprint`**: Optional, passed through if present
- **`usage`**: Estimated as 0/0/0 if missing (with warning logged)

### Text Completions (`/v1/completions`)

Similar validation for the legacy endpoint:

#### Required Fields
- **`choices`** array must exist and not be empty
- Each choice must have `text` field

#### Optional Fields
- **`id`**: Generated as `cmpl-{uuid}` if missing
- **`object`**: Set to `text_completion`
- **`created`**: Current timestamp if missing
- **`model`**: From request if missing
- **`usage`**: Estimated if missing

## Normalization

### Handling Different Response Formats

The normalizer can handle various response formats from your target endpoint:

#### OpenAI-Compatible Responses
If your endpoint already returns OpenAI-format responses:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4",
  "choices": [...],
  "usage": {...}
}
```
✅ Passed through directly (fastest path)

#### Partial OpenAI Format
If some fields are missing:
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello!"
      }
    }
  ]
}
```
✅ Missing fields auto-filled with proper defaults

#### Legacy/Custom Formats
If using a different structure:
```json
{
  "choices": [
    {
      "text": "Hello!",  // Will be converted to message.content
      "index": 0
    }
  ]
}
```
✅ Transformed to OpenAI format

## Error Handling

### Target Endpoint Errors

If your target endpoint returns an error:
```json
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_error"
  }
}
```
✅ Forwarded to client in OpenAI error format

### Malformed Responses

If the response is invalid:
- Not a JSON object
- Missing `choices` array
- Empty `choices` array
- Invalid structure

The proxy will return a proper OpenAI error:
```json
{
  "error": {
    "message": "Target endpoint returned invalid response format",
    "type": "invalid_response_error",
    "param": "choices",
    "code": "missing_choices"
  }
}
```

### Connection Errors

If the proxy can't reach your endpoint:
```json
{
  "error": {
    "message": "Failed to connect to target endpoint: Connection refused",
    "type": "connection_error",
    "param": null,
    "code": "target_connection_failed"
  }
}
```

## Logging

All validation events are logged:

### Info Level
- `"Target endpoint returned OpenAI-compatible response"` - No normalization needed
- `"Normalizing target endpoint response to OpenAI format"` - Applying transformations
- `"Forwarding request to target: {url}"` - Request sent

### Warning Level
- `"Target endpoint did not provide usage information, estimating"` - Missing usage stats
- `"Choice missing both message and delta"` - Unusual response structure
- `"Target endpoint returned error"` - Error from target

### Error Level
- `"Failed to validate target response"` - Invalid response format
- `"Error forwarding request to target"` - Connection or other errors

## Testing Your Integration

### Step 1: Configure Target Endpoint

```typescript
// src/config.ts
export const config = {
  targetEndpoint: 'https://your-llm-api.com/v1',
  targetApiKey: 'sk-your-key-here',
  usePlaceholderMode: false,
};
```

### Step 2: Test with a Simple Request

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_PROXY_TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Step 3: Check Logs

Watch the server logs for:
- ✅ `"Forwarding request to target"`
- ✅ `"Target endpoint returned OpenAI-compatible response"` (best case)
- ⚠️ `"Normalizing target endpoint response"` (transformation applied)
- ❌ Any error messages

### Step 4: Verify Response Format

The response should match OpenAI's format exactly, regardless of what your target returns.

## Supported Target Endpoints

This validation layer works with:

### ✅ Fully Compatible
- OpenAI API
- Azure OpenAI
- OpenRouter
- Together AI
- Perplexity AI
- Any endpoint that returns OpenAI-format responses

### ✅ Partially Compatible (with normalization)
- Ollama (with appropriate format)
- LocalAI
- Text Generation WebUI (ooba)
- vLLM
- Custom LLM servers

### ⚠️ May Require Customization
- Anthropic Claude API (different message format)
- Google PaLM/Gemini (different structure)
- Cohere API (different response format)

For incompatible endpoints, you may need to add custom transformation logic in [src/validators/response-validator.ts](src/validators/response-validator.ts).

## Advanced: Custom Validation

If you need to handle a specific response format, you can modify the validator:

```typescript
// src/validators/response-validator.ts

// Add custom handling before standard validation
if (response.custom_format) {
  // Transform your custom format to OpenAI format
  response = transformCustomFormat(response);
}

// Then continue with standard validation
const validation = validateAndNormalizeChatResponse(response, originalRequest);
```

## Performance

- **OpenAI-compatible responses**: No overhead (direct pass-through)
- **Normalization required**: < 1ms additional latency
- **Validation errors**: Immediate error return, no retry

## Security

- Validation prevents malformed responses from reaching clients
- Error details from target endpoint are sanitized
- API keys are never logged or exposed in errors
- All validation errors are logged for debugging

## Summary

The response validation system ensures that:

1. ✅ Your clients always receive valid OpenAI-format responses
2. ✅ Missing fields are automatically filled with proper defaults
3. ✅ Errors are handled gracefully and consistently
4. ✅ You can use any LLM endpoint that returns reasonable JSON
5. ✅ All edge cases are logged for debugging

**You don't need to worry about whether your target endpoint is 100% OpenAI-compatible** - the proxy handles the differences automatically!
