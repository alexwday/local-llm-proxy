import { ProxyConfig } from './types';
import { randomBytes } from 'crypto';
import { OAuthConfig } from './services/oauth-manager';

function generateAccessToken(): string {
  return 'llm-proxy-' + randomBytes(32).toString('hex');
}

/**
 * Load configuration from environment variables or use defaults
 */
function loadConfig() {
  // Proxy access token (static, used by your clients)
  // Can be set via env var for production, or auto-generated for dev
  const accessToken = process.env.PROXY_ACCESS_TOKEN || generateAccessToken();

  // Local proxy settings
  const localPort = parseInt(process.env.PROXY_PORT || '3000');
  const localBaseUrl = process.env.PROXY_BASE_URL || `http://localhost:${localPort}`;

  // Target endpoint settings
  const targetEndpoint = process.env.TARGET_ENDPOINT || 'https://your-llm-endpoint.com/v1';
  const targetApiKey = process.env.TARGET_API_KEY; // Optional: simple API key auth

  // OAuth settings (if using OAuth instead of simple API key)
  const oauthTokenEndpoint = process.env.OAUTH_TOKEN_ENDPOINT;
  const oauthClientId = process.env.OAUTH_CLIENT_ID;
  const oauthClientSecret = process.env.OAUTH_CLIENT_SECRET;
  const oauthScope = process.env.OAUTH_SCOPE;
  const oauthRefreshBufferMinutes = parseInt(process.env.OAUTH_REFRESH_BUFFER_MINUTES || '5');

  // Mode setting
  const usePlaceholderMode = process.env.USE_PLACEHOLDER_MODE === 'true' ||
                             (!process.env.TARGET_ENDPOINT && !oauthTokenEndpoint);

  return {
    // Proxy settings (static for clients)
    localPort,
    localBaseUrl,
    accessToken,

    // Target endpoint
    targetEndpoint,
    targetApiKey,

    // OAuth configuration
    oauth: (oauthTokenEndpoint && oauthClientId && oauthClientSecret) ? {
      tokenEndpoint: oauthTokenEndpoint,
      clientId: oauthClientId,
      clientSecret: oauthClientSecret,
      scope: oauthScope,
      grantType: 'client_credentials',
      refreshBufferMs: oauthRefreshBufferMinutes * 60 * 1000,
    } as OAuthConfig : undefined,

    // Mode
    usePlaceholderMode,
  };
}

export type Config = ReturnType<typeof loadConfig>;

export const config = loadConfig();

export function getConfig(): Config {
  return { ...config };
}

export function updateConfig(updates: Partial<Config>): void {
  Object.assign(config, updates);
}

/**
 * Check if OAuth is configured
 */
export function isOAuthConfigured(): boolean {
  return config.oauth !== undefined;
}

/**
 * Check if simple API key auth is configured
 */
export function isApiKeyConfigured(): boolean {
  return config.targetApiKey !== undefined && config.targetApiKey !== '';
}
