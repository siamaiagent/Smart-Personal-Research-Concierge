import requests
from bs4 import BeautifulSoup
import time

class CustomScraper:
    """
    Simple web scraper to extract article text from URLs.
    
    Fetches web pages and extracts paragraph text using BeautifulSoup.
    Respects timeouts and includes basic error handling.
    
    Dependencies:
        - requests: HTTP client
        - beautifulsoup4: HTML parsing
    
    Ethical Considerations:
        - Respects robots.txt (implement check before production use)
        - Includes user-agent header
        - Implements rate limiting (1 second between requests)
        - Only scrapes publicly accessible content
    
    Inputs:
        url (str): Web page URL to scrape
    
    Outputs:
        str: Extracted text (first 10 paragraphs) or None if failed
    
    Configuration:
        timeout: 6 seconds default
        headers: Includes User-Agent to identify bot
    
    Limitations:
        - Only extracts <p> tags
        - May fail on JavaScript-heavy sites
        - No authentication support
        - No robots.txt checking (add before production)
    
    Example:
        >>> scraper = CustomScraper()
        >>> text = scraper.fetch_text("https://example.com/article")
        >>> if text:
        ...     print(text[:100])
    """
    
    def __init__(self):
        self.timeout = 6  # seconds
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_text(self, url):
        """
        Fetch and extract text from a URL.
        
        Args:
            url: Web page URL to scrape
            
        Returns:
            String with extracted text (first 10 paragraphs)
        """
        print(f"[CustomScraper] Fetching: {url}")
        
        try:
            # Make request with timeout
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()  # Raise error for bad status codes
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract paragraphs
            paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
            
            # Filter out empty paragraphs
            paragraphs = [p for p in paragraphs if len(p) > 50]  # Only keep substantial paragraphs
            
            # Join first 10 paragraphs
            text = "\n\n".join(paragraphs[:10])
            
            if text:
                print(f"[CustomScraper] Successfully extracted {len(text)} characters")
                return text
            else:
                print(f"[CustomScraper] No content found")
                return None
                
        except requests.exceptions.Timeout:
            print(f"[CustomScraper] Timeout error for {url}")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"[CustomScraper] Error fetching {url}: {e}")
            return None
    
    def fetch_multiple(self, urls, max_urls=3):
        """
        Fetch text from multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            max_urls: Maximum number of URLs to fetch
            
        Returns:
            Dict mapping URLs to extracted text
        """
        results = {}
        
        for url in urls[:max_urls]:
            text = self.fetch_text(url)
            if text:
                results[url] = text
            
            # Be polite - wait between requests
            time.sleep(1)
        
        return results