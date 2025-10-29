#!/usr/bin/env python3
"""
Launch Web Scraping Agent with proxy configuration.

This script:
1. Enables RBC Security SSL certificates (if available)
2. Checks that the proxy server is running
3. Configures Crawl4AI to use the local proxy
4. Launches the interactive scraping agent

Prerequisites:
- The proxy server must be running (./run.sh or ./run-dev.sh)
- crawl4ai installed (pip install -r requirements.txt)
- Playwright browsers installed (playwright install)
- rbc_security package installed (pip install rbc_security) - optional

Usage:
    python3 launch-scraper.py
"""

import os
import sys
import subprocess
import logging
import asyncio
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


def check_crawl4ai_installed():
    """Check if crawl4ai is installed."""
    try:
        import crawl4ai
        logger.info("✓ crawl4ai is installed")
        return True
    except ImportError:
        logger.error("✗ crawl4ai is not installed")
        logger.error("")
        logger.error("Please install dependencies:")
        logger.error("  pip install -r requirements.txt")
        logger.error("")
        return False


def check_playwright_browsers():
    """Check if Playwright browsers are installed."""
    try:
        result = subprocess.run(
            ['playwright', 'install', '--help'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info("✓ Playwright is available")

            # Check if browsers are installed by running a quick check
            logger.info("  Note: If scraping fails, run: playwright install")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("⚠️  Playwright command not found")
        logger.warning("  If scraping fails, install browsers with:")
        logger.warning("  playwright install")
        return False


def setup_crawl4ai_config():
    """Setup Crawl4AI configuration for the proxy."""
    try:
        from crawl4ai import LLMConfig
        from config import Config

        config = Config()

        # Create LLM config for Crawl4AI
        llm_config = LLMConfig(
            provider=f"openai/{config.default_model}",
            api_token=config.proxy_access_token,
            base_url=f"http://localhost:{config.port}/v1"
        )

        logger.info("✓ Crawl4AI configured to use proxy")
        logger.info(f"  Provider: {llm_config.provider}")
        logger.info(f"  Base URL: {llm_config.base_url}")

        return llm_config, config

    except Exception as e:
        logger.error(f"Failed to setup Crawl4AI config: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


async def launch_scraper_agent():
    """Launch the interactive web scraping agent."""

    # Get configuration from .env
    proxy_port = os.getenv('PROXY_PORT', '3000')
    proxy_token = os.getenv('PROXY_ACCESS_TOKEN')
    target_model = os.getenv('DEFAULT_MODEL', 'gpt-4')
    max_tokens = int(os.getenv('MAX_TOKENS', '32768'))

    if not proxy_token:
        logger.error("PROXY_ACCESS_TOKEN not found in .env file")
        sys.exit(1)

    # Setup Crawl4AI configuration
    logger.info("Setting up Crawl4AI configuration...")
    llm_config, config = setup_crawl4ai_config()

    if not llm_config:
        logger.error("Failed to setup Crawl4AI configuration!")
        sys.exit(1)

    logger.info("")
    logger.info("=" * 80)
    logger.info("📝 Verifying Configuration...")
    logger.info("=" * 80)
    logger.info(f"  Proxy URL:        http://localhost:{proxy_port}")
    logger.info(f"  Access Token:     {proxy_token[:20]}...")
    logger.info(f"  Target Model:     {target_model}")
    logger.info(f"  Max Tokens:       {max_tokens}")
    logger.info(f"  LLM Provider:     {llm_config.provider}")
    logger.info(f"  Base URL:         {llm_config.base_url}")
    logger.info("")
    logger.info("💡 Note: All LLM-powered extractions will use your proxy")
    logger.info("   Check the dashboard at http://localhost:{} to see requests.".format(proxy_port))
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Import and launch the scraper agent
    try:
        from scraper_agent import ScraperAgent
        from logger_manager import LoggerManager

        # Create logger manager for dashboard integration
        log_manager = LoggerManager()

        # Create and run the agent
        agent = ScraperAgent(llm_config, log_manager)
        await agent.repl()

    except ImportError as e:
        logger.error(f"✗ Failed to import scraper_agent: {e}")
        logger.error("")
        logger.error("Please ensure all dependencies are installed:")
        logger.error("  pip install -r requirements.txt")
        logger.error("")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Scraping agent terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running scraper agent: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


def main():
    """Main entry point."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔧 Web Scraping Agent Launcher")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Setup RBC Security
    setup_rbc_security()
    logger.info("")

    # Step 2: Check if proxy is running
    if not check_proxy_running():
        sys.exit(1)
    logger.info("")

    # Step 3: Check if crawl4ai is installed
    if not check_crawl4ai_installed():
        sys.exit(1)
    logger.info("")

    # Step 4: Check Playwright browsers
    check_playwright_browsers()
    logger.info("")

    # Step 5: Launch the scraping agent
    logger.info("=" * 80)
    logger.info("🚀 Launching Web Scraping Agent")
    logger.info("=" * 80)
    logger.info("")

    try:
        asyncio.run(launch_scraper_agent())
    except KeyboardInterrupt:
        logger.info("\n\nAgent terminated by user\n")
        sys.exit(0)


if __name__ == '__main__':
    main()
