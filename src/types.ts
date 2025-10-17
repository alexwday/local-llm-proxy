export interface ProxyConfig {
  localPort: number;
  localBaseUrl: string;
  accessToken: string;
  targetEndpoint: string;
  targetApiKey?: string;
}

export interface ApiCallLog {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  requestHeaders: Record<string, string>;
  requestBody: any;
  responseStatus: number;
  responseBody: any;
  duration: number;
}

export interface ServerEventLog {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  details?: any;
}

// OpenAI Chat Completion Types (matching official API spec)
export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool' | 'function';
  content: string | null;
  name?: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  function_call?: FunctionCall;
}

export interface ToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
}

export interface FunctionCall {
  name: string;
  arguments: string;
}

export interface Tool {
  type: 'function';
  function: {
    name: string;
    description?: string;
    parameters?: Record<string, any>;
  };
}

export interface OpenAIChatRequest {
  // Required
  model: string;
  messages: ChatMessage[];

  // Sampling parameters
  temperature?: number; // 0-2, default 1
  top_p?: number; // 0-1, default 1
  n?: number; // default 1
  max_tokens?: number;
  max_completion_tokens?: number;

  // Streaming
  stream?: boolean; // default false
  stream_options?: {
    include_usage?: boolean;
  };

  // Stop sequences
  stop?: string | string[]; // max 4 sequences

  // Penalties
  presence_penalty?: number; // -2 to 2, default 0
  frequency_penalty?: number; // -2 to 2, default 0
  logit_bias?: Record<string, number>; // -100 to 100

  // Responses
  response_format?: {
    type: 'text' | 'json_object' | 'json_schema';
    json_schema?: {
      name: string;
      description?: string;
      schema?: Record<string, any>;
      strict?: boolean;
    };
  };

  // Debugging
  logprobs?: boolean; // default false
  top_logprobs?: number; // 0-20

  // Determinism
  seed?: number;

  // Function calling / Tools
  tools?: Tool[];
  tool_choice?: 'none' | 'auto' | 'required' | { type: 'function'; function: { name: string } };
  parallel_tool_calls?: boolean;

  // Deprecated function calling
  functions?: Array<{
    name: string;
    description?: string;
    parameters?: Record<string, any>;
  }>;
  function_call?: 'none' | 'auto' | { name: string };

  // User tracking
  user?: string;

  // OpenAI-specific
  service_tier?: 'auto' | 'default';
  store?: boolean;
  metadata?: Record<string, string>;
}

export interface LogProbsContent {
  token: string;
  logprob: number;
  bytes: number[] | null;
  top_logprobs: Array<{
    token: string;
    logprob: number;
    bytes: number[] | null;
  }>;
}

export interface OpenAIChatResponse {
  id: string;
  object: 'chat.completion' | 'chat.completion.chunk';
  created: number;
  model: string;
  system_fingerprint?: string;
  choices: Array<{
    index: number;
    message?: {
      role: 'assistant' | 'tool' | 'function';
      content: string | null;
      tool_calls?: ToolCall[];
      function_call?: FunctionCall;
    };
    delta?: {
      role?: 'assistant' | 'tool' | 'function';
      content?: string | null;
      tool_calls?: ToolCall[];
      function_call?: FunctionCall;
    };
    logprobs?: {
      content: LogProbsContent[] | null;
    } | null;
    finish_reason: 'stop' | 'length' | 'tool_calls' | 'content_filter' | 'function_call' | null;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    completion_tokens_details?: {
      reasoning_tokens?: number;
      accepted_prediction_tokens?: number;
      rejected_prediction_tokens?: number;
    };
    prompt_tokens_details?: {
      cached_tokens?: number;
      audio_tokens?: number;
    };
  };
}

// Legacy completions endpoint types
export interface OpenAICompletionRequest {
  model: string;
  prompt: string | string[];
  suffix?: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  n?: number;
  stream?: boolean;
  logprobs?: number;
  echo?: boolean;
  stop?: string | string[];
  presence_penalty?: number;
  frequency_penalty?: number;
  best_of?: number;
  logit_bias?: Record<string, number>;
  user?: string;
}

export interface OpenAICompletionResponse {
  id: string;
  object: 'text_completion';
  created: number;
  model: string;
  choices: Array<{
    text: string;
    index: number;
    logprobs: {
      tokens: string[];
      token_logprobs: number[];
      top_logprobs: Record<string, number>[];
      text_offset: number[];
    } | null;
    finish_reason: 'stop' | 'length' | 'content_filter' | null;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// Models endpoint types
export interface OpenAIModel {
  id: string;
  object: 'model';
  created: number;
  owned_by: string;
}

export interface OpenAIModelsResponse {
  object: 'list';
  data: OpenAIModel[];
}

// Error response type
export interface OpenAIError {
  error: {
    message: string;
    type: string;
    param: string | null;
    code: string | null;
  };
}
