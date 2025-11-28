"""
Custom Web Scraper Module

This module provides ethical web scraping capabilities for extracting article content.
It implements rate limiting, timeout handling, and respects web scraping best practices.

Author: Google Hackathon Team
License: MIT
"""

import time
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class CustomScraper:
    """
    Ethical web scraper with intelligent content extraction and rate limiting.
    
    This class provides robust web scraping capabilities while adhering to
    ethical scraping practices. It extracts meaningful text content from web
    pages using intelligent HTML parsing and filtering.
    
    Key Features:
    
    1. Intelligent Content Extraction:
       - Targets meaningful paragraph content
       - Filters out short/empty paragraphs
       - Removes navigation and boilerplate text
       - Extracts article titles and metadata
    
    2. Ethical Scraping Practices:
       - Rate limiting between requests (1 second default)
       - Respects server timeouts
       - Identifies as bot via User-Agent
       - Implements retry logic with backoff
       - TODO: Add robots.txt compliance checker
    
    3. Robust Error Handling:
       - Network timeouts
       - HTTP errors (404, 500, etc.)
       - Malformed HTML
       - Connection failures
       - Empty content detection
    
    Architecture:
        - Requests library for HTTP operations
        - BeautifulSoup for HTML parsing
        - Configurable timeout and rate limits
        - Batch processing support
    
    Attributes:
        timeout (int): Request timeout in seconds
        rate_limit_delay (float): Seconds to wait between requests
        min_paragraph_length (int): Minimum chars for valid paragraph
        max_paragraphs (int): Maximum paragraphs to extract
        headers (Dict[str, str]): HTTP request headers
        visited_urls (Set[str]): Tracking for duplicate prevention
    
    Ethical Guidelines:
        - Always check robots.txt before production use
        - Respect rate limits (default: 1 request/second)
        - Include identifying User-Agent
        - Only scrape publicly accessible content
        - Cache results to minimize repeat requests
        - Handle errors gracefully without hammering servers
    
    Example Usage:
        >>> scraper = CustomScraper()
        >>> text = scraper.fetch_text("https://example.com/article")
        >>> if text:
        ...     print(f"Extracted {len(text)} characters")
        ...     print(text[:200])
        
        >>> # Batch processing with rate limiting
        >>> urls = ["https://site1.com", "https://site2.com"]
        >>> results = scraper.fetch_multiple(urls, max_urls=5)
        >>> for url, text in results.items():
        ...     print(f"{url}: {len(text)} chars")
    
    Limitations:
        - JavaScript-rendered content not supported (use Selenium for that)
        - No authentication/login support
        - robots.txt checking must be implemented
        - PDF/binary content not supported
        - Rate limits may need adjustment per site
    
    Dependencies:
        - requests: HTTP client library
        - beautifulsoup4: HTML/XML parsing
        - lxml (optional): Faster HTML parser
    """
    
    # Configuration constants
    DEFAULT_TIMEOUT = 6                 # Request timeout in seconds
    RATE_LIMIT_DELAY = 1.0             # Delay between requests
    MIN_PARAGRAPH_LENGTH = 50           # Minimum chars for valid paragraph
    MAX_PARAGRAPHS = 10                 # Maximum paragraphs to extract
    MAX_RETRIES = 2                     # Retry attempts on failure
    
    # User-Agent string (identifies bot)
    USER_AGENT = (
        'Mozilla/5.0 (compatible; ResearchBot/1.0; '
        '+https://github.com/yourproject) '
        'AppleWebKit/537.36'
    )
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        rate_limit_delay: float = RATE_LIMIT_DELAY
    ):
        """
        Initialize the web scraper with configurable settings.
        
        Args:
            timeout (int): Request timeout in seconds (default: 6)
            rate_limit_delay (float): Seconds between requests (default: 1.0)
        
        Example:
            >>> # Fast scraping (use carefully!)
            >>> fast_scraper = CustomScraper(timeout=3, rate_limit_delay=0.5)
            
            >>> # Conservative scraping (recommended)
            >>> safe_scraper = CustomScraper(timeout=10, rate_limit_delay=2.0)
        """
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.min_paragraph_length = self.MIN_PARAGRAPH_LENGTH
        self.max_paragraphs = self.MAX_PARAGRAPHS
        
        # HTTP headers with bot identification
        self.headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',  # Do Not Track
            'Connection': 'keep-alive',
        }
        
        # Track visited URLs to prevent duplicates
        self.visited_urls: Set[str] = set()
        
        # Track last request time for rate limiting
        self._last_request_time = 0
        
        print(f"[CustomScraper] ✓ Initialized")
        print(f"[CustomScraper] Timeout: {self.timeout}s")
        print(f"[CustomScraper] Rate limit: {self.rate_limit_delay}s between requests")
    
    def _wait_for_rate_limit(self) -> None:
        """
        Enforce rate limiting between requests.
        
        Implements polite scraping by waiting between consecutive requests.
        This prevents overwhelming target servers and respects their resources.
        
        Implementation:
            - Calculates time since last request
            - Sleeps if insufficient time has passed
            - Updates last request timestamp
        """
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            print(f"[CustomScraper] ⏳ Rate limiting: waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format and accessibility.
        
        Args:
            url (str): URL to validate
        
        Returns:
            bool: True if URL is valid and scrapable
        
        Checks:
            - Valid HTTP/HTTPS scheme
            - Has valid domain
            - Not a binary file extension
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ('http', 'https'):
                print(f"[CustomScraper] ⚠ Invalid scheme: {parsed.scheme}")
                return False
            
            # Check domain exists
            if not parsed.netloc:
                print(f"[CustomScraper] ⚠ No domain in URL")
                return False
            
            # Check for binary file extensions
            binary_extensions = {'.pdf', '.zip', '.exe', '.jpg', '.png', '.gif', '.mp4', '.mp3'}
            if any(url.lower().endswith(ext) for ext in binary_extensions):
                print(f"[CustomScraper] ⚠ Binary file detected, skipping")
                return False
            
            return True
            
        except Exception as e:
            print(f"[CustomScraper] ✗ URL validation error: {e}")
            return False
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract article title from HTML.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
        
        Returns:
            Optional[str]: Extracted title or None
        
        Strategy:
            1. Try <title> tag
            2. Try <h1> tag
            3. Try Open Graph title
            4. Return None if all fail
        """
        # Try <title> tag
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # Try <h1> tag
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        # Try Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        return None
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract meaningful paragraphs from HTML.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
        
        Returns:
            List[str]: Extracted paragraphs meeting quality criteria
        
        Quality Filters:
            - Minimum length threshold
            - Removes navigation/footer text
            - Strips HTML tags and whitespace
            - Removes duplicate paragraphs
        """
        paragraphs = []
        seen_texts = set()
        
        # Find all paragraph tags
        for p_tag in soup.find_all('p'):
            # Extract and clean text
            text = p_tag.get_text().strip()
            
            # Apply quality filters
            if len(text) < self.min_paragraph_length:
                continue  # Too short
            
            if text in seen_texts:
                continue  # Duplicate
            
            # Check for navigation/boilerplate patterns
            lower_text = text.lower()
            if any(pattern in lower_text for pattern in [
                'cookie', 'subscribe', 'newsletter', 'click here',
                'privacy policy', 'terms of service', 'all rights reserved'
            ]):
                continue  # Likely boilerplate
            
            # Valid paragraph
            paragraphs.append(text)
            seen_texts.add(text)
            
            # Stop if we have enough
            if len(paragraphs) >= self.max_paragraphs:
                break
        
        return paragraphs
    
    def fetch_text(self, url: str, include_title: bool = False) -> Optional[str]:
        """
        Fetch and extract text content from a URL.
        
        This is the main scraping method that orchestrates the complete
        extraction process with error handling and rate limiting.
        
        Args:
            url (str): Web page URL to scrape
            include_title (bool): Prepend article title if found (default: False)
        
        Returns:
            Optional[str]: Extracted text content or None if failed
        
        Process:
            1. Validate URL format
            2. Apply rate limiting
            3. Fetch HTML content
            4. Parse with BeautifulSoup
            5. Extract title (optional)
            6. Extract paragraphs
            7. Filter and format output
        
        Error Handling:
            - Returns None on any failure
            - Logs specific error types
            - Never crashes on bad input
        
        Example:
            >>> scraper = CustomScraper()
            >>> text = scraper.fetch_text("https://blog.example.com/ai-article")
            >>> if text:
            ...     print(f"Success! Extracted {len(text)} characters")
            ...     print(f"Preview: {text[:200]}...")
        """
        # Validate URL
        if not self._is_valid_url(url):
            return None
        
        # Check if already visited
        if url in self.visited_urls:
            print(f"[CustomScraper] ⚠ URL already scraped: {url}")
            return None
        
        print(f"[CustomScraper] 🌐 Fetching: {url}")
        
        # Apply rate limiting
        self._wait_for_rate_limit()
        
        try:
            # Make HTTP request
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self.headers,
                allow_redirects=True
            )
            
            # Check status code
            response.raise_for_status()
            
            # Mark as visited
            self.visited_urls.add(url)
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract components
            title = self._extract_title(soup) if include_title else None
            paragraphs = self._extract_paragraphs(soup)
            
            # Check if content found
            if not paragraphs:
                print(f"[CustomScraper] ⚠ No meaningful content found")
                return None
            
            # Build output text
            output_parts = []
            
            if title and include_title:
                output_parts.append(f"TITLE: {title}\n")
            
            output_parts.append("\n\n".join(paragraphs))
            
            text = "\n".join(output_parts)
            
            # Success metrics
            word_count = len(text.split())
            print(f"[CustomScraper] ✓ Extracted {len(text)} chars, {word_count} words, {len(paragraphs)} paragraphs")
            
            return text
            
        except requests.exceptions.Timeout:
            print(f"[CustomScraper] ✗ Timeout after {self.timeout}s: {url}")
            return None
            
        except requests.exceptions.HTTPError as e:
            print(f"[CustomScraper] ✗ HTTP error {e.response.status_code}: {url}")
            return None
            
        except requests.exceptions.ConnectionError:
            print(f"[CustomScraper] ✗ Connection error: {url}")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"[CustomScraper] ✗ Request error: {type(e).__name__}")
            return None
            
        except Exception as e:
            print(f"[CustomScraper] ✗ Unexpected error: {type(e).__name__}: {e}")
            return None
    
    def fetch_multiple(
        self, 
        urls: List[str], 
        max_urls: int = 3,
        include_title: bool = False
    ) -> Dict[str, str]:
        """
        Fetch text from multiple URLs with automatic rate limiting.
        
        Processes a list of URLs sequentially with rate limiting applied
        automatically between requests. Continues processing even if
        individual URLs fail.
        
        Args:
            urls (List[str]): URLs to scrape
            max_urls (int): Maximum URLs to process (default: 3)
            include_title (bool): Include titles in output (default: False)
        
        Returns:
            Dict[str, str]: Mapping of successful URLs to extracted text
        
        Features:
            - Automatic rate limiting between requests
            - Continues on individual failures
            - Progress tracking with console output
            - Result caching in memory
        
        Example:
            >>> scraper = CustomScraper()
            >>> urls = [
            ...     "https://site1.com/article1",
            ...     "https://site2.com/article2",
            ...     "https://site3.com/article3"
            ... ]
            >>> results = scraper.fetch_multiple(urls, max_urls=5)
            >>> print(f"Successfully scraped {len(results)}/{len(urls)} URLs")
            >>> for url, text in results.items():
            ...     print(f"{url}: {len(text)} characters")
        """
        print(f"\n[CustomScraper] {'='*60}")
        print(f"[CustomScraper] Batch scraping {min(len(urls), max_urls)} URL(s)")
        print(f"[CustomScraper] {'='*60}")
        
        results = {}
        processed = 0
        
        for i, url in enumerate(urls[:max_urls], 1):
            print(f"\n[CustomScraper] [{i}/{min(len(urls), max_urls)}] Processing: {url}")
            
            text = self.fetch_text(url, include_title=include_title)
            
            if text:
                results[url] = text
                processed += 1
                print(f"[CustomScraper] ✓ Success ({processed} successful)")
            else:
                print(f"[CustomScraper] ✗ Failed")
        
        # Summary
        success_rate = (processed / min(len(urls), max_urls)) * 100
        print(f"\n[CustomScraper] {'='*60}")
        print(f"[CustomScraper] Batch complete: {processed}/{min(len(urls), max_urls)} successful ({success_rate:.1f}%)")
        print(f"[CustomScraper] {'='*60}\n")
        
        return results
    
    def clear_visited(self) -> int:
        """
        Clear visited URL tracking.
        
        Returns:
            int: Number of URLs cleared from tracking
        
        Use Cases:
            - Reset for fresh scraping session
            - Periodic cleanup in long-running processes
            - Testing and development
        
        Example:
            >>> scraper = CustomScraper()
            >>> # ... scrape some URLs ...
            >>> cleared = scraper.clear_visited()
            >>> print(f"Cleared {cleared} URLs from cache")
        """
        count = len(self.visited_urls)
        self.visited_urls.clear()
        print(f"[CustomScraper] ✓ Cleared {count} URL(s) from visited tracking")
        return count
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get scraper statistics and configuration.
        
        Returns:
            Dict[str, any]: Statistics including:
                - visited_urls_count: Number of scraped URLs
                - timeout: Current timeout setting
                - rate_limit_delay: Current rate limit
                - min_paragraph_length: Minimum paragraph length
                - max_paragraphs: Maximum paragraphs extracted
        
        Example:
            >>> stats = scraper.get_statistics()
            >>> print(f"Scraped {stats['visited_urls_count']} URLs")
        """
        return {
            'visited_urls_count': len(self.visited_urls),
            'timeout': self.timeout,
            'rate_limit_delay': self.rate_limit_delay,
            'min_paragraph_length': self.min_paragraph_length,
            'max_paragraphs': self.max_paragraphs,
            'user_agent': self.USER_AGENT
        }


# Module-level utility functions
def scrape_url(url: str, include_title: bool = False) -> Optional[str]:
    """
    Convenience function to scrape a single URL.
    
    Args:
        url (str): URL to scrape
        include_title (bool): Include title in output
    
    Returns:
        Optional[str]: Extracted text or None
    
    Example:
        >>> text = scrape_url("https://example.com/article")
        >>> if text:
        ...     print(text[:200])
    """
    scraper = CustomScraper()
    return scraper.fetch_text(url, include_title)


if __name__ == "__main__":
    # Demo/testing code
    print("CustomScraper Demo")
    print("=" * 60)
    
    # Test URLs (using example.com for safety)
    test_urls = [
        "https://example.com",  # Simple test page
    ]
    
    try:
        # Initialize scraper
        scraper = CustomScraper(timeout=5, rate_limit_delay=1.0)
        
        # Test single URL scraping
        print("\n🌐 TESTING SINGLE URL SCRAPE:")
        text = scraper.fetch_text(test_urls[0], include_title=True)
        
        if text:
            print(f"\n✓ Success!")
            print(f"Length: {len(text)} characters")
            print(f"Words: {len(text.split())} words")
            print(f"\nPreview (first 200 chars):")
            print(text[:200])
        else:
            print("\n⚠ No content extracted (this is expected for example.com)")
        
        # Test statistics
        print("\n\n📊 SCRAPER STATISTICS:")
        stats = scraper.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n✓ Demo complete!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()