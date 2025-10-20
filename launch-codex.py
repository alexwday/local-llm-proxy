#!/usr/bin/env python3
"""
Launch OpenAI Codex CLI with proxy configuration.

This script:
1. Enables RBC Security SSL certificates
2. Configures OpenAI Codex CLI to use the local proxy
3. Launches Codex CLI with custom endpoint using OpenAI native format

Key difference from launch-claude.py:
- OpenAI Codex CLI uses OpenAI format natively (not Anthropic format)
- Requests go to /v1/chat/completions endpoint directly
- No need for format conversion - bypasses Anthropic formatting in proxy

Prerequisites:
- The proxy server must be running (./run.sh or ./run-dev.sh)
- OpenAI Codex CLI installed (npm install -g @openai/codex)
- rbc_security package installed (pip install rbc_security)

Usage:
    python3 launch-codex.py
"""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()


def setup_rbc_security():
    """Enable RBC Security SSL certificates."""
    try:
        import rbc_security
        logger.info("Enabling RBC Security certificates...")
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


def check_proxy_running():
    """Check if the proxy server is running."""
    import requests

    proxy_url = f"http://localhost:{os.getenv('PROXY_PORT', '3000')}"

    try:
        response = requests.get(f"{proxy_url}/health", timeout=2)
        if response.ok:
            logger.info(f"✓ Proxy server is running at {proxy_url}")
            return True
    except:
        pass

    logger.error(f"✗ Proxy server is not running at {proxy_url}")
    logger.error("Please start the proxy server first:")
    logger.error("  ./run-dev.sh  (for development mode)")
    logger.error("  ./run.sh      (for production mode)")
    return False


def update_codex_config(proxy_port: str, proxy_token: str, model: str):
    """Update Codex config.toml to point to the proxy."""
    import toml

    codex_home = os.path.expanduser('~/.codex')
    config_path = os.path.join(codex_home, 'config.toml')

    if not os.path.exists(config_path):
        logger.warning(f"Codex config not found at {config_path}")
        return False

    try:
        # Read existing config
        logger.info(f"Reading config from: {config_path}")
        with open(config_path, 'r') as f:
            config = toml.load(f)

        logger.info(f"Config loaded. Keys: {list(config.keys())}")

        # Update or create the proxy provider
        if 'model_providers' not in config:
            logger.info("Creating model_providers section...")
            config['model_providers'] = {}

        logger.info(f"Model providers found: {list(config.get('model_providers', {}).keys())}")

        # Update the dashboard-proxy provider if it exists
        if 'dashboard-proxy' in config.get('model_providers', {}):
            logger.info("Found dashboard-proxy provider, updating...")
            provider_config = config['model_providers']['dashboard-proxy']

            # Fix structure: move model/model_provider/max_tokens to root if they're in provider section
            if 'model' in provider_config:
                provider_config.pop('model')
                logger.info("Removed 'model' from provider section (should be at root)")
            if 'model_provider' in provider_config:
                provider_config.pop('model_provider')
                logger.info("Removed 'model_provider' from provider section (should be at root)")
            if 'max_tokens' in provider_config:
                provider_config.pop('max_tokens')
                logger.info("Removed 'max_tokens' from provider section (should be at root)")

            # Update root level settings with correct values from .env
            config['model'] = model
            config['model_provider'] = 'dashboard-proxy'
            # Set high max_tokens for long responses (Codex needs this for multi-step tasks)
            config['max_tokens'] = 32768

            # Update base_url
            config['model_providers']['dashboard-proxy']['base_url'] = f'http://localhost:{proxy_port}/v1'
            logger.info(f"✓ Updated dashboard-proxy base_url to http://localhost:{proxy_port}/v1")
            logger.info(f"✓ Updated model to: {model}")
            logger.info(f"✓ Updated max_tokens to: 32768 (for long multi-step tasks)")
            logger.info(f"✓ Fixed config structure (model settings at root level)")
        else:
            logger.warning("dashboard-proxy provider NOT found in existing config!")
            logger.warning("Creating dashboard-proxy provider from scratch...")

            # Create the provider
            config['model_providers']['dashboard-proxy'] = {
                'name': 'Dashboard Proxy (Local Testing)',
                'base_url': f'http://localhost:{proxy_port}/v1',
                'env_key': 'CUSTOM_LLM_API_KEY',
                'wire_api': 'chat'
            }

            # Set root level settings
            config['model'] = model
            config['model_provider'] = 'dashboard-proxy'
            config['max_tokens'] = 32768

            logger.info(f"✓ Created dashboard-proxy provider with model: {model} (max_tokens: 32768)")

        # Also update any other custom providers
        for provider_name, provider_config in config.get('model_providers', {}).items():
            if isinstance(provider_config, dict) and 'base_url' in provider_config:
                # Update if it looks like it's pointing to localhost on a different port
                if 'localhost' in provider_config.get('base_url', ''):
                    old_url = provider_config['base_url']
                    provider_config['base_url'] = f'http://localhost:{proxy_port}/v1'
                    logger.info(f"✓ Updated {provider_name} base_url: {old_url} → http://localhost:{proxy_port}/v1")

        # Write updated config back
        logger.info(f"Writing updated config to: {config_path}")
        with open(config_path, 'w') as f:
            toml.dump(config, f)

        logger.info(f"✓ Codex config updated at {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to update Codex config: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def launch_codex():
    """Launch OpenAI Codex CLI with proxy configuration."""

    # Get configuration from .env
    proxy_port = os.getenv('PROXY_PORT', '3000')
    proxy_token = os.getenv('PROXY_ACCESS_TOKEN')
    target_model = os.getenv('DEFAULT_MODEL', 'gpt-4')

    if not proxy_token:
        logger.error("PROXY_ACCESS_TOKEN not found in .env file")
        sys.exit(1)

    # Update Codex config.toml to point to our proxy
    logger.info("Updating Codex configuration...")
    success = update_codex_config(proxy_port, proxy_token, target_model)

    if not success:
        logger.error("Failed to update Codex config.toml!")
        logger.error("Please check ~/.codex/config.toml manually")
        sys.exit(1)

    logger.info("")
    logger.info("=" * 80)
    logger.info("📝 Verifying Codex configuration...")
    logger.info("=" * 80)

    # Read and display the config to verify
    import toml
    config_path = os.path.expanduser('~/.codex/config.toml')
    try:
        with open(config_path, 'r') as f:
            config = toml.load(f)

        logger.info(f"  model: {config.get('model', 'NOT SET')}")
        logger.info(f"  model_provider: {config.get('model_provider', 'NOT SET')}")

        if 'model_providers' in config and 'dashboard-proxy' in config['model_providers']:
            dp = config['model_providers']['dashboard-proxy']
            logger.info(f"  [model_providers.dashboard-proxy]:")
            logger.info(f"    name: {dp.get('name', 'NOT SET')}")
            logger.info(f"    base_url: {dp.get('base_url', 'NOT SET')}")
            logger.info(f"    wire_api: {dp.get('wire_api', 'NOT SET')}")
            logger.info(f"    env_key: {dp.get('env_key', 'NOT SET')}")
        else:
            logger.error("  ✗ dashboard-proxy provider NOT FOUND in config!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to read config.toml: {e}")
        sys.exit(1)

    logger.info("")

    # Build environment variables for OpenAI Codex CLI
    env = os.environ.copy()

    # Configure OpenAI Codex CLI to use the proxy
    # Codex uses OpenAI environment variables (only works for built-in openai provider)
    env['OPENAI_BASE_URL'] = f'http://localhost:{proxy_port}/v1'
    env['OPENAI_API_KEY'] = proxy_token

    # Set additional API keys that custom Codex providers might expect
    # (Codex config.toml custom providers may reference different env variables)
    env['CUSTOM_LLM_API_KEY'] = proxy_token

    # Optional: Set Codex home directory
    if 'CODEX_HOME' not in env:
        env['CODEX_HOME'] = os.path.expanduser('~/.codex')

    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 Launching OpenAI Codex CLI with Proxy Configuration")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Base URL:            {env['OPENAI_BASE_URL']}")
    logger.info(f"  OPENAI_API_KEY:      {proxy_token[:20]}...")
    logger.info(f"  CUSTOM_LLM_API_KEY:  {proxy_token[:20]}...")
    logger.info(f"  Target Model:        {target_model}")
    logger.info(f"  Codex Home:          {env['CODEX_HOME']}")
    logger.info("")
    logger.info("🔄 OpenAI Codex CLI configuration:")
    logger.info("   → Custom provider config.toml updated to use proxy")
    logger.info("   → Launching with: --config model_provider=dashboard-proxy")
    logger.info("   → Requests sent to /v1/chat/completions (OpenAI format)")
    logger.info("   → No format conversion needed - bypasses Anthropic formatting")
    logger.info("   → Works directly with your custom models")
    logger.info("")
    logger.info("💡 Note: Using explicit --config flags to force provider selection")
    logger.info("   This ensures Codex uses dashboard-proxy instead of default openai")
    logger.info("")
    logger.info("Check the dashboard at http://localhost:{} to see requests.".format(proxy_port))
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Launch OpenAI Codex CLI
    # Force use of dashboard-proxy provider via command line
    try:
        # Launch without forcing provider first - let it use config.toml
        subprocess.run(['codex'], env=env)
    except FileNotFoundError:
        logger.error("✗ 'codex' command not found")
        logger.error("")
        logger.error("Please install OpenAI Codex CLI:")
        logger.error("  npm install -g @openai/codex")
        logger.error("")
        logger.error("Or if you have npm installed:")
        logger.error("  npx @openai/codex")
        logger.error("")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("OpenAI Codex CLI terminated by user")
        sys.exit(0)


def main():
    """Main entry point."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔧 OpenAI Codex CLI Proxy Launcher")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Setup RBC Security
    setup_rbc_security()
    logger.info("")

    # Step 2: Check if proxy is running
    if not check_proxy_running():
        sys.exit(1)
    logger.info("")

    # Step 3: Launch OpenAI Codex CLI
    launch_codex()


if __name__ == '__main__':
    main()
