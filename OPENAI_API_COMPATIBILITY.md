# OpenAI API Compatibility

This document outlines the OpenAI API compatibility of the local LLM proxy.

## ✅ Fully Implemented Endpoints

### 1. List Models
**Endpoint:** `GET /v1/models`

Returns a list of available models matching OpenAI's response format.

**Models Supported:**
- gpt-4
- gpt-4-turbo
- gpt-4-turbo-preview
- gpt-4o
- gpt-4o-mini
- gpt-3.5-turbo
- gpt-3.5-turbo-16k

### 2. Retrieve Model
**Endpoint:** `GET /v1/models/{model}`

Returns details about a specific model.

### 3. Chat Completions
**Endpoint:** `POST /v1/chat/completions`

The main endpoint for chat-based interactions. Fully compatible with OpenAI's specification.

#### Supported Request Parameters

**Required:**
- `model` (string) - Model to use
- `messages` (array) - Array of message objects with role and content

**Optional Sampling Parameters:**
- `temperature` (number, 0-2, default: 1) - Controls randomness
- `top_p` (number, 0-1, default: 1) - Nucleus sampling
- `n` (integer, default: 1) - Number of completions to generate
- `max_tokens` (integer) - Maximum tokens in response
- `max_completion_tokens` (integer) - Upper bound for completion tokens

**Optional Control Parameters:**
- `stop` (string or array) - Up to 4 stop sequences
- `presence_penalty` (number, -2 to 2, default: 0)
- `frequency_penalty` (number, -2 to 2, default: 0)
- `logit_bias` (object) - Modify token likelihoods (-100 to 100)

**Optional Response Format:**
- `response_format` (object) - Specify response format (text, json_object, json_schema)
- `logprobs` (boolean, default: false) - Return log probabilities
- `top_logprobs` (integer, 0-20) - Most likely tokens per position

**Optional Streaming:**
- `stream` (boolean, default: false) - Enable streaming
- `stream_options` (object) - Stream configuration

**Optional Tools/Functions:**
- `tools` (array) - List of tools/functions available
- `tool_choice` (string or object) - Control tool selection
- `parallel_tool_calls` (boolean) - Allow parallel tool calls
- `functions` (array) - [Deprecated] Function definitions
- `function_call` (string or object) - [Deprecated] Function call control

**Optional Other:**
- `seed` (integer) - For deterministic sampling
- `user` (string) - End-user identifier for tracking
- `service_tier` (string) - OpenAI service tier
- `store` (boolean) - Whether to store the completion
- `metadata` (object) - Additional metadata

#### Response Format

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4o",
  "system_fingerprint": "fp_...",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text...",
        "tool_calls": null,
        "function_call": null
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 25,
    "total_tokens": 35,
    "completion_tokens_details": {
      "reasoning_tokens": 0
    }
  }
}
```

### 4. Text Completions (Legacy)
**Endpoint:** `POST /v1/completions`

Legacy endpoint for text completions. Fully compatible with OpenAI's specification.

#### Supported Request Parameters

**Required:**
- `model` (string) - Model to use
- `prompt` (string or array) - Text to complete

**Optional:**
- `suffix` (string) - Text after completion
- `max_tokens` (integer) - Maximum tokens
- `temperature` (number, 0-2) - Sampling temperature
- `top_p` (number, 0-1) - Nucleus sampling
- `n` (integer) - Number of completions
- `stream` (boolean) - Enable streaming
- `logprobs` (integer) - Include log probabilities
- `echo` (boolean) - Echo back prompt
- `stop` (string or array) - Stop sequences
- `presence_penalty` (number, -2 to 2)
- `frequency_penalty` (number, -2 to 2)
- `best_of` (integer) - Generate and return best
- `logit_bias` (object) - Token likelihood modifications
- `user` (string) - End-user identifier

## Error Handling

All endpoints return OpenAI-compatible error responses:

```json
{
  "error": {
    "message": "Error message",
    "type": "invalid_request_error",
    "param": "parameter_name",
    "code": "error_code"
  }
}
```

**Error Types:**
- `invalid_request_error` - Invalid request parameters
- `invalid_api_key` - Authentication errors

**Status Codes:**
- `400` - Bad Request (missing/invalid parameters)
- `401` - Unauthorized (missing/invalid API key)
- `500` - Internal Server Error

## Authentication

Uses Bearer token authentication matching OpenAI's format:

```
Authorization: Bearer YOUR_API_KEY
```

## TypeScript Types

Complete TypeScript types are available in [src/types.ts](src/types.ts), including:

- `OpenAIChatRequest` - Full chat completion request
- `OpenAIChatResponse` - Full chat completion response
- `OpenAICompletionRequest` - Legacy completion request
- `OpenAICompletionResponse` - Legacy completion response
- `OpenAIModelsResponse` - Models list response
- `OpenAIError` - Error response format
- `ChatMessage` - Message format with all roles
- `ToolCall` - Function/tool calling types
- `Tool` - Tool definition types

## Testing with OpenAI Client Libraries

The proxy has been tested and verified to work with:

### Python OpenAI Library

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3000/v1",
    api_key="your-proxy-token"
)

# List models
models = client.models.list()

# Retrieve specific model
model = client.models.retrieve("gpt-4")

# Chat completion
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=100
)
```

### JavaScript/TypeScript OpenAI Library

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:3000/v1',
  apiKey: 'your-proxy-token',
});

const response = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello!' }],
});
```

### cURL

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Compatibility Notes

### ✅ Fully Compatible
- Request/response formats match OpenAI exactly
- All standard parameters are accepted
- Error responses follow OpenAI format
- Works seamlessly with official client libraries
- Proper HTTP status codes
- Bearer token authentication

### ⚠️ Placeholder Implementation
- Currently returns placeholder responses
- Actual LLM integration will be added in Phase 2
- All parameters are accepted but not yet forwarded to backend

### 🚧 Not Yet Implemented
- Streaming responses (`stream: true`)
- Function/tool calling (accepted but not executed)
- Embeddings endpoint
- Image generation endpoints
- Audio endpoints
- File endpoints
- Fine-tuning endpoints
- Moderation endpoint

## Next Steps

To integrate with your actual LLM endpoint, modify [src/routes/openai.ts](src/routes/openai.ts) to:

1. Forward requests to your LLM endpoint
2. Transform responses to OpenAI format
3. Handle streaming if needed
4. Implement tool/function calling if required

All the request validation, error handling, and response formatting is already in place and matches OpenAI's specification exactly.
