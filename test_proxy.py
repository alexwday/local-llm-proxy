#!/usr/bin/env python3
"""
Test script for OpenAI-Compatible LLM Proxy

Validates that the proxy is working correctly by testing all endpoints.

Usage:
    python3 test_proxy.py                          # Use .env config
    PROXY_URL=http://remote:3000 python3 test_proxy.py  # Test remote proxy
    TEST_MODEL=gpt-3.5-turbo python3 test_proxy.py      # Use different model
"""

import os
import sys
import json
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration
PROXY_URL = os.getenv('PROXY_URL', 'http://localhost:3000')
PROXY_TOKEN = os.getenv('PROXY_ACCESS_TOKEN', 'your-static-proxy-token-here')
TEST_MODEL = os.getenv('TEST_MODEL', 'gpt-4')  # Model to use for testing

# Test tracking
tests_passed = 0
tests_failed = 0


def log(emoji: str, message: str):
    """Print a log message."""
    print(f"{emoji} {message}")


def log_success(message: str):
    """Log a successful test."""
    global tests_passed
    tests_passed += 1
    log("✅", message)


def log_error(message: str):
    """Log a failed test."""
    global tests_failed
    tests_failed += 1
    log("❌", message)


def log_info(message: str):
    """Log an info message."""
    log("ℹ️ ", message)


def make_request(
    method: str,
    path: str,
    headers: Dict[str, str] = None,
    json_data: Dict[str, Any] = None
) -> requests.Response:
    """Make a request to the proxy."""
    url = f"{PROXY_URL}{path}"
    default_headers = {
        'Authorization': f'Bearer {PROXY_TOKEN}',
        'Content-Type': 'application/json'
    }

    if headers:
        default_headers.update(headers)

    try:
        if method == 'GET':
            return requests.get(url, headers=default_headers, timeout=10)
        elif method == 'POST':
            return requests.post(url, headers=default_headers, json=json_data, timeout=10)
        elif method == 'DELETE':
            return requests.delete(url, headers=default_headers, timeout=10)
    except requests.exceptions.ConnectionError:
        log_error(f"Cannot connect to proxy at {PROXY_URL}")
        log_info("   Make sure the proxy is running: ./run-dev.sh")
        sys.exit(1)
    except Exception as e:
        log_error(f"Request error: {e}")
        sys.exit(1)


def test_health_check():
    """Test the health check endpoint."""
    log_info("Test 1: Health check endpoint")
    try:
        response = requests.get(f"{PROXY_URL}/health", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                dev_mode = data.get('devMode', False)
                mode_str = "DEV MODE" if dev_mode else "PRODUCTION MODE"
                log_success(f"Health check passed ({mode_str})")
            else:
                log_error(f"Health check failed: unexpected status {data.get('status')}")
        else:
            log_error(f"Health check failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Health check error: {e}")


def test_proxy_config():
    """Test proxy configuration endpoint."""
    log_info("Test 2: Proxy configuration")
    try:
        response = requests.get(f"{PROXY_URL}/api/config", timeout=10)

        if response.status_code == 200:
            data = response.json()
            log_info(f"   Placeholder Mode: {data.get('usePlaceholderMode')}")
            log_info(f"   OAuth Configured: {data.get('oauthConfigured')}")
            log_info(f"   Dev Mode: {data.get('devMode')}")
            log_info(f"   Target: {data.get('targetEndpoint')}")
            log_success("Configuration retrieved")
        else:
            log_error(f"Config retrieval failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Config retrieval error: {e}")


def test_list_models():
    """Test listing models."""
    log_info("Test 3: List models endpoint (/v1/models)")
    try:
        response = make_request('GET', '/v1/models')

        if response.status_code == 200:
            data = response.json()
            if data.get('object') == 'list' and isinstance(data.get('data'), list):
                model_count = len(data['data'])
                models = [m['id'] for m in data['data']]
                log_success(f"Models list retrieved ({model_count} models)")
                log_info(f"   Available: {', '.join(models)}")
            else:
                log_error("Models list failed: invalid response format")
        elif response.status_code == 401:
            log_error(f"Models list failed: 401 Unauthorized")
            log_info(f"   Token being used: {PROXY_TOKEN[:30]}...")
            log_info(f"   Check your .env PROXY_ACCESS_TOKEN matches")
        else:
            log_error(f"Models list failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Models list error: {e}")


def test_get_model():
    """Test getting a specific model."""
    log_info(f"Test 4: Get specific model (/v1/models/{TEST_MODEL})")
    try:
        response = make_request('GET', f'/v1/models/{TEST_MODEL}')

        if response.status_code == 200:
            data = response.json()
            if data.get('id') == TEST_MODEL:
                log_success(f"Specific model retrieved: {TEST_MODEL}")
            else:
                log_error(f"Get model failed: unexpected model id {data.get('id')}")
        elif response.status_code == 404:
            log_error(f"Model '{TEST_MODEL}' not found")
            log_info(f"   Use TEST_MODEL env var to specify a different model")
        elif response.status_code == 401:
            log_error(f"Get model failed: 401 Unauthorized")
        else:
            log_error(f"Get model failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Get model error: {e}")


def test_chat_completion_basic():
    """Test basic chat completion."""
    log_info(f"Test 3: Chat completion with {TEST_MODEL}")
    try:
        response = make_request('POST', '/v1/chat/completions', json_data={
            'model': TEST_MODEL,
            'messages': [
                {'role': 'user', 'content': 'Say "test successful" if you can read this.'}
            ]
        })

        if response.status_code == 200:
            data = response.json()
            if data.get('choices') and len(data['choices']) > 0:
                message = data['choices'][0].get('message', {})
                content = message.get('content', '')
                log_success(f"Chat completion successful")
                log_info(f"   Response: {content[:80]}...")
            else:
                log_error("Chat completion failed: no choices in response")
        elif response.status_code == 401:
            log_error(f"Chat completion failed: 401 Unauthorized")
            log_info(f"   Token: {PROXY_TOKEN[:30]}...")
        elif response.status_code >= 500:
            log_error(f"Chat completion failed with server error: {response.status_code}")
            try:
                error_data = response.json()
                log_info(f"   Error: {error_data.get('error', {}).get('message', 'Unknown')}")
            except:
                pass
        else:
            log_error(f"Chat completion failed: status {response.status_code}")
            try:
                log_info(f"   Response: {response.text[:200]}")
            except:
                pass
    except Exception as e:
        log_error(f"Chat completion error: {e}")


def test_chat_completion_with_params():
    """Test chat completion with parameters."""
    log_info(f"Test 4: Chat completion with parameters")
    try:
        response = make_request('POST', '/v1/chat/completions', json_data={
            'model': TEST_MODEL,
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'What is 2+2?'}
            ],
            'temperature': 0.7,
            'max_tokens': 100,
            'n': 1
        })

        if response.status_code == 200:
            data = response.json()
            if data.get('choices'):
                log_success("Chat completion with parameters successful")
            else:
                log_error("Chat completion with params failed: no choices")
        elif response.status_code == 401:
            log_error(f"Chat completion with params failed: 401 Unauthorized")
        elif response.status_code >= 500:
            log_error(f"Chat completion with params failed: server error {response.status_code}")
        else:
            log_error(f"Chat completion with params failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Chat completion with params error: {e}")


def test_text_completion():
    """Test text completion (legacy endpoint)."""
    log_info("Test 7: Text completion (legacy endpoint)")
    try:
        response = make_request('POST', '/v1/completions', json_data={
            'model': 'gpt-3.5-turbo',
            'prompt': 'Once upon a time',
            'max_tokens': 50
        })

        if response.status_code == 200:
            data = response.json()
            if data.get('choices'):
                log_success("Text completion successful")
            else:
                log_error("Text completion failed: no choices")
        elif response.status_code == 401:
            log_error(f"Text completion failed: 401 Unauthorized")
        elif response.status_code >= 500:
            log_error(f"Text completion failed: server error {response.status_code}")
        else:
            log_error(f"Text completion failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Text completion error: {e}")


def test_authentication():
    """Test authentication validation."""
    log_info("Test 5: Authentication validation (should reject invalid token)")
    try:
        response = make_request('GET', '/v1/models', headers={
            'Authorization': 'Bearer invalid-token-12345'
        })

        if response.status_code == 401:
            log_success("Authentication validation working correctly")
        else:
            log_error(f"Authentication should reject invalid tokens (got {response.status_code})")
    except Exception as e:
        log_error(f"Authentication test error: {e}")


def test_dashboard():
    """Test dashboard accessibility."""
    log_info("Test 6: Dashboard accessibility")
    try:
        response = requests.get(PROXY_URL, timeout=10)

        if response.status_code == 200:
            if 'html' in response.headers.get('Content-Type', '').lower():
                log_success("Dashboard is accessible")
            else:
                log_error("Dashboard returned non-HTML content")
        else:
            log_error(f"Dashboard not accessible: status {response.status_code}")
    except Exception as e:
        log_error(f"Dashboard access error: {e}")


def test_dashboard_api_logs():
    """Test dashboard API logs endpoint."""
    log_info("Test 7: Dashboard API - logs endpoint")
    try:
        response = requests.get(f"{PROXY_URL}/api/logs", timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'apiCalls' in data and 'serverEvents' in data:
                log_success("Dashboard API logs endpoint working")
            else:
                log_error("Dashboard API logs failed: missing fields")
        else:
            log_error(f"Dashboard API logs failed: status {response.status_code}")
    except Exception as e:
        log_error(f"Dashboard API logs error: {e}")


def print_summary():
    """Print test summary."""
    total = tests_passed + tests_failed
    success_rate = (tests_passed / total * 100) if total > 0 else 0

    print()
    print("=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    print(f"✅ Tests passed: {tests_passed}")
    print(f"❌ Tests failed: {tests_failed}")
    print(f"📈 Success rate: {success_rate:.0f}%")

    if tests_failed == 0:
        print("\n🎉 All tests passed! The proxy is working correctly.")
    elif tests_failed <= 2 and tests_passed >= 8:
        print("\n⚠️  Most tests passed. Some failures may be due to configuration.")
        print("   Check the logs above for details.")
    else:
        print("\n❌ Multiple tests failed. Please check the configuration.")

    print("\n" + "=" * 80 + "\n")


def main():
    """Run all tests."""
    print()
    print("=" * 80)
    print("🧪 OpenAI-Compatible LLM Proxy Test Suite")
    print("=" * 80)
    print(f"\n🔗 Testing proxy at: {PROXY_URL}")
    print(f"🔑 Using access token: {PROXY_TOKEN[:30]}...")
    print(f"🤖 Test model: {TEST_MODEL}\n")

    # Run tests
    test_health_check()
    test_proxy_config()
    test_chat_completion_basic()
    test_chat_completion_with_params()
    test_authentication()
    test_dashboard()
    test_dashboard_api_logs()

    # Print summary
    print_summary()

    # Exit with appropriate code
    sys.exit(0 if tests_failed == 0 else 1)


if __name__ == '__main__':
    main()
