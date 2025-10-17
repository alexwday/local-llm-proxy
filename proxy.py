#!/usr/bin/env python3
"""
OpenAI-Compatible LLM Proxy Server

A production-ready proxy server that forwards OpenAI API requests to custom LLM endpoints.

Features:
- 100% OpenAI API v1 compatibility
- OAuth 2.0 token management with auto-refresh
- RBC Security SSL/TLS certificate integration
- Request/response validation and logging
- Beautiful web dashboard
- Dev mode for local testing

Usage:
    python proxy.py                    # Production mode
    DEV_MODE=true python proxy.py      # Development mode (bypasses OAuth & rbc_security)
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Check if we're in dev mode
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'

# Initialize Flask app
app = Flask(__name__, static_folder='dashboard', static_url_path='')
CORS(app)

# Import our modules
from oauth_manager import OAuthManager
from config import Config
from logger_manager import LoggerManager
from request_handler import RequestHandler

# Initialize components
config = Config()
log_manager = LoggerManager()
oauth_manager = None
request_handler = None


def setup_rbc_security():
    """Setup RBC Security SSL certificates."""
    if DEV_MODE:
        logger.info("🔧 DEV_MODE: Skipping rbc_security setup")
        return True

    try:
        import rbc_security
        logger.info("Setting up RBC Security certificates...")
        rbc_security.enable_certs()
        logger.info("✓ RBC Security configured successfully")
        return True
    except ImportError:
        logger.warning("⚠️  rbc_security not available - install with: pip install rbc_security")
        logger.warning("⚠️  Continuing without SSL certificates (may fail in RBC environment)")
        return False
    except Exception as e:
        logger.error(f"Failed to setup RBC Security: {e}")
        return False


def setup_oauth():
    """Setup OAuth token manager."""
    global oauth_manager

    if DEV_MODE:
        logger.info("🔧 DEV_MODE: Skipping OAuth setup (using mock tokens)")
        oauth_manager = None
        return True

    if not config.is_oauth_configured():
        logger.warning("OAuth not configured - set OAUTH_* environment variables")
        return False

    try:
        oauth_manager = OAuthManager(
            token_endpoint=config.oauth_token_endpoint,
            client_id=config.oauth_client_id,
            client_secret=config.oauth_client_secret,
            scope=config.oauth_scope,
            refresh_buffer_minutes=config.oauth_refresh_buffer_minutes
        )

        # Get initial token
        token = oauth_manager.get_token()
        if token:
            logger.info("✓ OAuth token manager initialized successfully")
            return True
        else:
            logger.error("Failed to obtain initial OAuth token")
            return False
    except Exception as e:
        logger.error(f"Failed to setup OAuth: {e}")
        return False


def initialize_app():
    """Initialize the application."""
    global request_handler

    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 OpenAI-Compatible LLM Proxy Server")
    logger.info("=" * 80)
    logger.info("")

    if DEV_MODE:
        logger.info("🔧 Running in DEVELOPMENT MODE")
        logger.info("   - OAuth disabled (using mock tokens)")
        logger.info("   - rbc_security disabled")
        logger.info("")

    # Setup RBC Security
    setup_rbc_security()

    # Setup OAuth
    setup_oauth()

    # Initialize request handler
    request_handler = RequestHandler(config, oauth_manager, log_manager, dev_mode=DEV_MODE)

    # Print configuration
    logger.info("")
    logger.info("📊 Configuration:")
    logger.info(f"   Port:             {config.port}")
    logger.info(f"   Base URL:         http://localhost:{config.port}")
    logger.info(f"   Access Token:     {config.proxy_access_token[:40]}...")
    logger.info(f"   Target Endpoint:  {config.target_endpoint}")
    logger.info(f"   Dev Mode:         {DEV_MODE}")
    logger.info(f"   Placeholder Mode: {config.use_placeholder_mode}")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")


# ============================================================================
# ROUTES
# ============================================================================

def verify_access_token():
    """Verify the proxy access token."""
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return False, {"error": {"message": "Missing or invalid Authorization header", "type": "invalid_request_error"}}

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    if token != config.proxy_access_token:
        return False, {"error": {"message": "Invalid access token", "type": "invalid_request_error"}}

    return True, None


# OpenAI API Routes
@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models."""
    valid, error = verify_access_token()
    if not valid:
        return jsonify(error), 401

    return request_handler.list_models()


@app.route('/v1/models/<model_id>', methods=['GET'])
def get_model(model_id):
    """Get specific model details."""
    valid, error = verify_access_token()
    if not valid:
        return jsonify(error), 401

    return request_handler.get_model(model_id)


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Handle chat completion requests."""
    valid, error = verify_access_token()
    if not valid:
        return jsonify(error), 401

    return request_handler.chat_completions(request.get_json())


@app.route('/v1/completions', methods=['POST'])
def completions():
    """Handle text completion requests."""
    valid, error = verify_access_token()
    if not valid:
        return jsonify(error), 401

    return request_handler.completions(request.get_json())


@app.route('/v1/messages', methods=['POST'])
def anthropic_messages():
    """Handle Anthropic Messages API requests (used by Claude Code)."""
    import litellm
    start_time = time.time()

    valid, error = verify_access_token()
    if not valid:
        return jsonify(error), 401

    # Get Anthropic format request
    anthropic_request = request.get_json()

    # Log background requests for debugging
    if logger.isEnabledFor(logging.DEBUG):
        msg_count = len(anthropic_request.get("messages", []))
        logger.debug(f"Anthropic Messages request: {msg_count} messages, model: {anthropic_request.get('model', 'unknown')}")

    try:
        # Suppress LiteLLM logging
        litellm.suppress_debug_info = True
        litellm.set_verbose = False

        # Translate Anthropic Messages format to OpenAI Chat Completions format
        # Extract messages and system prompt
        messages = []

        # Handle system prompt
        if "system" in anthropic_request:
            system_content = anthropic_request["system"]
            if isinstance(system_content, str):
                messages.append({"role": "system", "content": system_content})
            elif isinstance(system_content, list):
                for item in system_content:
                    if isinstance(item, dict) and "text" in item:
                        messages.append({"role": "system", "content": item["text"]})

        # Handle messages
        for msg in anthropic_request.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, list):
                # Combine text blocks
                text_parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
                content = "\n".join(text_parts)

            # Skip empty messages
            if not content or (isinstance(content, str) and not content.strip()):
                logger.warning(f"Skipping empty message with role: {msg.get('role', 'unknown')}")
                continue

            messages.append({
                "role": msg.get("role", "user"),
                "content": content
            })

        # Build OpenAI request with model mapping
        incoming_model = anthropic_request.get("model", config.default_model)
        mapped_model = config.map_model_name(incoming_model)

        logger.info(f"Model mapping: {incoming_model} → {mapped_model}")

        # Validate we have at least one message
        if not messages:
            logger.error("No valid messages after processing")
            error_response = {
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "Request contained no valid messages"
                }
            }
            duration_ms = int((time.time() - start_time) * 1000)
            log_manager.log_api_call('POST', '/v1/messages', 400, duration_ms, anthropic_request, error_response)
            return jsonify(error_response), 400

        openai_request = {
            "model": mapped_model,
            "messages": messages
        }

        # Map optional parameters
        if "max_tokens" in anthropic_request:
            openai_request["max_tokens"] = anthropic_request["max_tokens"]

        # Handle temperature - default to 1 if 0 or not set (some models don't support 0)
        if "temperature" in anthropic_request:
            temp = anthropic_request["temperature"]
            # Skip temperature if it's 0 (some models like GPT-5 don't support it)
            # or default it to 1 if needed
            if temp > 0:
                openai_request["temperature"] = temp

        if "top_p" in anthropic_request:
            openai_request["top_p"] = anthropic_request["top_p"]
        if "stream" in anthropic_request:
            openai_request["stream"] = anthropic_request["stream"]
        if "stop_sequences" in anthropic_request:
            openai_request["stop"] = anthropic_request["stop_sequences"]

        # Forward to OpenAI-compatible endpoint
        openai_response, status_code = request_handler.chat_completions(openai_request)

        if status_code != 200:
            duration_ms = int((time.time() - start_time) * 1000)
            log_manager.log_api_call('POST', '/v1/messages', status_code, duration_ms, anthropic_request, None)
            return openai_response, status_code

        # Convert OpenAI response to Anthropic format
        openai_data = openai_response.get_json()

        choice = openai_data.get("choices", [{}])[0]
        message_content = choice.get("message", {}).get("content", "")

        # Map finish_reason
        finish_reason_map = {
            "stop": "end_turn",
            "length": "max_tokens",
            "content_filter": "stop_sequence"
        }
        stop_reason = finish_reason_map.get(choice.get("finish_reason", "stop"), "end_turn")

        anthropic_response = {
            "id": openai_data.get("id", "msg_unknown").replace("chatcmpl-", "msg_"),
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": message_content}],
            "model": anthropic_request.get("model"),
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": openai_data.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": openai_data.get("usage", {}).get("completion_tokens", 0)
            }
        }

        # Log the API call
        duration_ms = int((time.time() - start_time) * 1000)
        log_manager.log_api_call('POST', '/v1/messages', 200, duration_ms, anthropic_request, anthropic_response)

        return jsonify(anthropic_response), 200

    except Exception as e:
        logger.error(f"Error in Anthropic Messages API: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        error_response = {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": str(e)
            }
        }
        log_manager.log_api_call('POST', '/v1/messages', 500, duration_ms, anthropic_request, error_response)
        return jsonify(error_response), 500


# Dashboard Routes
@app.route('/')
def dashboard():
    """Serve the dashboard."""
    return send_from_directory('dashboard', 'index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get proxy configuration."""
    return jsonify({
        'localPort': config.port,
        'localBaseUrl': f'http://localhost:{config.port}',
        'accessToken': config.proxy_access_token,
        'targetEndpoint': config.target_endpoint,
        'usePlaceholderMode': config.use_placeholder_mode,
        'devMode': DEV_MODE,
        'oauthConfigured': config.is_oauth_configured() and not DEV_MODE,
        'rbcSecurityAvailable': not DEV_MODE,
    })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get all logs."""
    return jsonify(log_manager.get_logs())


@app.route('/api/logs/api-calls', methods=['GET'])
def get_api_call_logs():
    """Get API call logs."""
    return jsonify(log_manager.get_api_calls())


@app.route('/api/logs/server-events', methods=['GET'])
def get_server_event_logs():
    """Get server event logs."""
    return jsonify(log_manager.get_server_events())


@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    """Clear all logs."""
    log_manager.clear_logs()
    return jsonify({'message': 'Logs cleared'})


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'devMode': DEV_MODE,
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    initialize_app()

    # Run the server
    app.run(
        host='0.0.0.0',
        port=config.port,
        debug=DEV_MODE,
        use_reloader=False  # Disable reloader to avoid double initialization
    )
