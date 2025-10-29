#!/usr/bin/env python3
"""
Launch GPT Researcher with proxy configuration.

This script:
1. Enables RBC Security SSL certificates (if available)
2. Checks that the proxy server is running
3. Configures GPT Researcher to use the local proxy and DuckDuckGo search
4. Provides an interactive interface for research queries

Prerequisites:
- The proxy server must be running (./run.sh or ./run-dev.sh)
- GPT Researcher installed (pip install -e gpt-researcher-lib)
- rbc_security package installed (pip install rbc_security) - optional

Usage:
    python3 launch-researcher.py "your research query"
    python3 launch-researcher.py --interactive
"""

import os
import sys
import asyncio
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


def setup_ddgs_compatibility():
    """Create ddgs compatibility wrapper for GPT Researcher.

    GPT Researcher expects 'from ddgs import DDGS' but the package is 'duckduckgo_search'.
    This creates a simple wrapper module to make it work.
    """
    try:
        # Check if wrapper already works
        import ddgs
        return True
    except ImportError:
        pass

    # Create wrapper in site-packages
    import site
    site_packages = site.getsitepackages()[0]
    wrapper_path = os.path.join(site_packages, 'ddgs.py')

    try:
        with open(wrapper_path, 'w') as f:
            f.write('''"""
Compatibility wrapper for GPT Researcher.
GPT Researcher expects 'from ddgs import DDGS' but the package is 'duckduckgo_search'.
"""
from duckduckgo_search import DDGS, AsyncDDGS

__all__ = ['DDGS', 'AsyncDDGS']
''')
        logger.info("✓ Created ddgs compatibility wrapper")
        return True
    except Exception as e:
        logger.warning(f"Could not create ddgs wrapper: {e}")
        logger.warning("DuckDuckGo search may not work")
        return False


def setup_ddgs_retry_patch():
    """Add retry logic to DuckDuckGo searches to handle rate limits."""
    try:
        # Import the patch module
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ddg_retry_patch import add_retry_to_ddgs

        # Apply the patch
        return add_retry_to_ddgs()
    except Exception as e:
        logger.warning(f"Could not apply DuckDuckGo retry patch: {e}")
        return False


def setup_researcher_config():
    """Setup GPT Researcher configuration using proxy."""
    # Get proxy configuration
    proxy_port = os.getenv('PROXY_PORT', '3000')
    proxy_token = os.getenv('PROXY_ACCESS_TOKEN')
    target_model = os.getenv('DEFAULT_MODEL', 'gpt-4')

    if not proxy_token:
        logger.error("PROXY_ACCESS_TOKEN not found in .env file")
        return False

    # Set GPT Researcher environment variables
    os.environ['OPENAI_API_BASE'] = f'http://localhost:{proxy_port}/v1'
    os.environ['OPENAI_API_KEY'] = proxy_token
    os.environ['RETRIEVER'] = 'duckduckgo'  # Use DuckDuckGo (no API key needed)

    # Override GPT Researcher's model defaults (format: "provider:model")
    # GPT Researcher uses 3 different models - set all to use your configured model
    os.environ['SMART_LLM'] = f'openai:{target_model}'      # Main research model (long responses)
    os.environ['FAST_LLM'] = f'openai:{target_model}'       # Fast task model (quick operations)
    os.environ['STRATEGIC_LLM'] = f'openai:{target_model}'  # Strategic planning model

    # Reduce search aggressiveness to avoid DuckDuckGo rate limits (HTTP 202)
    # These can be overridden in .env if needed:
    #   MAX_SEARCH_RESULTS_PER_QUERY=3
    #   MAX_ITERATIONS=2
    #   MAX_SUBTOPICS=2
    os.environ['MAX_SEARCH_RESULTS_PER_QUERY'] = os.getenv('MAX_SEARCH_RESULTS_PER_QUERY', '3')
    os.environ['MAX_ITERATIONS'] = os.getenv('MAX_ITERATIONS', '2')
    os.environ['MAX_SUBTOPICS'] = os.getenv('MAX_SUBTOPICS', '2')

    # Use more realistic user agent to avoid DuckDuckGo anti-bot detection
    # DuckDuckGo blocks obvious bot traffic, especially from corporate networks
    user_agent = os.getenv('USER_AGENT',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    os.environ['USER_AGENT'] = user_agent

    logger.info(f"  Search limits: {os.environ['MAX_SEARCH_RESULTS_PER_QUERY']} results/query, "
                f"{os.environ['MAX_ITERATIONS']} iterations, {os.environ['MAX_SUBTOPICS']} subtopics")

    # Configure corporate proxy for DuckDuckGo search (if needed)
    # Set these in .env if you're behind a corporate proxy:
    #   CORPORATE_HTTP_PROXY=http://proxy.company.com:8080
    #   CORPORATE_HTTPS_PROXY=http://proxy.company.com:8080
    if os.getenv('CORPORATE_HTTP_PROXY'):
        os.environ['HTTP_PROXY'] = os.getenv('CORPORATE_HTTP_PROXY')
        logger.info(f"  HTTP Proxy: {os.environ['HTTP_PROXY']}")
    if os.getenv('CORPORATE_HTTPS_PROXY'):
        os.environ['HTTPS_PROXY'] = os.getenv('CORPORATE_HTTPS_PROXY')
        logger.info(f"  HTTPS Proxy: {os.environ['HTTPS_PROXY']}")

    # Disable SSL verification for DuckDuckGo if behind corporate proxy
    # Only use this if you trust your corporate network
    if os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true':
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        logger.warning("  SSL verification DISABLED (DISABLE_SSL_VERIFY=true)")

    # Optional: Set other GPT Researcher configs
    if 'MAX_TOKENS' in os.environ:
        os.environ['MAX_TOKENS'] = os.getenv('MAX_TOKENS')

    logger.info("✓ GPT Researcher configured to use proxy")
    logger.info(f"  Base URL: http://localhost:{proxy_port}/v1")
    logger.info(f"  Model: {target_model}")
    logger.info(f"  Search Engine: DuckDuckGo (no API key required)")

    return True


async def run_research(query: str):
    """Run a research query using GPT Researcher."""
    try:
        from gpt_researcher import GPTResearcher
        logger.info("✓ GPT Researcher imported successfully")
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🔍 Research Query: {query}")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Starting research... This may take a few minutes.")
        logger.info("")

        # Create researcher instance
        researcher = GPTResearcher(
            query=query,
            report_type="research_report",  # Options: research_report, quick_report, etc.
            verbose=True
        )

        # Conduct research
        report = await researcher.conduct_research()

        # Generate final report
        final_report = await researcher.write_report()

        logger.info("")
        logger.info("=" * 80)
        logger.info("📄 Research Report")
        logger.info("=" * 80)
        logger.info("")
        print(final_report)
        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ Research completed!")
        logger.info("=" * 80)
        logger.info("")

        # Save report to file
        output_dir = "research_output"
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename from query
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in query)
        safe_filename = safe_filename[:50]  # Limit length
        output_file = f"{output_dir}/{safe_filename}.md"

        with open(output_file, 'w') as f:
            f.write(f"# Research Report: {query}\n\n")
            f.write(final_report)

        logger.info(f"✓ Report saved to: {output_file}")
        logger.info("")

        return final_report

    except ImportError as e:
        logger.error("✗ GPT Researcher not installed")
        logger.error(f"   Import error: {e}")
        logger.error("")
        logger.error("Please install dependencies:")
        logger.error("  source venv/bin/activate")
        logger.error("  pip install -r requirements.txt")
        logger.error("")
        logger.error("Or check which Python is being used:")
        logger.error(f"  Current Python: {sys.executable}")
        logger.error(f"  Run: {sys.executable} -m pip list | grep gpt-researcher")
        logger.error("")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during research: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


async def interactive_mode():
    """Run GPT Researcher in interactive mode."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔬 GPT Researcher - Interactive Mode")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Enter your research queries below.")
    logger.info("Type 'exit' or 'quit' to stop.")
    logger.info("")
    logger.info("Examples:")
    logger.info("  - What are the latest developments in AI agents?")
    logger.info("  - Compare LangChain vs LangGraph for building AI agents")
    logger.info("  - How does web scraping work with LLMs in 2025?")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    while True:
        try:
            query = input("\n🔍 Research Query: ").strip()

            if not query:
                continue

            if query.lower() in ('exit', 'quit', 'q'):
                logger.info("")
                logger.info("👋 Goodbye!")
                logger.info("")
                break

            # Run research
            await run_research(query)

        except KeyboardInterrupt:
            logger.info("")
            logger.info("")
            logger.info("👋 Goodbye!")
            logger.info("")
            break
        except EOFError:
            logger.info("")
            logger.info("")
            logger.info("👋 Goodbye!")
            logger.info("")
            break


def main():
    """Main entry point."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔧 GPT Researcher Launcher")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Setup RBC Security
    setup_rbc_security()
    logger.info("")

    # Step 2: Setup DuckDuckGo compatibility wrapper
    setup_ddgs_compatibility()
    setup_ddgs_retry_patch()
    logger.info("")

    # Step 3: Check if proxy is running
    if not check_proxy_running():
        sys.exit(1)
    logger.info("")

    # Step 4: Setup researcher configuration
    if not setup_researcher_config():
        sys.exit(1)
    logger.info("")

    # Step 5: Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ('--interactive', '-i'):
            # Interactive mode
            asyncio.run(interactive_mode())
        else:
            # Single query mode
            query = ' '.join(sys.argv[1:])
            asyncio.run(run_research(query))
    else:
        # No arguments, show usage
        logger.info("Usage:")
        logger.info("  python3 launch-researcher.py \"your research query\"")
        logger.info("  python3 launch-researcher.py --interactive")
        logger.info("")
        logger.info("Examples:")
        logger.info("  python3 launch-researcher.py \"What are the latest AI agent frameworks?\"")
        logger.info("  python3 launch-researcher.py --interactive")
        logger.info("")
        sys.exit(1)


if __name__ == '__main__':
    main()
