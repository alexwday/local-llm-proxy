"""Configuration management for the proxy server."""

import os
import secrets


class Config:
    """Proxy configuration loaded from environment variables."""

    def __init__(self):
        # Proxy settings
        self.port = int(os.getenv('PROXY_PORT', '3000'))
        self.proxy_access_token = os.getenv('PROXY_ACCESS_TOKEN') or self._generate_token()

        # Target endpoint
        self.target_endpoint = os.getenv('TARGET_ENDPOINT', 'https://your-llm-endpoint.com/v1')
        self.target_api_key = os.getenv('TARGET_API_KEY')
        self.use_placeholder_mode = os.getenv('USE_PLACEHOLDER_MODE', 'false').lower() == 'true'

        # Model configuration
        self.available_models = self._parse_models(os.getenv('AVAILABLE_MODELS', 'gpt-4,gpt-4-turbo,gpt-4o,gpt-4o-mini,gpt-3.5-turbo'))
        self.default_model = os.getenv('DEFAULT_MODEL', 'gpt-4')
        self.default_small_model = os.getenv('DEFAULT_SMALL_MODEL', 'gpt-3.5-turbo')

        # OAuth settings
        self.oauth_token_endpoint = os.getenv('OAUTH_TOKEN_ENDPOINT')
        self.oauth_client_id = os.getenv('OAUTH_CLIENT_ID')
        self.oauth_client_secret = os.getenv('OAUTH_CLIENT_SECRET')
        self.oauth_scope = os.getenv('OAUTH_SCOPE')
        self.oauth_refresh_buffer_minutes = int(os.getenv('OAUTH_REFRESH_BUFFER_MINUTES', '5'))

    def _parse_models(self, models_str: str) -> list:
        """Parse comma-separated model list from environment."""
        return [m.strip() for m in models_str.split(',') if m.strip()]

    def _generate_token(self) -> str:
        """Generate a random access token."""
        return f"llm-proxy-{secrets.token_hex(32)}"

    def is_oauth_configured(self) -> bool:
        """Check if OAuth is configured."""
        return bool(
            self.oauth_token_endpoint and
            self.oauth_client_id and
            self.oauth_client_secret
        )

    def is_api_key_configured(self) -> bool:
        """Check if simple API key is configured."""
        return bool(self.target_api_key)
