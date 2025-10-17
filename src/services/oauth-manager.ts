import { logServerEvent } from '../logger';

export interface OAuthConfig {
  tokenEndpoint: string;
  clientId: string;
  clientSecret: string;
  scope?: string;
  grantType?: string; // default: 'client_credentials'
  refreshBufferMs?: number; // default: 5 minutes before expiry
}

export interface OAuthToken {
  accessToken: string;
  expiresAt: number; // Unix timestamp in ms
  tokenType: string;
}

/**
 * OAuth Token Manager
 * Handles automatic token fetching and refreshing for target endpoint authentication
 */
export class OAuthManager {
  private config: OAuthConfig;
  private currentToken: OAuthToken | null = null;
  private refreshTimer: NodeJS.Timeout | null = null;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<void> | null = null;

  constructor(config: OAuthConfig) {
    this.config = {
      grantType: 'client_credentials',
      refreshBufferMs: 5 * 60 * 1000, // 5 minutes default
      ...config,
    };
  }

  /**
   * Initialize the OAuth manager and fetch the first token
   */
  async initialize(): Promise<void> {
    logServerEvent('info', 'Initializing OAuth token manager', {
      tokenEndpoint: this.config.tokenEndpoint,
      clientId: this.config.clientId,
    });

    await this.refreshToken();
  }

  /**
   * Get a valid access token, refreshing if necessary
   */
  async getAccessToken(): Promise<string> {
    // If no token, fetch one
    if (!this.currentToken) {
      await this.refreshToken();
      return this.currentToken!.accessToken;
    }

    // If token is about to expire or expired, refresh
    const now = Date.now();
    const bufferMs = this.config.refreshBufferMs || 5 * 60 * 1000;

    if (now >= this.currentToken.expiresAt - bufferMs) {
      // If already refreshing, wait for that to complete
      if (this.isRefreshing && this.refreshPromise) {
        await this.refreshPromise;
      } else {
        await this.refreshToken();
      }
    }

    return this.currentToken!.accessToken;
  }

  /**
   * Fetch a new access token from the OAuth endpoint
   */
  private async refreshToken(): Promise<void> {
    // Prevent concurrent refresh attempts
    if (this.isRefreshing) {
      if (this.refreshPromise) {
        return this.refreshPromise;
      }
    }

    this.isRefreshing = true;
    this.refreshPromise = this.doRefresh();

    try {
      await this.refreshPromise;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  /**
   * Actual token refresh logic
   */
  private async doRefresh(): Promise<void> {
    try {
      logServerEvent('info', 'Fetching new OAuth token', {
        endpoint: this.config.tokenEndpoint,
      });

      // Prepare OAuth request body
      const body = new URLSearchParams({
        grant_type: this.config.grantType || 'client_credentials',
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
      });

      // Add scope if provided
      if (this.config.scope) {
        body.append('scope', this.config.scope);
      }

      // Make OAuth token request
      const response = await fetch(this.config.tokenEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: body.toString(),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`OAuth token request failed: ${response.status} ${errorText}`);
      }

      const data = await response.json();

      // Validate response
      if (!data.access_token) {
        throw new Error('OAuth response missing access_token field');
      }

      // Calculate expiry time
      // expires_in is typically in seconds
      const expiresInMs = (data.expires_in || 3600) * 1000;
      const expiresAt = Date.now() + expiresInMs;

      // Store the token
      this.currentToken = {
        accessToken: data.access_token,
        expiresAt,
        tokenType: data.token_type || 'Bearer',
      };

      logServerEvent('info', 'OAuth token acquired successfully', {
        expiresIn: data.expires_in,
        expiresAt: new Date(expiresAt).toISOString(),
        tokenType: this.currentToken.tokenType,
      });

      // Schedule next refresh
      this.scheduleRefresh();
    } catch (error) {
      logServerEvent('error', 'Failed to refresh OAuth token', {
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  }

  /**
   * Schedule the next token refresh
   */
  private scheduleRefresh(): void {
    // Clear existing timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }

    if (!this.currentToken) {
      return;
    }

    // Calculate when to refresh (with buffer)
    const now = Date.now();
    const bufferMs = this.config.refreshBufferMs || 5 * 60 * 1000;
    const refreshAt = this.currentToken.expiresAt - bufferMs;
    const delay = Math.max(0, refreshAt - now);

    logServerEvent('info', 'Scheduled next OAuth token refresh', {
      currentTime: new Date(now).toISOString(),
      refreshAt: new Date(refreshAt).toISOString(),
      delayMs: delay,
      delayMinutes: Math.round(delay / 60000),
    });

    this.refreshTimer = setTimeout(() => {
      this.refreshToken().catch((error) => {
        logServerEvent('error', 'Scheduled OAuth token refresh failed', {
          error: error instanceof Error ? error.message : String(error),
        });
        // Try again in 1 minute on failure
        setTimeout(() => {
          this.refreshToken();
        }, 60000);
      });
    }, delay);
  }

  /**
   * Get the current token info (for debugging/monitoring)
   */
  getTokenInfo(): { hasToken: boolean; expiresAt?: string; isExpired?: boolean } {
    if (!this.currentToken) {
      return { hasToken: false };
    }

    const now = Date.now();
    return {
      hasToken: true,
      expiresAt: new Date(this.currentToken.expiresAt).toISOString(),
      isExpired: now >= this.currentToken.expiresAt,
    };
  }

  /**
   * Force a token refresh (useful for testing or error recovery)
   */
  async forceRefresh(): Promise<void> {
    logServerEvent('info', 'Forcing OAuth token refresh');
    this.currentToken = null;
    await this.refreshToken();
  }

  /**
   * Cleanup on shutdown
   */
  destroy(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.currentToken = null;
    logServerEvent('info', 'OAuth manager destroyed');
  }
}

// Singleton instance
let oauthManagerInstance: OAuthManager | null = null;

/**
 * Initialize the global OAuth manager
 */
export async function initializeOAuth(config: OAuthConfig): Promise<void> {
  if (oauthManagerInstance) {
    oauthManagerInstance.destroy();
  }

  oauthManagerInstance = new OAuthManager(config);
  await oauthManagerInstance.initialize();
}

/**
 * Get the current OAuth manager instance
 */
export function getOAuthManager(): OAuthManager | null {
  return oauthManagerInstance;
}

/**
 * Check if OAuth is configured and initialized
 */
export function isOAuthEnabled(): boolean {
  return oauthManagerInstance !== null;
}
