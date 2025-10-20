"""Request handler for OpenAI API endpoints."""

import time
import uuid
import logging
import requests
from typing import Optional, Dict, Any
from flask import jsonify, Response, stream_with_context

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

        # Strip temperature=0 if configured (some models don't support it)
        if self.config.strip_zero_temperature and request_data:
            temp = request_data.get('temperature')
            if temp is not None and temp == 0:
                logger.info(f"Removing temperature=0 (STRIP_ZERO_TEMPERATURE=true)")
                request_data.pop('temperature', None)

        # Inject max_tokens if not set (Codex doesn't send it, causing truncation)
        if request_data and 'max_tokens' not in request_data:
            default_max_tokens = self.config.max_tokens
            request_data['max_tokens'] = default_max_tokens
            logger.info(f"Injected max_tokens={default_max_tokens} (not set by client)")

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
            logger.debug("Using placeholder response")
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

            # Check if streaming is requested
            is_streaming = request_data.get('stream', False)

            # Log request details for debugging
            messages = request_data.get('messages', [])
            num_messages = len(messages)
            max_tokens_req = request_data.get('max_tokens', 'not set')
            model = request_data.get('model', 'not set')
            tools = request_data.get('tools', [])
            tool_choice = request_data.get('tool_choice', 'not set')

            # Check messages for tool_calls and tool results
            has_assistant_tool_calls = False
            has_tool_results = False
            for msg in messages:
                if msg.get('role') == 'assistant' and 'tool_calls' in msg:
                    has_assistant_tool_calls = True
                if msg.get('role') == 'tool':
                    has_tool_results = True

            # Estimate prompt size (rough approximation: 1 token ≈ 4 chars)
            total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
            estimated_prompt_tokens = total_chars // 4

            # Concise INFO logging for production
            tool_info = f", tools={len(tools)}" if tools else ""
            logger.info(f"→ {model} | msgs={num_messages}, max_tokens={max_tokens_req}{tool_info} | streaming={is_streaming}")

            # Detailed DEBUG logging
            if tools:
                logger.debug(f"Tools: {len(tools)} defined, choice={tool_choice}")
                for i, tool in enumerate(tools):
                    tool_name = tool.get('function', {}).get('name', 'unknown')
                    logger.debug(f"  Tool {i+1}: {tool_name}")

            if has_assistant_tool_calls:
                logger.debug(f"Message history includes assistant tool_calls")
            if has_tool_results:
                logger.debug(f"Message history includes tool results")

            logger.debug(f"Estimated prompt size: ~{estimated_prompt_tokens:,} tokens")

            # Warn if max_tokens not set
            if max_tokens_req == 'not set':
                logger.warning("!!! max_tokens NOT SET in request - gateway may use low default !!!")
                logger.warning("Codex config should set max_tokens (check ~/.codex/config.toml)")

            # For streaming, use longer timeout and keep connection alive
            if is_streaming:
                timeout_seconds = 600  # 10 minutes for long responses
            else:
                timeout_seconds = 120

            response = requests.post(
                target_url,
                json=request_data,
                headers=headers,
                timeout=timeout_seconds,
                stream=is_streaming  # Enable streaming if requested
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

            # Handle streaming responses
            if is_streaming:
                logger.debug("Starting to stream response from target...")

                def generate():
                    try:
                        chunk_count = 0
                        full_response_text = ""
                        actual_prompt_tokens = None  # Will be set when usage arrives
                        accumulated_tool_calls = {}  # Track tool calls by index
                        for chunk in response.iter_lines():
                            if chunk:
                                chunk_count += 1
                                if chunk_count == 1:
                                    logger.debug(f"First chunk received: {chunk[:100]}")
                                elif chunk_count % 50 == 0:
                                    logger.debug(f"Received {chunk_count} chunks so far...")

                                # Try to extract content from chunk for debugging
                                try:
                                    import json
                                    if chunk.startswith(b'data: ') and not b'[DONE]' in chunk:
                                        chunk_json = json.loads(chunk[6:])  # Skip "data: "
                                        if 'choices' in chunk_json and len(chunk_json['choices']) > 0:
                                            choice = chunk_json['choices'][0]
                                            delta = choice.get('delta', {})
                                            content = delta.get('content', '')
                                            if content:
                                                full_response_text += content

                                            # Check for tool calls (including empty arrays)
                                            if 'tool_calls' in delta:
                                                logger.debug(f"[CHUNK {chunk_count}] tool_calls in delta")
                                                if delta['tool_calls'] and len(delta['tool_calls']) > 0:
                                                    # Accumulate tool call data
                                                    for tc_delta in delta['tool_calls']:
                                                        tc_index = tc_delta.get('index', 0)
                                                        if tc_index not in accumulated_tool_calls:
                                                            accumulated_tool_calls[tc_index] = {
                                                                'id': tc_delta.get('id', ''),
                                                                'type': tc_delta.get('type', 'function'),
                                                                'function': {
                                                                    'name': '',
                                                                    'arguments': ''
                                                                }
                                                            }

                                                        # Update accumulated data
                                                        if 'id' in tc_delta:
                                                            accumulated_tool_calls[tc_index]['id'] = tc_delta['id']
                                                        if 'type' in tc_delta:
                                                            accumulated_tool_calls[tc_index]['type'] = tc_delta['type']
                                                        if 'function' in tc_delta:
                                                            if 'name' in tc_delta['function']:
                                                                accumulated_tool_calls[tc_index]['function']['name'] = tc_delta['function']['name']
                                                            if 'arguments' in tc_delta['function']:
                                                                accumulated_tool_calls[tc_index]['function']['arguments'] += tc_delta['function']['arguments']

                                                    logger.debug(f"[CHUNK {chunk_count}] Tool call data: {delta['tool_calls']}")

                                            # Check finish_reason
                                            finish_reason = choice.get('finish_reason')
                                            if finish_reason:
                                                logger.info(f"← finish_reason={finish_reason}")
                                                if finish_reason == 'tool_calls':
                                                    if accumulated_tool_calls:
                                                        tool_names = [tc.get('function', {}).get('name', '?') for tc in accumulated_tool_calls.values()]
                                                        logger.info(f"  Tool calls: {', '.join(tool_names)}")
                                                    logger.debug(f"Full choice: {json.dumps(choice, indent=2)}")
                                                elif finish_reason == 'length':
                                                    logger.error(f"Response TRUNCATED (finish_reason=length, max_tokens={max_tokens_req})")
                                                    if accumulated_tool_calls:
                                                        logger.error(f"  Incomplete tool calls detected!")
                                                    logger.debug(f"Response so far: {full_response_text[:200]}")

                                        # Log usage if present
                                        if 'usage' in chunk_json:
                                            usage = chunk_json['usage']
                                            prompt_tokens = usage.get('prompt_tokens', 0)
                                            comp_tokens = usage.get('completion_tokens', 0)
                                            total_tokens = usage.get('total_tokens', 0)
                                            actual_prompt_tokens = prompt_tokens

                                            logger.info(f"  Usage: {prompt_tokens:,} prompt + {comp_tokens:,} completion = {total_tokens:,} tokens")

                                            # Check for potential issues
                                            if prompt_tokens > 256000:
                                                logger.error(f"Prompt exceeds 256k limit: {prompt_tokens:,} tokens")
                                            elif prompt_tokens > 230000:
                                                logger.warning(f"Prompt approaching limit: {prompt_tokens:,}/256k tokens")

                                            if comp_tokens < 10 and not accumulated_tool_calls:
                                                logger.warning(f"Suspiciously short response: {comp_tokens} tokens")
                                except Exception as parse_error:
                                    # Log parsing errors instead of silently ignoring
                                    logger.debug(f"[CHUNK {chunk_count}] Could not parse chunk: {parse_error}")

                                # SSE format requires \n\n after each event
                                # iter_lines() strips newlines, so we add both back
                                yield chunk + b'\n\n'

                        logger.debug(f"Stream complete: {chunk_count} chunks, {len(full_response_text)} chars")

                        # Log accumulated tool calls at DEBUG level
                        if accumulated_tool_calls:
                            logger.debug(f"Accumulated {len(accumulated_tool_calls)} tool calls")
                            for idx, tc in accumulated_tool_calls.items():
                                func_name = tc.get('function', {}).get('name', 'unknown')
                                func_args = tc.get('function', {}).get('arguments', '')
                                logger.debug(f"  [{idx}] {func_name}: {func_args[:100]}")

                        if chunk_count == 0:
                            logger.warning("No chunks received from target!")

                        response.close()
                    except GeneratorExit:
                        logger.warning(f"Client disconnected ({chunk_count} chunks sent)")
                    except Exception as e:
                        logger.error(f"Streaming error: {e}")
                        logger.debug(f"Traceback:", exc_info=True)
                        # Send error as SSE
                        error_chunk = f'data: {{"error": {{"message": "{str(e)}"}}}}\n\n'
                        yield error_chunk.encode('utf-8')

                # Log streaming request (no response data yet)
                self.log_manager.log_api_call('POST', '/v1/chat/completions', 200, duration_ms, request_data, {"streaming": True})

                return Response(
                    stream_with_context(generate()),
                    content_type='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no',
                        'Connection': 'keep-alive'
                    }
                ), 200

            # Parse response JSON with better error handling (non-streaming)
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

            # Log non-streaming response
            if 'choices' in response_data and len(response_data['choices']) > 0:
                choice = response_data['choices'][0]
                message = choice.get('message', {})
                finish_reason = choice.get('finish_reason', 'unknown')

                logger.info(f"← finish_reason={finish_reason}")

                if 'tool_calls' in message:
                    tool_calls = message['tool_calls']
                    tool_names = [tc.get('function', {}).get('name', '?') for tc in tool_calls]
                    logger.info(f"  Tool calls: {', '.join(tool_names)}")

                if 'content' in message and message.get('content'):
                    content = message['content']
                    logger.debug(f"Content: {content[:100]}")

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
        is_streaming = request_data.get('stream', False)

        logger.info(f"Placeholder response - streaming: {is_streaming}")

        # Handle streaming placeholder response
        if is_streaming:
            import json

            def generate_placeholder_stream():
                logger.info("Starting placeholder stream generation...")

                # Send initial chunk with role
                chunk_role = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_data.get("model", self.config.default_model),
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None
                    }]
                }
                chunk_data = f"data: {json.dumps(chunk_role)}\n\n".encode('utf-8')
                logger.info(f"Sending role chunk: {chunk_data[:100]}")
                yield chunk_data

                # Send content in chunks (simulating streaming)
                message = "This is a placeholder streaming response from the local LLM proxy."
                words = message.split()
                logger.info(f"Sending {len(words)} content chunks...")
                for i, word in enumerate(words):
                    content = word + (" " if i < len(words) - 1 else "")
                    chunk_content = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request_data.get("model", self.config.default_model),
                        "choices": [{
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None
                        }]
                    }
                    chunk_data = f"data: {json.dumps(chunk_content)}\n\n".encode('utf-8')
                    if i == 0:
                        logger.info(f"First content chunk: {chunk_data[:100]}")
                    yield chunk_data

                # Send final chunk
                chunk_final = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_data.get("model", self.config.default_model),
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                chunk_data = f"data: {json.dumps(chunk_final)}\n\n".encode('utf-8')
                logger.info(f"Sending final chunk: {chunk_data[:100]}")
                yield chunk_data

                logger.info("Sending [DONE]")
                yield b"data: [DONE]\n\n"
                logger.info("Stream complete!")

            duration_ms = int((time.time() - start_time) * 1000)
            self.log_manager.log_api_call('POST', '/v1/chat/completions', 200, duration_ms, request_data, {"streaming": True, "placeholder": True})

            return Response(
                stream_with_context(generate_placeholder_stream()),
                content_type='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            ), 200

        # Non-streaming response
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
