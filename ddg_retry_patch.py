"""
Monkey patch for DuckDuckGo search to add retry logic with delays.
This helps avoid 202 rate limit errors from corporate networks.
"""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def add_retry_to_ddgs():
    """Patch DDGS.text() to add retry logic with delays."""
    try:
        from duckduckgo_search import DDGS
        
        original_text = DDGS.text
        
        @wraps(original_text)
        def text_with_retry(self, *args, **kwargs):
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    result = original_text(self, *args, **kwargs)
                    return result
                except Exception as e:
                    error_msg = str(e).lower()
                    if '202' in error_msg or 'rate' in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1)
                            logger.warning(f"DuckDuckGo rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                            time.sleep(wait_time)
                            continue
                    raise
            
            return []
        
        DDGS.text = text_with_retry
        logger.info("✓ Added DuckDuckGo retry logic")
        return True
        
    except Exception as e:
        logger.warning(f"Could not patch DuckDuckGo search: {e}")
        return False
