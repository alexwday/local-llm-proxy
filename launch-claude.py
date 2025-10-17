#!/usr/bin/env python3
"""
Launch Claude Code CLI with proxy configuration.

This script:
1. Enables RBC Security SSL certificates
2. Configures Claude Code to use the local proxy
3. Launches Claude Code CLI with the custom endpoint

Prerequisites:
- The proxy server must be running (./run.sh or ./run-dev.sh)
- rbc_security package installed (pip install rbc_security)

Usage:
    python3 launch-claude.py
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

    proxy_url = f"http://localhost:{os.getenv('LOCAL_PORT', '3000')}"

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


def launch_claude_code():
    """Launch Claude Code CLI with proxy configuration."""

    # Get configuration from .env
    proxy_port = os.getenv('LOCAL_PORT', '3000')
    proxy_token = os.getenv('PROXY_ACCESS_TOKEN')
    target_model = os.getenv('TARGET_MODEL', 'gpt-4')

    if not proxy_token:
        logger.error("PROXY_ACCESS_TOKEN not found in .env file")
        sys.exit(1)

    # Build environment variables for Claude Code
    env = os.environ.copy()

    # Configure Claude Code to use the proxy
    env['ANTHROPIC_BASE_URL'] = f'http://localhost:{proxy_port}'
    env['ANTHROPIC_AUTH_TOKEN'] = proxy_token
    env['ANTHROPIC_MODEL'] = target_model

    # Optional: Configure additional Claude Code settings
    env['ANTHROPIC_SMALL_FAST_MODEL'] = os.getenv('TARGET_SMALL_MODEL', 'gpt-3.5-turbo')
    env['API_TIMEOUT_MS'] = '600000'  # 10 minutes
    env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
    env['DISABLE_TELEMETRY'] = '1'

    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 Launching Claude Code CLI with Proxy Configuration")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Base URL:  {env['ANTHROPIC_BASE_URL']}")
    logger.info(f"  Token:     {proxy_token[:20]}...")
    logger.info(f"  Model:     {env['ANTHROPIC_MODEL']}")
    logger.info(f"  Small Model: {env['ANTHROPIC_SMALL_FAST_MODEL']}")
    logger.info("")
    logger.info("All Claude Code API requests will go through your local proxy.")
    logger.info("Check the dashboard at http://localhost:{} to see requests.".format(proxy_port))
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Launch Claude Code CLI
    try:
        subprocess.run(['claude'], env=env)
    except FileNotFoundError:
        logger.error("✗ 'claude' command not found")
        logger.error("")
        logger.error("Please install Claude Code CLI:")
        logger.error("  Visit: https://docs.anthropic.com/claude/docs/claude-code")
        logger.error("")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Claude Code CLI terminated by user")
        sys.exit(0)


def main():
    """Main entry point."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔧 Claude Code Proxy Launcher")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Setup RBC Security
    setup_rbc_security()
    logger.info("")

    # Step 2: Check if proxy is running
    if not check_proxy_running():
        sys.exit(1)
    logger.info("")

    # Step 3: Launch Claude Code
    launch_claude_code()


if __name__ == '__main__':
    main()
