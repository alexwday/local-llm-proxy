# Architecture Overview

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Application                   │
│          (Python/JavaScript/cURL with OpenAI library)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP Request (OpenAI Format)
                         │ Authorization: Bearer {proxy-token}
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Local LLM Proxy                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Gateway (Express)                    │  │
│  │  • Authentication (Bearer Token)                      │  │
│  │  • Request Validation                                 │  │
│  │  • Logging                                            │  │
│  └───────────────┬──────────────────────────────────────┘  │
│                  │                                           │
│      ┌──────────┴──────────┐                                │
│      │                     │                                │
│      ▼                     ▼                                │
│  ┌─────────────────┐  ┌──────────────────────┐             │
│  │  Placeholder    │  │  Target Forwarder    │             │
│  │  Mode           │  │  • HTTP Client       │             │
│  │  • Mock         │  │  • Request Proxy     │             │
│  │    Responses    │  │  • Response          │             │
│  └─────────────────┘  │    Validation        │             │
│                       │  • Normalization     │             │
│                       └──────┬───────────────┘             │
│                              │                               │
│                              │ HTTP Request                  │
│                              │ (OpenAI Format)               │
│                              ▼                               │
│                       ┌─────────────────────┐               │
│                       │  Response Validator │               │
│                       │  • Format Check     │               │
│                       │  • Field Validation │               │
│                       │  • Normalization    │               │
│                       │  • Error Handling   │               │
│                       └──────┬──────────────┘               │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │ OpenAI-Format Response
                               │
                               ▼
                    ┌────────────────────────┐
                    │   Target LLM Endpoint  │
                    │  (Your actual LLM API) │
                    └────────────────────────┘
```

## Request Flow

### 1. Client Request
```
Client → Local Proxy
```
- Client sends OpenAI-formatted request
- Must include `Authorization: Bearer {token}` header
- Request validated against OpenAI spec

### 2. Authentication
```
API Gateway → Token Verification
```
- Checks Bearer token against configured access token
- Returns 401 error if missing/invalid
- Logs all authentication attempts

### 3. Request Validation
```
Routes → Type Validation
```
- Validates required fields (model, messages, prompt)
- Checks parameter types and ranges
- Returns 400 error for invalid requests

### 4. Mode Selection
```
Routes → Placeholder vs. Forwarding
```

**Placeholder Mode** (`usePlaceholderMode: true`):
- Returns mock responses
- No external requests
- Useful for testing integration

**Forwarding Mode** (`usePlaceholderMode: false`):
- Forwards to target endpoint
- Validates response
- Normalizes format

### 5. Response Processing

**For Forwarding Mode:**
```
Target Forwarder → HTTP Request → Target Endpoint
                ↓
      Response Validator
                ↓
         Normalization
                ↓
        OpenAI Format Response
```

**Validation Steps:**
1. Check for error responses from target
2. Verify `choices` array exists and is populated
3. Validate message/delta structure
4. Fill missing required fields (id, created, model)
5. Estimate usage if not provided

### 6. Logging
```
Every Request → Logger
```
- API call logs (request/response/duration)
- Server event logs (info/warn/error)
- Stored in-memory (last 1000 entries)
- Accessible via dashboard API

### 7. Response Return
```
Proxy → Client
```
- Always returns OpenAI-compatible format
- Includes proper HTTP status codes
- Contains all required fields

## Key Files

### Core Application
- **`src/index.ts`** - Main server, middleware setup, startup
- **`src/config.ts`** - Configuration management
- **`src/logger.ts`** - Logging system

### API Routes
- **`src/routes/openai.ts`** - OpenAI-compatible endpoints
  - Authentication middleware
  - Request validation
  - Mode switching (placeholder/forwarding)
  - Response handling
- **`src/routes/dashboard.ts`** - Dashboard API endpoints
  - Configuration access
  - Log retrieval
  - Management operations

### Services
- **`src/services/target-forwarder.ts`** - HTTP client for target endpoint
  - Request forwarding
  - Error handling
  - Response capture

### Validation
- **`src/validators/response-validator.ts`** - Response validation & normalization
  - Format validation
  - Field normalization
  - Error detection
  - ID generation

### Type Definitions
- **`src/types.ts`** - Complete TypeScript types
  - OpenAI request/response types
  - All optional parameters
  - Error types
  - Internal types

### Frontend
- **`src/public/index.html`** - Dashboard UI
  - Real-time stats
  - Configuration display
  - Live log viewing
  - Auto-refresh

## Data Flow Examples

### Example 1: Successful Placeholder Request

```
1. Client sends: POST /v1/chat/completions
   {
     "model": "gpt-4",
     "messages": [{"role": "user", "content": "Hello"}]
   }

2. Proxy validates: ✅ Model present, ✅ Messages array valid

3. Config check: usePlaceholderMode = true

4. Generate mock response:
   {
     "id": "chatcmpl-abc123",
     "object": "chat.completion",
     "model": "gpt-4",
     "choices": [{
       "message": {"role": "assistant", "content": "Placeholder response"}
     }],
     "usage": {"total_tokens": 35}
   }

5. Log API call

6. Return 200 OK with response
```

### Example 2: Forwarded Request with Normalization

```
1. Client sends: POST /v1/chat/completions
   {
     "model": "gpt-4",
     "messages": [{"role": "user", "content": "Hello"}],
     "temperature": 0.7
   }

2. Proxy validates: ✅ All required fields present

3. Config check: usePlaceholderMode = false

4. Forward to target: POST https://target-llm.com/v1/chat/completions
   (with all parameters)

5. Target responds:
   {
     "choices": [{
       "message": {"role": "assistant", "content": "Hi there!"}
     }]
     // Missing: id, created, model, usage
   }

6. Validator detects: Missing fields

7. Normalize response:
   {
     "id": "chatcmpl-generated",      // ← Generated
     "object": "chat.completion",      // ← Added
     "created": 1234567890,            // ← Added
     "model": "gpt-4",                 // ← From request
     "choices": [{...}],               // ← From target
     "usage": {                        // ← Estimated
       "prompt_tokens": 0,
       "completion_tokens": 0,
       "total_tokens": 0
     }
   }

8. Log API call (with target duration)

9. Return 200 OK with normalized response
```

### Example 3: Target Endpoint Error

```
1. Client sends request

2. Proxy forwards to target

3. Target responds: 429 Rate Limit
   {
     "error": {"message": "Too many requests"}
   }

4. Validator detects error

5. Transform to OpenAI error format:
   {
     "error": {
       "message": "Too many requests",
       "type": "target_endpoint_error",
       "param": null,
       "code": "http_429"
     }
   }

6. Log error

7. Return 500 with error response
```

## Configuration Options

### Required Settings
```typescript
localPort: 3000                    // Port to listen on
localBaseUrl: 'http://localhost:3000'  // Public URL
accessToken: 'generated'            // Auto-generated bearer token
```

### Target Endpoint Settings
```typescript
targetEndpoint: 'https://...'       // Your LLM endpoint URL
targetApiKey: 'sk-...'              // Optional: target API key
usePlaceholderMode: true/false      // Toggle forwarding
```

## Error Handling Strategy

### Client Errors (4xx)
- **400 Bad Request**: Invalid parameters, missing required fields
- **401 Unauthorized**: Missing/invalid proxy access token

### Server Errors (5xx)
- **500 Internal Server Error**:
  - Target endpoint unreachable
  - Target returned invalid response
  - Validation failure

### Error Response Format
All errors follow OpenAI's format:
```json
{
  "error": {
    "message": "Human-readable error",
    "type": "error_type",
    "param": "parameter_name",
    "code": "error_code"
  }
}
```

## Performance Characteristics

### Placeholder Mode
- **Latency**: < 1ms
- **Throughput**: Limited by Node.js event loop
- **Resource**: Minimal CPU/memory

### Forwarding Mode
- **Latency**: Target latency + 1-2ms (validation overhead)
- **Throughput**: Limited by target endpoint
- **Resource**: Minimal additional overhead

### Logging
- **Impact**: < 0.1ms per request
- **Storage**: In-memory ring buffer (last 1000 entries)
- **Cleanup**: Automatic (oldest entries dropped)

## Security Considerations

### Authentication
- Bearer token generated on startup (cryptographically random)
- Token required for all API endpoints
- Token visible in logs and dashboard (store securely)

### Data Handling
- No persistent storage of requests/responses
- Logs kept in-memory only
- Target API keys never logged

### Network
- All target requests use HTTPS (recommended)
- No SSL/TLS validation bypass
- Standard Node.js fetch API

## Scalability

### Current Limitations
- Single instance (no clustering)
- In-memory logs (not shared across instances)
- Access token per instance

### Future Enhancements
- Redis for distributed logging
- Persistent token storage
- Load balancing support
- Response caching
- Rate limiting

## Development vs. Production

### Development Mode (`npm run dev`)
- Hot reload on file changes
- Detailed console logging
- New token on each restart

### Production Mode (`npm run build && npm start`)
- Compiled TypeScript
- Optimized performance
- Single token until restart

## Monitoring & Observability

### Available Metrics
- Total requests
- Success rate
- Average response time
- Uptime

### Log Types
1. **API Call Logs**
   - Method, path, headers
   - Request/response bodies
   - Status codes, duration

2. **Server Event Logs**
   - Level (info/warn/error)
   - Message, details
   - Timestamp

### Dashboard
- Real-time view at `/`
- Auto-refresh every 2 seconds
- Last 50 logs visible
- Stats cards with computed metrics

## Extension Points

### Adding Custom Endpoints
Add routes in `src/routes/openai.ts`:
```typescript
router.post('/custom', async (req, res) => {
  // Custom logic
});
```

### Custom Validation Logic
Extend `src/validators/response-validator.ts`:
```typescript
export function validateCustomResponse(response: any) {
  // Custom validation
}
```

### Adding More LLM Providers
Add provider-specific logic in `src/services/`:
```typescript
export async function forwardToProvider(request) {
  // Provider-specific handling
}
```

## Testing Strategy

### Unit Tests (TODO)
- Validation logic
- Normalization functions
- ID generation

### Integration Tests
- Currently: Manual testing with OpenAI client
- Verified: All major request types
- Tested: Error handling paths

### E2E Tests (TODO)
- Full request flow
- Multiple scenarios
- Performance benchmarks
