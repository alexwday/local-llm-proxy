import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import {
  OpenAIChatRequest,
  OpenAIChatResponse,
  OpenAICompletionRequest,
  OpenAICompletionResponse,
  OpenAIModelsResponse,
  OpenAIError,
} from '../types';
import { config } from '../config';
import { logApiCall, logServerEvent } from '../logger';
import { forwardChatCompletionRequest, forwardCompletionRequest } from '../services/target-forwarder';
import { generateChatCompletionId, generateSystemFingerprint, generateCompletionId } from '../validators/response-validator';

const router = Router();

// Middleware to verify access token
function verifyToken(req: Request, res: Response, next: Function): void {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    const error: OpenAIError = {
      error: {
        message: 'You didn\'t provide an API key. You need to provide your API key in an Authorization header using Bearer auth (i.e. Authorization: Bearer YOUR_KEY)',
        type: 'invalid_request_error',
        param: null,
        code: 'invalid_api_key',
      },
    };
    res.status(401).json(error);
    return;
  }

  const token = authHeader.replace('Bearer ', '').trim();

  if (token !== config.accessToken) {
    const error: OpenAIError = {
      error: {
        message: 'Incorrect API key provided. You can find your API key at the dashboard.',
        type: 'invalid_request_error',
        param: null,
        code: 'invalid_api_key',
      },
    };
    res.status(401).json(error);
    return;
  }

  next();
}

// Apply token verification to all routes
router.use(verifyToken);

// GET /v1/models - List available models
router.get('/models', (req: Request, res: Response) => {
  const startTime = Date.now();

  const response: OpenAIModelsResponse = {
    object: 'list',
    data: [
      {
        id: 'gpt-4',
        object: 'model',
        created: 1687882411,
        owned_by: 'openai',
      },
      {
        id: 'gpt-4-turbo',
        object: 'model',
        created: 1706037612,
        owned_by: 'system',
      },
      {
        id: 'gpt-4-turbo-preview',
        object: 'model',
        created: 1706037612,
        owned_by: 'system',
      },
      {
        id: 'gpt-4o',
        object: 'model',
        created: 1715367049,
        owned_by: 'system',
      },
      {
        id: 'gpt-4o-mini',
        object: 'model',
        created: 1721172741,
        owned_by: 'system',
      },
      {
        id: 'gpt-3.5-turbo',
        object: 'model',
        created: 1677610602,
        owned_by: 'openai',
      },
      {
        id: 'gpt-3.5-turbo-16k',
        object: 'model',
        created: 1683758102,
        owned_by: 'openai-internal',
      },
    ],
  };

  logApiCall({
    method: req.method,
    path: req.path,
    requestHeaders: req.headers as Record<string, string>,
    requestBody: null,
    responseStatus: 200,
    responseBody: response,
    duration: Date.now() - startTime,
  });

  res.json(response);
});

// GET /v1/models/:model - Retrieve a specific model
router.get('/models/:model', (req: Request, res: Response) => {
  const startTime = Date.now();
  const modelId = req.params.model;

  const response = {
    id: modelId,
    object: 'model',
    created: 1687882411,
    owned_by: 'openai',
  };

  logApiCall({
    method: req.method,
    path: req.path,
    requestHeaders: req.headers as Record<string, string>,
    requestBody: null,
    responseStatus: 200,
    responseBody: response,
    duration: Date.now() - startTime,
  });

  res.json(response);
});

// POST /v1/chat/completions - Chat completion (main endpoint)
router.post('/chat/completions', async (req: Request, res: Response) => {
  const startTime = Date.now();
  const requestBody: OpenAIChatRequest = req.body;

  // Validate required fields
  if (!requestBody.model) {
    const error: OpenAIError = {
      error: {
        message: 'you must provide a model parameter',
        type: 'invalid_request_error',
        param: 'model',
        code: null,
      },
    };
    res.status(400).json(error);
    return;
  }

  if (!requestBody.messages || !Array.isArray(requestBody.messages) || requestBody.messages.length === 0) {
    const error: OpenAIError = {
      error: {
        message: 'messages must be an array with at least one message',
        type: 'invalid_request_error',
        param: 'messages',
        code: null,
      },
    };
    res.status(400).json(error);
    return;
  }

  // Check if we should forward to target or use placeholder
  if (!config.usePlaceholderMode) {
    // Forward request to target endpoint
    logServerEvent('info', 'Forwarding chat completion request to target endpoint');

    const result = await forwardChatCompletionRequest(requestBody);

    if (!result.success) {
      // Log the failed request
      logApiCall({
        method: req.method,
        path: req.path,
        requestHeaders: req.headers as Record<string, string>,
        requestBody,
        responseStatus: 500,
        responseBody: result.error,
        duration: result.duration,
      });

      res.status(500).json(result.error);
      return;
    }

    // Log successful forwarded request
    logApiCall({
      method: req.method,
      path: req.path,
      requestHeaders: req.headers as Record<string, string>,
      requestBody,
      responseStatus: 200,
      responseBody: result.data,
      duration: Date.now() - startTime,
    });

    res.json(result.data);
    return;
  }

  // Placeholder mode: generate mock response
  const n = requestBody.n || 1;

  const choices = Array.from({ length: n }, (_, index) => ({
    index,
    message: {
      role: 'assistant' as const,
      content: `This is a placeholder response from the local LLM proxy. The actual LLM endpoint integration will replace this message with real completions. [Completion ${index + 1}/${n}]`,
    },
    logprobs: requestBody.logprobs ? { content: null } : null,
    finish_reason: 'stop' as const,
  }));

  const response: OpenAIChatResponse = {
    id: generateChatCompletionId(),
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model: requestBody.model,
    system_fingerprint: generateSystemFingerprint(),
    choices,
    usage: {
      prompt_tokens: 10,
      completion_tokens: 25 * n,
      total_tokens: 10 + (25 * n),
    },
  };

  logApiCall({
    method: req.method,
    path: req.path,
    requestHeaders: req.headers as Record<string, string>,
    requestBody,
    responseStatus: 200,
    responseBody: response,
    duration: Date.now() - startTime,
  });

  res.json(response);
});

// POST /v1/completions - Text completion (legacy)
router.post('/completions', async (req: Request, res: Response) => {
  const startTime = Date.now();
  const requestBody: OpenAICompletionRequest = req.body;

  // Validate required fields
  if (!requestBody.model) {
    const error: OpenAIError = {
      error: {
        message: 'you must provide a model parameter',
        type: 'invalid_request_error',
        param: 'model',
        code: null,
      },
    };
    res.status(400).json(error);
    return;
  }

  if (!requestBody.prompt) {
    const error: OpenAIError = {
      error: {
        message: 'you must provide a prompt',
        type: 'invalid_request_error',
        param: 'prompt',
        code: null,
      },
    };
    res.status(400).json(error);
    return;
  }

  // Check if we should forward to target or use placeholder
  if (!config.usePlaceholderMode) {
    logServerEvent('info', 'Forwarding completion request to target endpoint');

    const result = await forwardCompletionRequest(requestBody);

    if (!result.success) {
      logApiCall({
        method: req.method,
        path: req.path,
        requestHeaders: req.headers as Record<string, string>,
        requestBody: req.body,
        responseStatus: 500,
        responseBody: result.error,
        duration: result.duration,
      });

      res.status(500).json(result.error);
      return;
    }

    logApiCall({
      method: req.method,
      path: req.path,
      requestHeaders: req.headers as Record<string, string>,
      requestBody: req.body,
      responseStatus: 200,
      responseBody: result.data,
      duration: Date.now() - startTime,
    });

    res.json(result.data);
    return;
  }

  // Placeholder mode
  const n = requestBody.n || 1;
  const logprobs = requestBody.logprobs;

  const choices = Array.from({ length: n }, (_, index) => ({
    text: `This is a placeholder text completion response. [Completion ${index + 1}/${n}]`,
    index,
    logprobs: logprobs ? {
      tokens: [],
      token_logprobs: [],
      top_logprobs: [],
      text_offset: [],
    } : null,
    finish_reason: 'stop' as const,
  }));

  const response: OpenAICompletionResponse = {
    id: generateCompletionId(),
    object: 'text_completion',
    created: Math.floor(Date.now() / 1000),
    model: requestBody.model,
    choices,
    usage: {
      prompt_tokens: 5,
      completion_tokens: 7 * n,
      total_tokens: 5 + (7 * n),
    },
  };

  logApiCall({
    method: req.method,
    path: req.path,
    requestHeaders: req.headers as Record<string, string>,
    requestBody: req.body,
    responseStatus: 200,
    responseBody: response,
    duration: Date.now() - startTime,
  });

  res.json(response);
});

export default router;
