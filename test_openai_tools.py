#!/usr/bin/env python3
"""
Test script to check if OpenAI API endpoint has built-in web search tools.

This script:
1. Uses OAuth2 (via rbc_security) to get an access token
2. Uses the OpenAI SDK to connect to a custom endpoint
3. Tests with gpt-5 (or specified model)
4. Checks what tools may be available natively in the model

Usage:
    python3 test_openai_tools.py

Configuration:
    Set these environment variables or edit .env:
    - OAUTH_TOKEN_ENDPOINT: OAuth token endpoint URL
    - OAUTH_CLIENT_ID: OAuth client ID
    - OAUTH_CLIENT_SECRET: OAuth client secret
    - OAUTH_SCOPE: OAuth scope (optional)
    - TARGET_ENDPOINT: Your custom OpenAI-compatible endpoint (e.g., https://api.company.com/v1)
    - TEST_MODEL: Model to test (REQUIRED - e.g., gpt-5, gpt-5-mini, gpt-4o)
    - GPT5_VERBOSITY: For GPT-5 models - low/medium/high (optional, default: medium)
    - GPT5_REASONING_EFFORT: For GPT-5 models - minimal/low/medium/high (optional)
"""

import os
import sys
import time
import json
import requests
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()


def setup_rbc_security():
    """Setup RBC Security SSL certificates if available."""
    try:
        import rbc_security
        print("🔐 Setting up RBC Security certificates...")
        rbc_security.enable_certs()
        print("✅ RBC Security configured successfully")
        return True
    except ImportError:
        print("⚠️  rbc_security not available (may be needed in corporate environment)")
        return False
    except Exception as e:
        print(f"⚠️  Failed to setup RBC Security: {e}")
        return False


class RBCOAuthManager:
    """Simple OAuth manager for RBC security."""

    def __init__(
        self,
        token_endpoint: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None
    ):
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._access_token: Optional[str] = None

    def get_token(self) -> str:
        """Fetch OAuth token using client credentials flow."""
        print(f"🔐 Fetching OAuth token from {self.token_endpoint}")

        data = {
            'grant_type': 'client_credentials',
        }

        if self.scope:
            data['scope'] = self.scope

        # Try with Basic Auth first (most OAuth servers prefer this)
        from requests.auth import HTTPBasicAuth
        auth = HTTPBasicAuth(self.client_id, self.client_secret)

        try:
            response = requests.post(
                self.token_endpoint,
                data=data,
                auth=auth,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )

            # If Basic Auth fails, try with credentials in body
            if response.status_code == 400:
                print("⚠️  Basic Auth failed, trying with credentials in request body...")
                data['client_id'] = self.client_id
                data['client_secret'] = self.client_secret

                response = requests.post(
                    self.token_endpoint,
                    data=data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )

            if not response.ok:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = f": {json.dumps(error_data, indent=2)}"
                except:
                    error_detail = f": {response.text}"

                raise Exception(f"OAuth request failed with status {response.status_code}{error_detail}")

            response.raise_for_status()
            token_data = response.json()

            self._access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 'unknown')

            print(f"✅ OAuth token obtained (expires in {expires_in}s)")
            return self._access_token

        except Exception as e:
            print(f"❌ Failed to fetch OAuth token: {e}")
            raise


def test_openai_tools():
    """Test OpenAI endpoint for built-in tools like web search."""

    # Setup RBC Security first (if available)
    print("=" * 80)
    print("🔧 Setup")
    print("=" * 80)
    setup_rbc_security()
    print()

    # Configuration
    oauth_endpoint = os.getenv('OAUTH_TOKEN_ENDPOINT')
    oauth_client_id = os.getenv('OAUTH_CLIENT_ID')
    oauth_client_secret = os.getenv('OAUTH_CLIENT_SECRET')
    oauth_scope = os.getenv('OAUTH_SCOPE')
    target_endpoint = os.getenv('TARGET_ENDPOINT')
    test_model = os.getenv('TEST_MODEL')
    gpt5_verbosity = os.getenv('GPT5_VERBOSITY', 'medium')
    gpt5_reasoning_effort = os.getenv('GPT5_REASONING_EFFORT')

    # Validate configuration
    if not all([oauth_endpoint, oauth_client_id, oauth_client_secret, target_endpoint, test_model]):
        print("❌ Missing required configuration!")
        print("\nRequired environment variables:")
        print("  - OAUTH_TOKEN_ENDPOINT")
        print("  - OAUTH_CLIENT_ID")
        print("  - OAUTH_CLIENT_SECRET")
        print("  - TARGET_ENDPOINT")
        print("  - TEST_MODEL (e.g., gpt-5, gpt-5-mini, gpt-4o)")
        print("\nOptional:")
        print("  - OAUTH_SCOPE")
        print("  - GPT5_VERBOSITY (low/medium/high, default: medium)")
        print("  - GPT5_REASONING_EFFORT (minimal/low/medium/high)")
        print("\nSet these in your .env file or environment.")
        sys.exit(1)

    # Detect if using GPT-5 model
    is_gpt5 = test_model.startswith('gpt-5')

    print("=" * 80)
    print("🧪 OpenAI Built-in Tools Test")
    print("=" * 80)
    print(f"\n📍 Endpoint: {target_endpoint}")
    print(f"🤖 Model: {test_model}")
    print(f"🔑 OAuth Endpoint: {oauth_endpoint}")
    if is_gpt5:
        print(f"🧠 GPT-5 Verbosity: {gpt5_verbosity}")
        if gpt5_reasoning_effort:
            print(f"🧠 GPT-5 Reasoning Effort: {gpt5_reasoning_effort}")
        print("ℹ️  Note: GPT-5 only supports temperature=1 (default)")
    print()

    try:
        # Step 1: Get OAuth token
        oauth_manager = RBCOAuthManager(
            token_endpoint=oauth_endpoint,
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            scope=oauth_scope
        )
        access_token = oauth_manager.get_token()
        print()

        # Step 2: Initialize OpenAI client with custom endpoint
        print(f"🔧 Initializing OpenAI client with custom endpoint...")
        client = OpenAI(
            api_key=access_token,
            base_url=target_endpoint
        )
        print("✅ OpenAI client initialized")
        print()

        # Step 3: Test 1 - Ask about available tools
        print("=" * 80)
        print("Test 1: Ask model about its capabilities")
        print("=" * 80)

        # Build request parameters
        request_params = {
            "model": test_model,
            "messages": [
                {
                    "role": "user",
                    "content": "What tools and capabilities do you have access to? Can you search the web? List all available tools you can use."
                }
            ]
        }

        # Add GPT-5 specific parameters if applicable
        if is_gpt5:
            request_params["verbosity"] = gpt5_verbosity
            if gpt5_reasoning_effort:
                request_params["reasoning_effort"] = gpt5_reasoning_effort
            # Don't set temperature for GPT-5 (only supports default value of 1)
        else:
            # For non-GPT-5 models, use temperature
            request_params["temperature"] = 0.1

        response = client.chat.completions.create(**request_params)

        content = response.choices[0].message.content
        print(f"\n📝 Model Response:\n{content}\n")

        # Check if response mentions web search or tools
        response_lower = content.lower()
        has_tools_mention = any(keyword in response_lower for keyword in [
            'web search', 'search the web', 'browse', 'internet search',
            'tool', 'function', 'capability', 'access to'
        ])

        if has_tools_mention:
            print("✅ Model mentions tools/capabilities in response")
        else:
            print("⚠️  Model does not explicitly mention tools")

        print()

        # Step 4: Test 2 - Ask a question that would require web search
        print("=" * 80)
        print("Test 2: Ask a question requiring current information")
        print("=" * 80)
        print("Asking: 'What is the current weather in New York City right now?'\n")

        request_params2 = {
            "model": test_model,
            "messages": [
                {
                    "role": "user",
                    "content": "What is the current weather in New York City right now? If you can search the web, please do so."
                }
            ]
        }

        if is_gpt5:
            request_params2["verbosity"] = gpt5_verbosity
            if gpt5_reasoning_effort:
                request_params2["reasoning_effort"] = gpt5_reasoning_effort
        else:
            request_params2["temperature"] = 0.1

        response2 = client.chat.completions.create(**request_params2)

        content2 = response2.choices[0].message.content
        print(f"📝 Model Response:\n{content2}\n")

        # Check for tool usage indicators
        if hasattr(response2.choices[0].message, 'tool_calls') and response2.choices[0].message.tool_calls:
            print("🎉 FOUND TOOL CALLS!")
            print(f"Number of tool calls: {len(response2.choices[0].message.tool_calls)}")
            for i, tool_call in enumerate(response2.choices[0].message.tool_calls):
                print(f"\nTool Call {i+1}:")
                print(f"  - ID: {tool_call.id}")
                print(f"  - Type: {tool_call.type}")
                print(f"  - Function: {tool_call.function.name}")
                print(f"  - Arguments: {tool_call.function.arguments}")
        else:
            print("ℹ️  No tool_calls in response object")

        print()

        # Step 5: Test 3 - Explicitly request web search with current events
        print("=" * 80)
        print("Test 3: Request explicit web search for current events")
        print("=" * 80)
        print("Asking: 'Search the web for the latest news today'\n")

        request_params3 = {
            "model": test_model,
            "messages": [
                {
                    "role": "user",
                    "content": "Search the web for the latest news headlines today. Use any web search tools you have available."
                }
            ]
        }

        if is_gpt5:
            request_params3["verbosity"] = gpt5_verbosity
            if gpt5_reasoning_effort:
                request_params3["reasoning_effort"] = gpt5_reasoning_effort
        else:
            request_params3["temperature"] = 0.1

        response3 = client.chat.completions.create(**request_params3)

        content3 = response3.choices[0].message.content
        print(f"📝 Model Response:\n{content3}\n")

        if hasattr(response3.choices[0].message, 'tool_calls') and response3.choices[0].message.tool_calls:
            print("🎉 FOUND TOOL CALLS!")
            for i, tool_call in enumerate(response3.choices[0].message.tool_calls):
                print(f"\nTool Call {i+1}:")
                print(f"  - Function: {tool_call.function.name}")
                print(f"  - Arguments: {tool_call.function.arguments}")
        else:
            print("ℹ️  No tool_calls in response object")

        print()

        # Summary
        print("=" * 80)
        print("📊 Summary")
        print("=" * 80)
        print("\n✅ Successfully connected to endpoint with OAuth token")
        print(f"✅ Model '{test_model}' is accessible")
        print(f"✅ Completed {3} test queries")

        # Check if any tools were detected
        tools_detected = False
        for resp in [response, response2, response3]:
            if hasattr(resp.choices[0].message, 'tool_calls') and resp.choices[0].message.tool_calls:
                tools_detected = True
                break

        if tools_detected:
            print("\n🎉 RESULT: Built-in tools (possibly web search) ARE AVAILABLE!")
        else:
            print("\n⚠️  RESULT: No built-in tools detected in responses")
            print("   The endpoint may not have native web search tools enabled,")
            print("   or they require specific parameters/configuration to activate.")

        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    test_openai_tools()
