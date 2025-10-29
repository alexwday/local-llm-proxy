#!/usr/bin/env python3
"""
Interactive Web Scraping Agent using Crawl4AI.

This agent provides an interactive REPL interface for web scraping with LLM-powered extraction.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    from crawl4ai import AsyncWebCrawler, LLMExtractionStrategy, LLMConfig, CrawlerRunConfig
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, NoExtractionStrategy
    from pydantic import BaseModel, Field, create_model
except ImportError:
    print("ERROR: crawl4ai not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

from logger_manager import LoggerManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ScraperAgent:
    """Interactive web scraping agent with Crawl4AI."""

    def __init__(self, llm_config: LLMConfig, log_manager: Optional[LoggerManager] = None):
        """Initialize the scraping agent.

        Args:
            llm_config: Configuration for LLM integration
            log_manager: Optional logger manager for dashboard integration
        """
        self.llm_config = llm_config
        self.log_manager = log_manager
        self.last_result = None
        self.output_dir = Path("scraper_output")
        self.output_dir.mkdir(exist_ok=True)
        self.session_history = []

        logger.info("✓ Scraper agent initialized")

    def _log_event(self, level: str, message: str, data: Any = None):
        """Log an event to both console and dashboard."""
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)

        if self.log_manager:
            self.log_manager.log_server_event(level, message, data)

    async def scrape(self, url: str, use_llm: bool = False, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Scrape a single webpage.

        Args:
            url: URL to scrape
            use_llm: Whether to use LLM for extraction
            prompt: Optional prompt for LLM extraction

        Returns:
            Dictionary with scraping results
        """
        self._log_event("info", f"🔍 Scraping: {url}")

        try:
            start_time = datetime.now()

            # Configure extraction strategy
            extraction_strategy = None
            if use_llm and prompt:
                extraction_strategy = LLMExtractionStrategy(
                    llm_config=self.llm_config,
                    instruction=prompt
                )

            # Create crawler and run
            async with AsyncWebCrawler(verbose=False) as crawler:
                config = CrawlerRunConfig(
                    extraction_strategy=extraction_strategy
                )
                result = await crawler.arun(url=url, config=config)

            duration = (datetime.now() - start_time).total_seconds()

            # Process results
            response = {
                "success": result.success,
                "url": url,
                "status_code": result.status_code,
                "markdown": result.markdown_v2.raw_markdown if result.success else None,
                "extracted_content": result.extracted_content if use_llm else None,
                "links": {
                    "internal": list(result.links.get("internal", [])) if result.success else [],
                    "external": list(result.links.get("external", [])) if result.success else []
                },
                "metadata": {
                    "duration_seconds": duration,
                    "content_length": len(result.markdown_v2.raw_markdown) if result.success else 0,
                    "timestamp": datetime.now().isoformat()
                }
            }

            self.last_result = response
            self.session_history.append({
                "type": "scrape",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "success": result.success
            })

            if result.success:
                self._log_event("info", f"✓ Scraped {len(response['metadata']['content_length'])} chars in {duration:.2f}s")
            else:
                self._log_event("error", f"✗ Failed to scrape {url}: {result.error_message}")

            return response

        except Exception as e:
            self._log_event("error", f"Error scraping {url}: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

    async def extract(self, url: str, schema: Dict[str, str], instruction: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured data from a webpage using LLM.

        Args:
            url: URL to extract from
            schema: Dictionary defining the schema (e.g., {"title": "str", "price": "float"})
            instruction: Optional custom instruction for extraction

        Returns:
            Dictionary with extracted structured data
        """
        self._log_event("info", f"🤖 Extracting structured data from: {url}")

        try:
            start_time = datetime.now()

            # Create Pydantic model from schema dynamically
            field_definitions = {}
            for field_name, field_type in schema.items():
                if field_type == "str":
                    field_definitions[field_name] = (str, Field(...))
                elif field_type == "int":
                    field_definitions[field_name] = (int, Field(...))
                elif field_type == "float":
                    field_definitions[field_name] = (float, Field(...))
                elif field_type == "bool":
                    field_definitions[field_name] = (bool, Field(...))
                elif field_type == "list":
                    field_definitions[field_name] = (List[str], Field(...))
                else:
                    field_definitions[field_name] = (str, Field(...))

            ExtractionModel = create_model('ExtractionModel', **field_definitions)

            # Configure LLM extraction
            default_instruction = f"Extract the following fields from the webpage: {', '.join(schema.keys())}"
            extraction_strategy = LLMExtractionStrategy(
                llm_config=self.llm_config,
                schema=ExtractionModel.model_json_schema(),
                extraction_type="schema",
                instruction=instruction or default_instruction
            )

            # Run extraction
            async with AsyncWebCrawler(verbose=False) as crawler:
                config = CrawlerRunConfig(
                    extraction_strategy=extraction_strategy
                )
                result = await crawler.arun(url=url, config=config)

            duration = (datetime.now() - start_time).total_seconds()

            # Parse extracted content
            extracted_data = None
            if result.success and result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)
                except json.JSONDecodeError:
                    extracted_data = result.extracted_content

            response = {
                "success": result.success,
                "url": url,
                "schema": schema,
                "extracted_data": extracted_data,
                "metadata": {
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat()
                }
            }

            self.last_result = response
            self.session_history.append({
                "type": "extract",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "success": result.success
            })

            if result.success:
                self._log_event("info", f"✓ Extracted data in {duration:.2f}s")
            else:
                self._log_event("error", f"✗ Extraction failed: {result.error_message}")

            return response

        except Exception as e:
            self._log_event("error", f"Error extracting from {url}: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

    async def crawl(self, url: str, max_depth: int = 2, max_pages: int = 10) -> Dict[str, Any]:
        """Crawl multiple pages starting from a URL.

        Args:
            url: Starting URL
            max_depth: Maximum depth to crawl
            max_pages: Maximum number of pages to crawl

        Returns:
            Dictionary with crawl results
        """
        self._log_event("info", f"🕷️  Crawling: {url} (depth={max_depth}, max_pages={max_pages})")

        try:
            start_time = datetime.now()
            crawled_pages = []
            to_crawl = [(url, 0)]  # (url, depth)
            crawled_urls = set()

            async with AsyncWebCrawler(verbose=False) as crawler:
                while to_crawl and len(crawled_pages) < max_pages:
                    current_url, depth = to_crawl.pop(0)

                    if current_url in crawled_urls or depth > max_depth:
                        continue

                    logger.info(f"  [{len(crawled_pages) + 1}/{max_pages}] Depth {depth}: {current_url}")

                    config = CrawlerRunConfig()
                    result = await crawler.arun(url=current_url, config=config)

                    crawled_urls.add(current_url)

                    if result.success:
                        page_data = {
                            "url": current_url,
                            "depth": depth,
                            "markdown": result.markdown_v2.raw_markdown,
                            "links": {
                                "internal": list(result.links.get("internal", [])),
                                "external": list(result.links.get("external", []))
                            }
                        }
                        crawled_pages.append(page_data)

                        # Add internal links to crawl queue if not at max depth
                        if depth < max_depth:
                            for link in list(result.links.get("internal", []))[:5]:  # Limit links per page
                                if link not in crawled_urls:
                                    to_crawl.append((link, depth + 1))

            duration = (datetime.now() - start_time).total_seconds()

            response = {
                "success": True,
                "starting_url": url,
                "pages_crawled": len(crawled_pages),
                "pages": crawled_pages,
                "metadata": {
                    "duration_seconds": duration,
                    "max_depth": max_depth,
                    "max_pages": max_pages,
                    "timestamp": datetime.now().isoformat()
                }
            }

            self.last_result = response
            self.session_history.append({
                "type": "crawl",
                "url": url,
                "pages_crawled": len(crawled_pages),
                "timestamp": datetime.now().isoformat(),
                "success": True
            })

            self._log_event("info", f"✓ Crawled {len(crawled_pages)} pages in {duration:.2f}s")

            return response

        except Exception as e:
            self._log_event("error", f"Error crawling {url}: {str(e)}")
            return {
                "success": False,
                "starting_url": url,
                "error": str(e)
            }

    def save_result(self, filename: Optional[str] = None, format: str = "json") -> str:
        """Save the last result to a file.

        Args:
            filename: Optional filename (auto-generated if not provided)
            format: Output format (json, md, or txt)

        Returns:
            Path to saved file
        """
        if not self.last_result:
            logger.warning("No results to save")
            return None

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"scrape-{timestamp}.{format}"

        filepath = self.output_dir / filename

        try:
            if format == "json":
                with open(filepath, 'w') as f:
                    json.dump(self.last_result, f, indent=2)
            elif format in ("md", "txt"):
                with open(filepath, 'w') as f:
                    if "markdown" in self.last_result:
                        f.write(self.last_result["markdown"])
                    elif "pages" in self.last_result:
                        for page in self.last_result["pages"]:
                            f.write(f"\n\n# {page['url']}\n\n")
                            f.write(page["markdown"])
                    else:
                        f.write(json.dumps(self.last_result, indent=2))

            logger.info(f"✓ Saved to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving result: {e}")
            return None

    def show_config(self):
        """Display current configuration."""
        print("\n" + "=" * 60)
        print("📊 Scraper Agent Configuration")
        print("=" * 60)
        print(f"LLM Provider:    {self.llm_config.provider}")
        print(f"Base URL:        {self.llm_config.base_url}")
        print(f"Output Dir:      {self.output_dir}")
        print(f"Session History: {len(self.session_history)} operations")
        print("=" * 60 + "\n")

    def show_history(self):
        """Display session history."""
        if not self.session_history:
            print("No operations in history\n")
            return

        print("\n" + "=" * 60)
        print("📜 Session History")
        print("=" * 60)
        for i, entry in enumerate(self.session_history[-10:], 1):  # Show last 10
            status = "✓" if entry["success"] else "✗"
            print(f"{i}. {status} [{entry['type']}] {entry['url']}")
            if entry['type'] == 'crawl':
                print(f"   Pages: {entry.get('pages_crawled', 0)}")
        print("=" * 60 + "\n")

    def show_help(self):
        """Display help information."""
        help_text = """
╔══════════════════════════════════════════════════════════════════════╗
║                    Web Scraping Agent - Help                         ║
╚══════════════════════════════════════════════════════════════════════╝

📝 Basic Commands:
  scrape <url>
      Scrape a single webpage and extract markdown content
      Example: scrape https://example.com

  scrape <url> --llm "<prompt>"
      Scrape with LLM-powered extraction using a custom prompt
      Example: scrape https://news.ycombinator.com --llm "Extract the top 5 article titles"

🎯 Structured Extraction:
  extract <url> <schema>
      Extract structured data using LLM with a defined schema
      Example: extract https://example.com {"title":"str","price":"float"}

  extract <url> <schema> --instruction "<text>"
      Extract with custom instruction
      Example: extract https://news.ycombinator.com {"title":"str","points":"int"} --instruction "Get top stories"

🕷️  Multi-Page Crawling:
  crawl <url>
      Crawl multiple pages starting from URL (default: depth=2, max=10 pages)
      Example: crawl https://docs.example.com

  crawl <url> --depth <n> --max <n>
      Crawl with custom depth and page limit
      Example: crawl https://docs.example.com --depth 3 --max 20

💾 Output Management:
  save [filename] [--format json|md|txt]
      Save last result to file (auto-named if filename not provided)
      Example: save output.json
      Example: save --format md

  export <format>
      Quick save with auto-generated filename
      Example: export json

ℹ️  Information:
  config        Show current configuration
  history       Show session history
  logs          Show recent scraping logs
  help          Show this help message

🚪 Control:
  clear         Clear the screen
  exit          Quit the agent
  quit          Quit the agent

💡 Tips:
  - All scraped content is saved as markdown for LLM compatibility
  - Use --llm flag for free-form extraction with natural language prompts
  - Use extract command for structured data with defined schemas
  - Results are automatically logged to the proxy dashboard
  - Output files are saved to: scraper_output/

╚══════════════════════════════════════════════════════════════════════╝
"""
        print(help_text)

    async def repl(self):
        """Run the interactive REPL."""
        print("\n" + "=" * 70)
        print("🚀 Web Scraping Agent with Crawl4AI")
        print("=" * 70)
        print(f"LLM: {self.llm_config.provider} via {self.llm_config.base_url}")
        print(f"Output: {self.output_dir}")
        print("\nType 'help' for available commands or 'exit' to quit")
        print("=" * 70 + "\n")

        while True:
            try:
                # Get user input
                user_input = input("scraper> ").strip()

                if not user_input:
                    continue

                # Parse command
                parts = user_input.split()
                command = parts[0].lower()

                # Handle commands
                if command in ("exit", "quit"):
                    print("👋 Goodbye!\n")
                    break

                elif command == "help":
                    self.show_help()

                elif command == "config":
                    self.show_config()

                elif command == "history":
                    self.show_history()

                elif command == "clear":
                    os.system('clear' if os.name != 'nt' else 'cls')

                elif command == "scrape":
                    if len(parts) < 2:
                        print("Usage: scrape <url> [--llm \"<prompt>\"]")
                        continue

                    url = parts[1]
                    use_llm = "--llm" in user_input
                    prompt = None

                    if use_llm:
                        # Extract prompt from quotes
                        try:
                            prompt_start = user_input.index('"') + 1
                            prompt_end = user_input.rindex('"')
                            prompt = user_input[prompt_start:prompt_end]
                        except ValueError:
                            print("Error: LLM prompt must be in quotes")
                            continue

                    result = await self.scrape(url, use_llm=use_llm, prompt=prompt)

                    if result["success"]:
                        print(f"\n✓ Success!")
                        print(f"  Content: {result['metadata']['content_length']} characters")
                        print(f"  Links: {len(result['links']['internal'])} internal, {len(result['links']['external'])} external")
                        print(f"  Duration: {result['metadata']['duration_seconds']:.2f}s")

                        if result.get("extracted_content"):
                            print(f"\n📄 Extracted Content:")
                            print(result["extracted_content"][:500])  # Show first 500 chars
                            if len(result["extracted_content"]) > 500:
                                print("... (truncated)")
                        print()
                    else:
                        print(f"\n✗ Failed: {result.get('error', 'Unknown error')}\n")

                elif command == "extract":
                    if len(parts) < 3:
                        print("Usage: extract <url> <schema> [--instruction \"<text>\"]")
                        print("Example: extract https://example.com {\"title\":\"str\",\"price\":\"float\"}")
                        continue

                    url = parts[1]

                    # Parse schema (JSON)
                    try:
                        schema_start = user_input.index("{")
                        schema_end = user_input.rindex("}") + 1
                        schema_str = user_input[schema_start:schema_end]
                        schema = json.loads(schema_str)
                    except (ValueError, json.JSONDecodeError) as e:
                        print(f"Error: Invalid schema JSON: {e}")
                        continue

                    # Extract instruction if provided
                    instruction = None
                    if "--instruction" in user_input:
                        try:
                            inst_start = user_input.rindex('"', 0, user_input.rindex('"')) + 1
                            inst_end = user_input.rindex('"')
                            instruction = user_input[inst_start:inst_end]
                        except ValueError:
                            print("Warning: Could not parse instruction")

                    result = await self.extract(url, schema, instruction)

                    if result["success"]:
                        print(f"\n✓ Success!")
                        print(f"  Duration: {result['metadata']['duration_seconds']:.2f}s")
                        print(f"\n📊 Extracted Data:")
                        print(json.dumps(result["extracted_data"], indent=2))
                        print()
                    else:
                        print(f"\n✗ Failed: {result.get('error', 'Unknown error')}\n")

                elif command == "crawl":
                    if len(parts) < 2:
                        print("Usage: crawl <url> [--depth <n>] [--max <n>]")
                        continue

                    url = parts[1]
                    max_depth = 2
                    max_pages = 10

                    # Parse optional flags
                    if "--depth" in parts:
                        try:
                            depth_idx = parts.index("--depth")
                            max_depth = int(parts[depth_idx + 1])
                        except (ValueError, IndexError):
                            print("Warning: Invalid depth value, using default (2)")

                    if "--max" in parts:
                        try:
                            max_idx = parts.index("--max")
                            max_pages = int(parts[max_idx + 1])
                        except (ValueError, IndexError):
                            print("Warning: Invalid max value, using default (10)")

                    result = await self.crawl(url, max_depth=max_depth, max_pages=max_pages)

                    if result["success"]:
                        print(f"\n✓ Crawled {result['pages_crawled']} pages in {result['metadata']['duration_seconds']:.2f}s")
                        for i, page in enumerate(result["pages"][:5], 1):  # Show first 5
                            print(f"  {i}. [Depth {page['depth']}] {page['url']}")
                        if result['pages_crawled'] > 5:
                            print(f"  ... and {result['pages_crawled'] - 5} more pages")
                        print()
                    else:
                        print(f"\n✗ Failed: {result.get('error', 'Unknown error')}\n")

                elif command in ("save", "export"):
                    if not self.last_result:
                        print("No results to save\n")
                        continue

                    filename = None
                    format = "json"

                    if command == "save" and len(parts) > 1:
                        filename = parts[1]
                        if "--format" in parts:
                            try:
                                format_idx = parts.index("--format")
                                format = parts[format_idx + 1]
                            except IndexError:
                                pass
                    elif command == "export" and len(parts) > 1:
                        format = parts[1]

                    filepath = self.save_result(filename, format)
                    if filepath:
                        print(f"✓ Saved to: {filepath}\n")

                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"Error: {e}\n")


async def main():
    """Main entry point for testing the agent directly."""
    from dotenv import load_dotenv
    from config import Config

    load_dotenv()
    config = Config()

    # Create LLM config
    llm_config = LLMConfig(
        provider=f"openai/{config.default_model}",
        api_token=config.proxy_access_token,
        base_url=f"http://localhost:{config.port}/v1"
    )

    # Create and run agent
    agent = ScraperAgent(llm_config)
    await agent.repl()


if __name__ == '__main__':
    asyncio.run(main())
