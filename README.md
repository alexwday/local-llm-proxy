# OpenAI-Compatible LLM Proxy

A production-ready Python proxy server that forwards OpenAI API requests to custom LLM endpoints with OAuth 2.0 and RBC Security support.

## Features

- **100% OpenAI API v1 Compatible** - Works with official OpenAI clients and tools (including OpenAI Codex CLI)
- **OAuth 2.0 Token Management** - Automatic token refresh with configurable buffer
- **RBC Security Integration** - Direct integration with `rbc_security` Python package
- **Development Mode** - Bypasses OAuth and rbc_security for local testing
- **Modern Dashboard** - Real-time monitoring and configuration
- **Virtual Environment** - Clean, isolated Python environment
- **Request/Response Logging** - Track all API interactions

## Quick Start

### 1. Setup

```bash
./setup.sh
```

### 2. Configure

Edit `.env` with your settings:

```bash
PROXY_ACCESS_TOKEN=your-token
TARGET_ENDPOINT=https://your-llm-endpoint.com/v1
OAUTH_TOKEN_ENDPOINT=https://auth.yourcompany.com/oauth/token
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
```

### 3. Run

**Development Mode (bypasses OAuth & rbc_security):**
```bash
./run-dev.sh
```

**Production Mode (uses OAuth & rbc_security):**
```bash
./run.sh
```

### 4. Use with OpenAI Codex CLI

Launch OpenAI Codex CLI through the proxy:

```bash
# In terminal 1: Start the proxy
./run-dev.sh  # or ./run.sh for production

# In terminal 2: Launch OpenAI Codex CLI
./launch-codex.sh
```

**Note:** Use `launch-codex.sh` (not `launch-codex.py`) to ensure the venv Python with required packages is used.

**Using from other project directories:**
```bash
# From any project directory
~/Projects/local-llm-proxy/launch-codex.sh

# Or add an alias to your shell config (~/.bashrc, ~/.zshrc):
alias codex-proxy="~/Projects/local-llm-proxy/launch-codex.sh"

# Then from anywhere:
cd ~/my-project
codex-proxy
```

**Installation:**
```bash
npm install -g @openai/codex
# Or use npx: npx @openai/codex
```

### 5. Test

Validate the proxy is working correctly:

```bash
# Run the test suite (proxy must be running)
python3 test_proxy.py
```

The test script automatically:
- ✅ Loads configuration from `.env`
- ✅ Shows proxy mode (dev/production, placeholder/real endpoint)
- ✅ Tests chat completion endpoints with proper authentication
- ✅ Validates OAuth and SSL configuration in production mode
- ✅ Tests dashboard and logging functionality

**Customize test model:**
```bash
TEST_MODEL=gpt-3.5-turbo python3 test_proxy.py
```

**Test against remote proxy:**
```bash
PROXY_URL=https://remote-proxy.com python3 test_proxy.py
```

**Testing Modes:**

**Placeholder Mode (Default for local testing):**
```bash
# In .env:
USE_PLACEHOLDER_MODE=true

# All 10 tests should pass without real endpoint
```

**Production Mode (With real endpoint):**
```bash
# In .env:
USE_PLACEHOLDER_MODE=false
TARGET_ENDPOINT=https://your-real-llm-endpoint.com/v1
OAUTH_TOKEN_ENDPOINT=https://auth.yourcompany.com/oauth/token
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret

# Run in production mode:
./run.sh

# Then test (OAuth and SSL will be used):
python3 test_proxy.py
```

**Expected output:**
```
🎉 All tests passed! The proxy is working correctly.
✅ Tests passed: 7
❌ Tests failed: 0
📈 Success rate: 100%
```

## Model Configuration

Configure your target models in `.env`:

```bash
# In .env file
DEFAULT_MODEL=your-model-name           # Default model for requests
AVAILABLE_MODELS=model1,model2,model3  # Comma-separated list of available models
```

## Development vs Production

### Development Mode
- OAuth: Disabled (mock tokens)
- rbc_security: Disabled
- Use case: Local testing

### Production Mode
- OAuth: Required (auto-refresh)
- rbc_security: Required (SSL setup)
- Use case: RBC work environment

## RBC Work Environment

1. Clone and setup:
   ```bash
   git clone https://github.com/alexwday/local-llm-proxy.git
   cd local-llm-proxy
   ./setup.sh
   ```

2. Install rbc_security:
   ```bash
   source venv/bin/activate
   pip install rbc_security
   ```

3. Configure `.env` with your models and OAuth settings:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the proxy:
   ```bash
   ./run.sh
   ```

5. Launch OpenAI Codex CLI (from any directory):
   ```bash
   ./launch-codex.sh
   ```

## API Endpoints

### OpenAI-Compatible Endpoints
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Get model details
- `POST /v1/chat/completions` - Chat completions (OpenAI format)
- `POST /v1/completions` - Text completions (OpenAI format)

### Dashboard & Monitoring
- `GET /` - Web dashboard
- `GET /api/config` - Proxy configuration
- `GET /api/logs` - All logs
- `GET /api/logs/api-calls` - API call history
- `GET /api/logs/server-events` - Server events
- `GET /health` - Health check

## Documentation

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

## License

MIT
