import { OpenAIChatResponse, OpenAICompletionResponse, OpenAIError } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { logServerEvent } from '../logger';

/**
 * Validates and normalizes a chat completion response from the target endpoint
 * to ensure it matches OpenAI's format exactly
 */
export function validateAndNormalizeChatResponse(
  response: any,
  originalRequest: any
): { valid: boolean; normalized?: OpenAIChatResponse; error?: OpenAIError } {
  try {
    // Check if response is an object
    if (!response || typeof response !== 'object') {
      return {
        valid: false,
        error: {
          error: {
            message: 'Target endpoint returned invalid response format (not an object)',
            type: 'invalid_response_error',
            param: null,
            code: 'invalid_target_response',
          },
        },
      };
    }

    // Check for error responses from target
    if (response.error) {
      logServerEvent('warn', 'Target endpoint returned error', response.error);
      return {
        valid: false,
        error: {
          error: {
            message: response.error.message || 'Target endpoint returned an error',
            type: response.error.type || 'target_endpoint_error',
            param: response.error.param || null,
            code: response.error.code || null,
          },
        },
      };
    }

    // Normalize the response to OpenAI format
    const normalized: OpenAIChatResponse = {
      id: response.id || generateChatCompletionId(),
      object: response.object || 'chat.completion',
      created: response.created || Math.floor(Date.now() / 1000),
      model: response.model || originalRequest.model,
      system_fingerprint: response.system_fingerprint || undefined,
      choices: [],
      usage: undefined,
    };

    // Validate and normalize choices
    if (!response.choices || !Array.isArray(response.choices)) {
      return {
        valid: false,
        error: {
          error: {
            message: 'Target endpoint response missing "choices" array',
            type: 'invalid_response_error',
            param: 'choices',
            code: 'missing_choices',
          },
        },
      };
    }

    if (response.choices.length === 0) {
      return {
        valid: false,
        error: {
          error: {
            message: 'Target endpoint returned empty choices array',
            type: 'invalid_response_error',
            param: 'choices',
            code: 'empty_choices',
          },
        },
      };
    }

    // Normalize each choice
    normalized.choices = response.choices.map((choice: any, index: number) => {
      const normalizedChoice: any = {
        index: choice.index !== undefined ? choice.index : index,
        finish_reason: choice.finish_reason || 'stop',
      };

      // Handle message (non-streaming)
      if (choice.message) {
        normalizedChoice.message = {
          role: choice.message.role || 'assistant',
          content: choice.message.content !== undefined ? choice.message.content : null,
          tool_calls: choice.message.tool_calls || undefined,
          function_call: choice.message.function_call || undefined,
        };
      } else if (choice.delta) {
        // Handle delta (streaming)
        normalizedChoice.delta = {
          role: choice.delta.role || undefined,
          content: choice.delta.content || undefined,
          tool_calls: choice.delta.tool_calls || undefined,
          function_call: choice.delta.function_call || undefined,
        };
      } else {
        // Missing both message and delta - try to infer
        if (choice.text !== undefined) {
          // Legacy format or completions endpoint
          normalizedChoice.message = {
            role: 'assistant',
            content: choice.text,
          };
        } else {
          logServerEvent('warn', 'Choice missing both message and delta', { choice, index });
          normalizedChoice.message = {
            role: 'assistant',
            content: null,
          };
        }
      }

      // Add logprobs if present
      if (choice.logprobs !== undefined) {
        normalizedChoice.logprobs = choice.logprobs;
      }

      return normalizedChoice;
    });

    // Validate and normalize usage
    if (response.usage) {
      normalized.usage = {
        prompt_tokens: response.usage.prompt_tokens || 0,
        completion_tokens: response.usage.completion_tokens || 0,
        total_tokens: response.usage.total_tokens || 0,
        completion_tokens_details: response.usage.completion_tokens_details || undefined,
        prompt_tokens_details: response.usage.prompt_tokens_details || undefined,
      };
    } else {
      // Estimate usage if not provided
      logServerEvent('warn', 'Target endpoint did not provide usage information, estimating');
      normalized.usage = {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
      };
    }

    return { valid: true, normalized };
  } catch (error) {
    logServerEvent('error', 'Error validating target response', { error: String(error) });
    return {
      valid: false,
      error: {
        error: {
          message: `Failed to validate target response: ${error instanceof Error ? error.message : String(error)}`,
          type: 'validation_error',
          param: null,
          code: 'response_validation_failed',
        },
      },
    };
  }
}

/**
 * Validates and normalizes a text completion response from the target endpoint
 */
export function validateAndNormalizeCompletionResponse(
  response: any,
  originalRequest: any
): { valid: boolean; normalized?: OpenAICompletionResponse; error?: OpenAIError } {
  try {
    if (!response || typeof response !== 'object') {
      return {
        valid: false,
        error: {
          error: {
            message: 'Target endpoint returned invalid response format',
            type: 'invalid_response_error',
            param: null,
            code: 'invalid_target_response',
          },
        },
      };
    }

    if (response.error) {
      return {
        valid: false,
        error: {
          error: {
            message: response.error.message || 'Target endpoint returned an error',
            type: response.error.type || 'target_endpoint_error',
            param: response.error.param || null,
            code: response.error.code || null,
          },
        },
      };
    }

    const normalized: OpenAICompletionResponse = {
      id: response.id || generateCompletionId(),
      object: 'text_completion',
      created: response.created || Math.floor(Date.now() / 1000),
      model: response.model || originalRequest.model,
      choices: [],
      usage: {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0,
      },
    };

    if (!response.choices || !Array.isArray(response.choices) || response.choices.length === 0) {
      return {
        valid: false,
        error: {
          error: {
            message: 'Target endpoint response missing or empty "choices" array',
            type: 'invalid_response_error',
            param: 'choices',
            code: 'missing_choices',
          },
        },
      };
    }

    normalized.choices = response.choices.map((choice: any, index: number) => ({
      text: choice.text || choice.message?.content || '',
      index: choice.index !== undefined ? choice.index : index,
      logprobs: choice.logprobs || null,
      finish_reason: choice.finish_reason || 'stop',
    }));

    if (response.usage) {
      normalized.usage = {
        prompt_tokens: response.usage.prompt_tokens || 0,
        completion_tokens: response.usage.completion_tokens || 0,
        total_tokens: response.usage.total_tokens || 0,
      };
    }

    return { valid: true, normalized };
  } catch (error) {
    return {
      valid: false,
      error: {
        error: {
          message: `Failed to validate target response: ${error instanceof Error ? error.message : String(error)}`,
          type: 'validation_error',
          param: null,
          code: 'response_validation_failed',
        },
      },
    };
  }
}

/**
 * Checks if a response looks like an OpenAI-compatible format
 */
export function isOpenAICompatibleResponse(response: any): boolean {
  return (
    response &&
    typeof response === 'object' &&
    (response.object === 'chat.completion' ||
      response.object === 'text_completion' ||
      response.object === 'chat.completion.chunk') &&
    Array.isArray(response.choices)
  );
}

/**
 * Generates a chat completion ID matching OpenAI's format
 */
export function generateChatCompletionId(): string {
  return 'chatcmpl-' + uuidv4().replace(/-/g, '');
}

/**
 * Generates a completion ID matching OpenAI's format
 */
export function generateCompletionId(): string {
  return 'cmpl-' + uuidv4().replace(/-/g, '');
}

/**
 * Generates a system fingerprint
 */
export function generateSystemFingerprint(): string {
  return 'fp_' + Math.random().toString(36).substring(2, 15);
}
