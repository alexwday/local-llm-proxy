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


def launch_codex():
    """Launch OpenAI Codex CLI with proxy configuration."""

    # Get configuration from .env
    proxy_port = os.getenv('PROXY_PORT', '3000')
    proxy_token = os.getenv('PROXY_ACCESS_TOKEN')
    target_model = os.getenv('DEFAULT_MODEL', 'gpt-4')

    if not proxy_token:
        logger.error("PROXY_ACCESS_TOKEN not found in .env file")
        sys.exit(1)

    # Build environment variables for OpenAI Codex CLI
    env = os.environ.copy()

    # Configure OpenAI Codex CLI to use the proxy
    # Codex uses OpenAI environment variables
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
    logger.info("🔄 OpenAI Codex CLI uses OpenAI format natively:")
    logger.info("   → Requests sent to /v1/chat/completions (OpenAI format)")
    logger.info("   → No format conversion needed - bypasses Anthropic formatting")
    logger.info("   → Works directly with your custom models")
    logger.info("")
    logger.info("Check the dashboard at http://localhost:{} to see requests.".format(proxy_port))
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Launch OpenAI Codex CLI
    try:
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
