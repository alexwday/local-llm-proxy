import https from 'https';
import { config, isOAuthConfigured, isApiKeyConfigured } from '../config';
import { logServerEvent } from '../logger';
import {
  validateAndNormalizeChatResponse,
  validateAndNormalizeCompletionResponse,
  isOpenAICompatibleResponse,
} from '../validators/response-validator';
import { OpenAIChatRequest, OpenAICompletionRequest, OpenAIError } from '../types';
import { getOAuthManager } from './oauth-manager';
import { getSSLOptions, isSSLConfigured } from './rbc-security';

/**
 * Forwards a chat completion request to the target LLM endpoint
 * and validates/normalizes the response
 */
export async function forwardChatCompletionRequest(
  request: OpenAIChatRequest
): Promise<{ success: boolean; data?: any; error?: OpenAIError; duration: number }> {
  const startTime = Date.now();

  try {
    // Check if target endpoint is configured
    if (!config.targetEndpoint || config.targetEndpoint === 'https://your-llm-endpoint.com/v1') {
      logServerEvent('warn', 'Target endpoint not configured, using placeholder response');
      return {
        success: false,
        error: {
          error: {
            message: 'Target LLM endpoint not configured. Please set targetEndpoint in config.',
            type: 'configuration_error',
            param: null,
            code: 'no_target_endpoint',
          },
        },
        duration: Date.now() - startTime,
      };
    }

    // Prepare the request
    const targetUrl = `${config.targetEndpoint}/chat/completions`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add authorization header
    await addAuthorizationHeader(headers);

    logServerEvent('info', `Forwarding request to target: ${targetUrl}`);

    // Create HTTPS agent with SSL options if configured
    const fetchOptions: RequestInit = {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    };

    // Add HTTPS agent with SSL options if needed
    if (isSSLConfigured()) {
      const sslOptions = getSSLOptions();
      const httpsAgent = new https.Agent(sslOptions);
      // @ts-ignore - fetch accepts agent in Node.js
      fetchOptions.agent = httpsAgent;
      logServerEvent('info', 'Using custom SSL configuration for request');
    }

    // Make the request to target endpoint
    const response = await fetch(targetUrl, fetchOptions);

    const duration = Date.now() - startTime;

    // Handle non-200 responses
    if (!response.ok) {
      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = { error: { message: await response.text() } };
      }

      logServerEvent('error', `Target endpoint returned ${response.status}`, errorData);

      return {
        success: false,
        error: {
          error: {
            message: errorData.error?.message || `Target endpoint returned status ${response.status}`,
            type: errorData.error?.type || 'target_endpoint_error',
            param: errorData.error?.param || null,
            code: errorData.error?.code || `http_${response.status}`,
          },
        },
        duration,
      };
    }

    // Parse response
    const responseData = await response.json();

    // Check if response is already OpenAI-compatible
    if (isOpenAICompatibleResponse(responseData)) {
      logServerEvent('info', 'Target endpoint returned OpenAI-compatible response');
      return {
        success: true,
        data: responseData,
        duration,
      };
    }

    // Validate and normalize the response
    logServerEvent('info', 'Normalizing target endpoint response to OpenAI format');
    const validation = validateAndNormalizeChatResponse(responseData, request);

    if (!validation.valid) {
      logServerEvent('error', 'Failed to validate target response', validation.error);
      return {
        success: false,
        error: validation.error,
        duration,
      };
    }

    return {
      success: true,
      data: validation.normalized,
      duration,
    };
  } catch (error) {
    const duration = Date.now() - startTime;
    logServerEvent('error', 'Error forwarding request to target', {
      error: error instanceof Error ? error.message : String(error),
    });

    return {
      success: false,
      error: {
        error: {
          message: `Failed to connect to target endpoint: ${error instanceof Error ? error.message : String(error)}`,
          type: 'connection_error',
          param: null,
          code: 'target_connection_failed',
        },
      },
      duration,
    };
  }
}

/**
 * Forwards a text completion request to the target LLM endpoint
 */
export async function forwardCompletionRequest(
  request: OpenAICompletionRequest
): Promise<{ success: boolean; data?: any; error?: OpenAIError; duration: number }> {
  const startTime = Date.now();

  try {
    if (!config.targetEndpoint || config.targetEndpoint === 'https://your-llm-endpoint.com/v1') {
      return {
        success: false,
        error: {
          error: {
            message: 'Target LLM endpoint not configured',
            type: 'configuration_error',
            param: null,
            code: 'no_target_endpoint',
          },
        },
        duration: Date.now() - startTime,
      };
    }

    const targetUrl = `${config.targetEndpoint}/completions`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    await addAuthorizationHeader(headers);

    // Create HTTPS agent with SSL options if configured
    const fetchOptions: RequestInit = {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    };

    // Add HTTPS agent with SSL options if needed
    if (isSSLConfigured()) {
      const sslOptions = getSSLOptions();
      const httpsAgent = new https.Agent(sslOptions);
      // @ts-ignore - fetch accepts agent in Node.js
      fetchOptions.agent = httpsAgent;
    }

    const response = await fetch(targetUrl, fetchOptions);

    const duration = Date.now() - startTime;

    if (!response.ok) {
      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = { error: { message: await response.text() } };
      }

      return {
        success: false,
        error: {
          error: {
            message: errorData.error?.message || `Target endpoint returned status ${response.status}`,
            type: errorData.error?.type || 'target_endpoint_error',
            param: errorData.error?.param || null,
            code: errorData.error?.code || `http_${response.status}`,
          },
        },
        duration,
      };
    }

    const responseData = await response.json();

    if (responseData.object === 'text_completion') {
      return {
        success: true,
        data: responseData,
        duration,
      };
    }

    const validation = validateAndNormalizeCompletionResponse(responseData, request);

    if (!validation.valid) {
      return {
        success: false,
        error: validation.error,
        duration,
      };
    }

    return {
      success: true,
      data: validation.normalized,
      duration,
    };
  } catch (error) {
    const duration = Date.now() - startTime;
    return {
      success: false,
      error: {
        error: {
          message: `Failed to connect to target endpoint: ${error instanceof Error ? error.message : String(error)}`,
          type: 'connection_error',
          param: null,
          code: 'target_connection_failed',
        },
      },
      duration,
    };
  }
}


/**
 * Helper function to add authorization header based on configuration
 * Supports both OAuth and simple API key authentication
 */
async function addAuthorizationHeader(headers: Record<string, string>): Promise<void> {
  // Priority 1: OAuth (dynamic token)
  if (isOAuthConfigured()) {
    const oauthManager = getOAuthManager();
    if (oauthManager) {
      try {
        const token = await oauthManager.getAccessToken();
        headers["Authorization"] = `Bearer ${token}`;
        logServerEvent("info", "Using OAuth token for target authentication");
        return;
      } catch (error) {
        logServerEvent("error", "Failed to get OAuth token", {
          error: error instanceof Error ? error.message : String(error),
        });
        throw new Error("OAuth token unavailable");
      }
    }
  }

  // Priority 2: Simple API key
  if (isApiKeyConfigured() && config.targetApiKey) {
    headers["Authorization"] = `Bearer ${config.targetApiKey}`;
    logServerEvent("info", "Using static API key for target authentication");
    return;
  }

  // No authentication configured
  logServerEvent("warn", "No authentication configured for target endpoint");
}

