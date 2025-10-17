# Troubleshooting Guide

## OAuth Errors

### "invalid_scope" - The request scope is invalid

**Error Message:**
```
OAuth token request failed with 400: the request scope is invalid, unknown, malformed, or exceed that which the client is permitted to request error invalid_scope
```

**Solution:**

1. **Try without scope** - Comment out or remove `OAUTH_SCOPE` from `.env`:
   ```bash
   # OAUTH_SCOPE=api.read
   ```

2. **Ask your OAuth admin** for the correct scope value

3. **Common scopes to try:**
   ```bash
   OAUTH_SCOPE=openid
   # or
   OAUTH_SCOPE=read write
   # or
   OAUTH_SCOPE=llm.api
   ```

### "invalid_client" - Client authentication failed

**Error Message:**
```
OAuth token request failed with 401: invalid_client
```

**Solution:**

1. **Verify credentials** in `.env`:
   ```bash
   OAUTH_CLIENT_ID=your-actual-client-id
   OAUTH_CLIENT_SECRET=your-actual-client-secret
   ```

2. **Check the OAuth endpoint URL** is correct

3. **Verify client is registered** with your OAuth provider

### OAuth token obtained but requests still fail with 401

**Possible causes:**

1. **Wrong target endpoint** - Verify `TARGET_ENDPOINT` in `.env`

2. **Token not being sent** - Check server logs for:
   ```
   [INFO] Using OAuth token for target authentication
   ```

3. **Target endpoint expects different auth** - Some endpoints need API keys instead of OAuth

## Test Script Failures

### Tests 4-7 fail with 401 Unauthorized

**Check:**

1. **Proxy token mismatch:**
   ```bash
   # In .env:
   PROXY_ACCESS_TOKEN=your-token

   # Test script reads this automatically from .env
   python3 test_proxy.py
   ```

2. **OAuth not configured:**
   - If using real endpoint, configure OAuth in `.env`
   - If testing locally, set `USE_PLACEHOLDER_MODE=true`

### Tests 4-7 fail with 500 errors

**This means:**

1. **OAuth failed** - Check server logs for detailed error
2. **Target endpoint unreachable** - Verify `TARGET_ENDPOINT` in `.env`
3. **SSL/rbc_security issue** - On work computer, ensure `pip install rbc_security`

## Development vs Production Mode

### How to test without OAuth/rbc_security (local computer)

```bash
# Run in dev mode:
./run-dev.sh

# Or set in .env:
DEV_MODE=true

# Then:
./run.sh
```

### How to test with real OAuth (work computer)

```bash
# In .env:
# Remove or comment out DEV_MODE
# DEV_MODE=true

# Configure OAuth:
OAUTH_TOKEN_ENDPOINT=https://your-oauth-server.com/token
OAUTH_CLIENT_ID=your-id
OAUTH_CLIENT_SECRET=your-secret
# OAUTH_SCOPE=  (comment out if you get invalid_scope error)

# Run:
./run.sh

# Test:
python3 test_proxy.py
```

## rbc_security Issues

### "rbc_security not available"

**On personal computer:** This is normal - use `./run-dev.sh`

**On RBC work computer:**
```bash
source venv/bin/activate
pip install rbc_security
```

### SSL certificate errors

**Work computer:**
```bash
# Ensure rbc_security is installed
pip list | grep rbc_security

# Run in production mode (not dev mode)
./run.sh
```

**Personal computer:**
```bash
# Use dev mode to bypass SSL
./run-dev.sh
```

## General Debugging

### Enable detailed logging

The proxy automatically logs OAuth and request details. Check the server output for:

```
[INFO] Fetching OAuth token from https://...
[DEBUG] OAuth request: grant_type=client_credentials, scope=...
[ERROR] OAuth token request failed with 400: {...}
```

### Test configuration

Check what mode the proxy is running in:

```bash
curl http://localhost:3000/api/config | python3 -m json.tool
```

Output shows:
```json
{
  "usePlaceholderMode": true/false,
  "oauthConfigured": true/false,
  "devMode": true/false,
  "targetEndpoint": "..."
}
```

### Quick fixes

1. **Port in use:**
   ```bash
   lsof -ti:3000 | xargs kill -9
   ```

2. **Restart proxy:**
   ```bash
   pkill -f "python proxy.py"
   ./run.sh  # or ./run-dev.sh
   ```

3. **Clean restart:**
   ```bash
   rm -rf venv
   ./setup.sh
   ./run.sh
   ```

## Getting Help

When asking for help, provide:

1. **Error message from server logs**
2. **Configuration output:**
   ```bash
   curl http://localhost:3000/api/config
   ```
3. **Test output:**
   ```bash
   python3 test_proxy.py
   ```
4. **Mode you're running in:** `./run.sh` or `./run-dev.sh`
