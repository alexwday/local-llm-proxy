# Local LLM Proxy

An OpenAI-compatible local proxy server that allows you to use custom LLM endpoints with any tool that supports OpenAI API format.

## Features

- **100% OpenAI API Compatible**: Fully compliant with OpenAI's v1 API specification
  - All request parameters supported
  - All response formats match exactly
  - Works seamlessly with official OpenAI client libraries (Python, JavaScript, etc.)
- **OAuth 2.0 Support**: Automatic token management for target endpoints
  - Auto-refresh before expiration
  - Configurable refresh buffer
  - Fallback to simple API key authentication
- **Response Validation**: Automatic normalization of target responses to OpenAI format
  - Handles various response formats
  - Auto-fills missing fields
  - Comprehensive error handling
- **Modern Dashboard**: Beautiful, responsive UI with real-time stats and logs
- **Custom Access Token**: Secure your proxy with automatically generated tokens
- **Request/Response Logging**: Track all API interactions with detailed logs
- **Easy Integration**: Drop-in replacement for any tool that accepts custom OpenAI base URLs
- **Type-Safe**: Comprehensive TypeScript types matching OpenAI's specification
- **Environment-Based Configuration**: Production-ready configuration via environment variables

## Quick Start

### Installation

```bash
npm install
```

### Development Mode

```bash
npm run dev
```

### Production Mode

```bash
npm run build
npm start
```

## Usage

### 1. Start the Server

```bash
npm run dev
```

The server will start on port 3000 by default and display:
- Dashboard URL
- API Base URL
- Access Token

### 2. Access the Dashboard

Open your browser to `http://localhost:3000` to view:
- Configuration details (proxy URL, access token, target endpoint)
- API call logs (requests and responses)
- Server event logs

### 3. Use with OpenAI-Compatible Tools

Configure your tools with:

- **Base URL**: `http://localhost:3000/v1`
- **API Key**: The access token displayed in the console/dashboard

Example with `curl`:

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Example with Python OpenAI library:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3000/v1",
    api_key="YOUR_ACCESS_TOKEN"
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## API Endpoints

### OpenAI-Compatible Endpoints (requires Bearer token)

All endpoints fully match the OpenAI API specification:

- `GET /v1/models` - List available models
- `GET /v1/models/{model}` - Retrieve specific model details
- `POST /v1/chat/completions` - Chat completions (main endpoint)
  - Supports all OpenAI parameters: temperature, top_p, n, max_tokens, stop, presence_penalty, frequency_penalty, logit_bias, response_format, seed, tools, functions, user, and more
  - Returns properly formatted responses with system_fingerprint, usage details, etc.
- `POST /v1/completions` - Legacy text completions
  - Full parameter support matching OpenAI specification

**See [OPENAI_API_COMPATIBILITY.md](OPENAI_API_COMPATIBILITY.md) for complete API documentation.**

### Dashboard API Endpoints

- `GET /api/config` - Get proxy configuration
- `GET /api/logs/api-calls` - Get API call logs
- `GET /api/logs/server-events` - Get server event logs
- `DELETE /api/logs` - Clear all logs

### Utility Endpoints

- `GET /health` - Health check
- `GET /` - Dashboard UI

## Configuration

The proxy is configured using environment variables. See [.env.example](.env.example) for all available options.

### Quick Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```bash
   # Required: Your static proxy token (for clients)
   PROXY_ACCESS_TOKEN=llm-proxy-your-token-here

   # Required: Your target LLM endpoint
   TARGET_ENDPOINT=https://your-llm-endpoint.com/v1

   # Choose ONE authentication method:

   # Option A: OAuth 2.0 (recommended for enterprise endpoints)
   OAUTH_TOKEN_ENDPOINT=https://auth.yourservice.com/token
   OAUTH_CLIENT_ID=your-client-id
   OAUTH_CLIENT_SECRET=your-client-secret
   OAUTH_REFRESH_BUFFER_MINUTES=5

   # Option B: Simple API Key
   TARGET_API_KEY=sk-your-api-key
   ```

3. **Start the server:**
   ```bash
   npm run dev
   ```

### Configuration Options

#### Proxy Settings
- `PROXY_PORT` - Port to listen on (default: 3000)
- `PROXY_BASE_URL` - Public URL of the proxy
- `PROXY_ACCESS_TOKEN` - Static token for client authentication (auto-generated if not set)

#### Target Endpoint
- `TARGET_ENDPOINT` - URL of your actual LLM service
- `USE_PLACEHOLDER_MODE` - Set to `true` for testing without a real endpoint

#### Authentication (choose one)

**OAuth 2.0 Client Credentials Flow:**
- `OAUTH_TOKEN_ENDPOINT` - OAuth token endpoint URL
- `OAUTH_CLIENT_ID` - OAuth client ID
- `OAUTH_CLIENT_SECRET` - OAuth client secret
- `OAUTH_SCOPE` - OAuth scope (optional)
- `OAUTH_REFRESH_BUFFER_MINUTES` - Minutes before expiry to refresh (default: 5)

**Simple API Key:**
- `TARGET_API_KEY` - Bearer token for target endpoint

### Testing the Proxy

Run the included test script to validate your configuration:

```bash
# Set your proxy token
export PROXY_ACCESS_TOKEN=your-token-here

# Run tests (default: http://localhost:3000)
node test-proxy.js

# Or test a remote proxy
PROXY_URL=https://your-proxy.com node test-proxy.js
```

The test script validates:
- Health check endpoint
- Model listing and retrieval
- Chat completions (basic and with parameters)
- Text completions (legacy)
- Authentication
- Dashboard access
- Dashboard API endpoints

**See [SETUP.md](SETUP.md) for complete setup and testing instructions.**

## Operating Modes

### Placeholder Mode (Testing)

Set `USE_PLACEHOLDER_MODE=true` to return mock responses without connecting to a real endpoint. Great for:
- Testing client integrations
- Verifying API compatibility
- Development without target access

### Forwarding Mode (Production)

Set `USE_PLACEHOLDER_MODE=false` to forward requests to your actual LLM endpoint. The proxy will:
- Authenticate using OAuth or API key
- Forward requests with all parameters
- Validate and normalize responses to OpenAI format
- Handle errors gracefully
- Auto-refresh OAuth tokens before expiration

**See [RESPONSE_VALIDATION.md](RESPONSE_VALIDATION.md) for details on response normalization.**

## Project Structure

```
local-llm-proxy/
├── src/
│   ├── index.ts                       # Main server with OAuth initialization
│   ├── config.ts                      # Environment-based configuration
│   ├── logger.ts                      # Logging utilities
│   ├── types.ts                       # TypeScript types (OpenAI spec)
│   ├── routes/
│   │   ├── openai.ts                  # OpenAI-compatible endpoints
│   │   └── dashboard.ts               # Dashboard API endpoints
│   ├── services/
│   │   ├── oauth-manager.ts           # OAuth token management
│   │   └── target-forwarder.ts        # Request forwarding to target
│   ├── validators/
│   │   └── response-validator.ts      # Response validation & normalization
│   └── public/
│       └── index.html                 # Dashboard UI
├── .env.example                       # Environment configuration template
├── test-proxy.js                      # Test script for validation
├── SETUP.md                           # Complete setup guide
├── ARCHITECTURE.md                    # System architecture docs
├── OPENAI_API_COMPATIBILITY.md        # API specification
├── RESPONSE_VALIDATION.md             # Response handling docs
├── package.json
├── tsconfig.json
└── README.md
```

## Development

### Build

```bash
npm run build
```

### Run Tests

```bash
npm test
```

## Security Notes

- **Proxy Access Token**: Set `PROXY_ACCESS_TOKEN` in production for consistent authentication
  - Auto-generated if not set (changes on restart)
  - Never commit tokens to version control
  - Use strong, random tokens in production
- **OAuth Credentials**: OAuth client secrets are never logged
  - Tokens are stored in memory only
  - Auto-refresh before expiration
  - Proper cleanup on shutdown
- **Target API Keys**: Never logged or exposed in error messages
- **HTTPS**: Use HTTPS in production for both proxy and target endpoints
- **Environment Variables**: Use `.env` file (gitignored) for sensitive config
- **For Production**: Consider implementing:
  - Rate limiting
  - IP whitelisting
  - Request size limits
  - Persistent logging
  - Monitoring and alerts

## Troubleshooting

### Port Already in Use

Set `PROXY_PORT` in your `.env` file to use a different port:
```bash
PROXY_PORT=8080
```

### Authorization Errors

**Client to Proxy:**
- Ensure you're using the correct `PROXY_ACCESS_TOKEN`
- Include `Authorization: Bearer YOUR_PROXY_TOKEN` header
- Check the dashboard or console output for the token

**Proxy to Target:**
- Verify OAuth credentials are correct
- Check OAuth token endpoint is accessible
- Ensure API key is valid if using simple auth
- Check server logs for authentication errors

### OAuth Token Errors

If OAuth initialization fails:
1. Verify `OAUTH_TOKEN_ENDPOINT` is accessible
2. Check `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` are correct
3. Confirm the OAuth server supports client credentials flow
4. Check if `OAUTH_SCOPE` is required and correct
5. Review server logs for detailed error messages

### Response Format Errors

If you see "invalid response format" errors:
- Your target endpoint may return non-OpenAI format responses
- Check [RESPONSE_VALIDATION.md](RESPONSE_VALIDATION.md) for supported formats
- Enable detailed logging to see raw responses
- May need custom transformation logic

### Connection Errors

- Verify `TARGET_ENDPOINT` is accessible from your server
- Check firewall and network settings
- Ensure HTTPS certificates are valid
- Try `USE_PLACEHOLDER_MODE=true` to test proxy without target

**For detailed troubleshooting, see [SETUP.md](SETUP.md).**

## License

MIT
