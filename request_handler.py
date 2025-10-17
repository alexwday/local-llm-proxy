"""Request handler for OpenAI API endpoints."""

import time
import uuid
import logging
import requests
from typing import Optional, Dict, Any
from flask import jsonify

logger = logging.getLogger(__name__)


class RequestHandler:
    """Handles OpenAI API requests and forwards to target endpoint."""

    def __init__(self, config, oauth_manager, log_manager, dev_mode=False):
        self.config = config
        self.oauth_manager = oauth_manager
        self.log_manager = log_manager
        self.dev_mode = dev_mode

        # Build models list from config
        self.models = self._build_models_list()

    def _build_models_list(self):
        """Build models list from configuration."""
        models = []
        base_timestamp = 1687882410  # Base timestamp for model creation

        for i, model_id in enumerate(self.config.available_models):
            models.append({
                "id": model_id,
                "object": "model",
                "created": base_timestamp + (i * 1000000),  # Increment timestamp for each model
                "owned_by": "openai"
            })

        return models

    def list_models(self):
        """List available models."""
        return jsonify({
            "object": "list",
            "data": self.models
        })

    def get_model(self, model_id: str):
        """Get specific model details."""
        model = next((m for m in self.models if m["id"] == model_id), None)

        if not model:
            return jsonify({
                "error": {
                    "message": f"Model '{model_id}' not found",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_found"
                }
            }), 404

        return jsonify(model)

    def chat_completions(self, request_data: Dict):
        """Handle chat completion requests."""
        start_time = time.time()

        # Validate required fields
        if not request_data or not request_data.get('model'):
            error_response = jsonify({
                "error": {
                    "message": "you must provide a model parameter",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": None
                }
            })
            duration_ms = int((time.time() - start_time) * 1000)
            self.log_manager.log_api_call('POST', '/v1/chat/completions', 400, duration_ms, request_data, None)
            return error_response, 400

        if not request_data.get('messages'):
            error_response = jsonify({
                "error": {
                    "message": "you must provide a messages parameter",
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": None
                }
            })
            duration_ms = int((time.time() - start_time) * 1000)
            self.log_manager.log_api_call('POST', '/v1/chat/completions', 400, duration_ms, request_data, None)
            return error_response, 400

        # Check mode
        if self.config.use_placeholder_mode:
            return self._placeholder_chat_response(request_data, start_time)

        # Forward to target
        return self._forward_chat_request(request_data, start_time)

    def completions(self, request_data: Dict):
        """Handle text completion requests."""
        start_time = time.time()

        if not request_data or not request_data.get('model'):
            return jsonify({
                "error": {
                    "message": "you must provide a model parameter",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": None
                }
            }), 400

        if self.config.use_placeholder_mode:
            return self._placeholder_completion_response(request_data, start_time)

        return self._forward_completion_request(request_data, start_time)

    def _forward_chat_request(self, request_data: Dict, start_time: float):
        """Forward chat completion request to target endpoint."""
        try:
            target_url = f"{self.config.target_endpoint}/chat/completions"
            headers = {'Content-Type': 'application/json'}

            # Add authorization
            self._add_authorization_header(headers)

            logger.info(f"Forwarding request to: {target_url}")

            response = requests.post(
                target_url,
                json=request_data,
                headers=headers,
                timeout=120
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if not response.ok:
                logger.error(f"Target returned {response.status_code}")
                try:
                    error_data = response.json()
                except:
                    error_data = {"error": {"message": response.text or "Empty response from target"}}

                self.log_manager.log_api_call('POST', '/v1/chat/completions', response.status_code, duration_ms, request_data, error_data)
                return jsonify(error_data), response.status_code

            # Parse response JSON with better error handling
            try:
                response_data = response.json()
            except Exception as json_err:
                logger.error(f"Failed to parse target response as JSON: {json_err}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response body (first 500 chars): {response.text[:500]}")
                error_data = {
                    "error": {
                        "message": f"Target returned invalid JSON: {str(json_err)}",
                        "type": "invalid_response_error",
                        "response_preview": response.text[:200]
                    }
                }
                self.log_manager.log_api_call('POST', '/v1/chat/completions', 500, duration_ms, request_data, error_data)
                return jsonify(error_data), 500

            self.log_manager.log_api_call('POST', '/v1/chat/completions', 200, duration_ms, request_data, response_data)
            return jsonify(response_data), 200

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            error_data = {
                "error": {
                    "message": f"Failed to connect to target endpoint: {str(e)}",
                    "type": "connection_error",
                    "param": None,
                    "code": "target_connection_failed"
                }
            }
            self.log_manager.log_api_call('POST', '/v1/chat/completions', 500, duration_ms, request_data, error_data)
            return jsonify(error_data), 500

    def _forward_completion_request(self, request_data: Dict, start_time: float):
        """Forward text completion request to target endpoint."""
        try:
            target_url = f"{self.config.target_endpoint}/completions"
            headers = {'Content-Type': 'application/json'}

            self._add_authorization_header(headers)

            response = requests.post(
                target_url,
                json=request_data,
                headers=headers,
                timeout=120
            )

            if not response.ok:
                try:
                    error_data = response.json()
                except:
                    error_data = {"error": {"message": response.text}}

                return jsonify(error_data), response.status_code

            response_data = response.json()
            return jsonify(response_data), 200

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            return jsonify({
                "error": {
                    "message": f"Failed to connect to target endpoint: {str(e)}",
                    "type": "connection_error",
                    "param": None,
                    "code": "target_connection_failed"
                }
            }), 500

    def _add_authorization_header(self, headers: Dict[str, str]):
        """Add authorization header to request."""
        if self.dev_mode:
            # Dev mode: use mock token
            headers['Authorization'] = 'Bearer dev-mock-token'
            logger.debug("Using dev mock token")
            return

        # Priority 1: OAuth
        if self.oauth_manager:
            try:
                token = self.oauth_manager.get_token()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    logger.debug("Using OAuth token")
                    return
            except Exception as e:
                logger.error(f"Failed to get OAuth token: {e}")

        # Priority 2: Simple API key
        if self.config.is_api_key_configured():
            headers['Authorization'] = f'Bearer {self.config.target_api_key}'
            logger.debug("Using static API key")
            return

        logger.warning("No authentication configured for target endpoint")

    def _placeholder_chat_response(self, request_data: Dict, start_time: float):
        """Return placeholder chat completion response."""
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": request_data.get("model", self.config.default_model),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a placeholder response from the local LLM proxy. Configure TARGET_ENDPOINT to connect to your actual LLM service."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

        duration_ms = int((time.time() - start_time) * 1000)
        self.log_manager.log_api_call('POST', '/v1/chat/completions', 200, duration_ms, request_data, response)

        return jsonify(response), 200

    def _placeholder_completion_response(self, request_data: Dict, start_time: float):
        """Return placeholder text completion response."""
        completion_id = f"cmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        response = {
            "id": completion_id,
            "object": "text_completion",
            "created": created,
            "model": request_data.get("model", self.config.default_small_model),
            "choices": [{
                "text": "This is a placeholder response.",
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 10,
                "total_tokens": 15
            }
        }

        return jsonify(response), 200
