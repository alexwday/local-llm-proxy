#!/bin/bash
# Test script to verify Codex can reach the proxy endpoint

echo "Testing proxy endpoint that Codex should use..."
echo ""

TOKEN="your-static-proxy-token-here"
URL="http://localhost:3000/v1/chat/completions"

echo "URL: $URL"
echo "Token: ${TOKEN:0:20}..."
echo ""

curl -X POST "$URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test-model",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -v 2>&1 | grep -E "(HTTP|Connected|Authorization|error|placeholder)"

echo ""
echo "If you see 200 and placeholder response above, the endpoint is working!"
