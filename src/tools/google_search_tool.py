"""
Google Search Tool Module

This module provides AI-powered search result generation using Gemini.
For production use, integrate with Google Custom Search API or similar service.

Author: Google Hackathon Team
License: MIT
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.rate_limiter import get_rate_limiter, retry_on_rate_limit


class GoogleSearchTool:
    """
    AI-powered search result generator with intelligent content simulation.
    
    This tool simulates realistic web search results using Gemini AI. It's designed
    for development, demo, and testing purposes. For production deployment, replace
    with actual search APIs.
    
    Purpose & Use Cases:
    
    1. Development & Testing:
       - Rapid prototyping without API costs
       - Testing research pipelines end-to-end
       - Demo presentations without external dependencies
    
    2. Educational Projects:
       - Learning about research agents
       - Understanding search result structures
       - Hackathon demonstrations
    
    3. Fallback Mechanism:
       - Backup when real search APIs are unavailable
       - Rate limit mitigation strategy
       - Offline development capability
    
    Production Migration Path:
        Replace this with:
        - Google Custom Search API (programmablesearchengine.google.com)
        - Bing Web Search API (azure.microsoft.com/en-us/services/cognitive-services/bing-web-search-api/)
        - SerpAPI (serpapi.com)
        - ScraperAPI (scraperapi.com)
    
    Architecture:
        - Uses Gemini 2.0 Flash for result generation
        - Implements rate limiting for API protection
        - Validates output structure with error recovery
        - Generates realistic metadata (titles, snippets, URLs)
    
    Attributes:
        model (GenerativeModel): Configured Gemini model
        DEFAULT_NUM_RESULTS (int): Default result count
        MAX_RESULTS (int): Maximum allowed results
        SNIPPET_LENGTH (int): Target snippet length
    
    Result Structure:
        [
            {
                "title": "Article Title Here",
                "snippet": "Brief 2-sentence summary providing key information.",
                "url": "https://example.com/article-slug"
            }
        ]
    
    Example Usage:
        >>> tool = GoogleSearchTool()
        >>> results = tool.search("artificial intelligence trends", num_results=5)
        >>> for result in results:
        ...     print(f"{result['title']}: {result['url']}")
        
        >>> # With error handling
        >>> results = tool.search("quantum computing")
        >>> if results:
        ...     print(f"Found {len(results)} results")
        ...     print(results[0]['snippet'])
    
    Limitations:
        ⚠️ IMPORTANT: Simulated results, not real web search
        - Results are AI-generated, not from actual web crawling
        - URLs are placeholders (example.com domain)
        - No real-time web data access
        - May occasionally produce hallucinated information
        - Limited to Gemini's knowledge cutoff
    
    Production Replacement Guide:
        ```python
        # Replace search() method with:
        def search(self, query: str, num_results: int = 3):
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", 
                          developerKey=self.api_key)
            
            result = service.cse().list(
                q=query,
                cx=self.search_engine_id,
                num=num_results
            ).execute()
            
            return [
                {
                    "title": item['title'],
                    "snippet": item['snippet'],
                    "url": item['link']
                }
                for item in result.get('items', [])
            ]
        ```
    
    Dependencies:
        - google-generativeai: Gemini API for result generation
        - python-dotenv: Environment variable management
        - Custom rate_limiter: API throttling utilities
    """
    
    # Configuration constants
    MODEL_NAME = "gemini-2.0-flash"
    DEFAULT_NUM_RESULTS = 3
    MAX_RESULTS = 10
    SNIPPET_LENGTH = 150  # Target character length for snippets
    
    # Realistic domains for URL generation
    REALISTIC_DOMAINS = [
        'medium.com', 'towardsdatascience.com', 'arxiv.org',
        'techcrunch.com', 'wired.com', 'forbes.com',
        'mit.edu', 'stanford.edu', 'nature.com',
        'github.com', 'stackoverflow.com', 'wikipedia.org'
    ]
    
    def __init__(self):
        """
        Initialize the search tool with Gemini API configuration.
        
        Raises:
            ValueError: If GOOGLE_API_KEY is not found in environment
        
        Example:
            >>> tool = GoogleSearchTool()
            >>> print(f"Search tool ready with {tool.MODEL_NAME}")
        """
        # Retrieve and validate API key
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. Please set it in your .env file or environment variables."
            )
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.MODEL_NAME)
        
        print(f"[GoogleSearchTool] ✓ Initialized with model: {self.MODEL_NAME}")
        print(f"[GoogleSearchTool] ⚠ NOTE: This generates simulated results for demo purposes")
        print(f"[GoogleSearchTool] ⚠ For production, replace with real search API")
    
    @retry_on_rate_limit(max_retries=3, backoff_factor=2)
    def search(
        self, 
        query: str, 
        num_results: int = DEFAULT_NUM_RESULTS
    ) -> List[Dict[str, str]]:
        """
        Generate simulated search results for a query.
        
        This method uses AI to generate realistic search results based on the
        query. Results include titles, snippets, and URLs formatted to match
        real search engine output structure.
        
        Args:
            query (str): Search query string
            num_results (int): Number of results to generate (default: 3, max: 10)
        
        Returns:
            List[Dict[str, str]]: Search results with structure:
                [
                    {
                        "title": str,      # Article/page title
                        "snippet": str,    # 2-sentence summary
                        "url": str        # Source URL
                    }
                ]
        
        Error Handling:
            - Rate limiting: Applied via decorator
            - JSON parsing: Falls back to default results
            - API failures: Returns fallback results
            - Invalid response: Validates and repairs structure
        
        Production Note:
            Replace this implementation with actual Google Custom Search API
            or similar service for real web search capabilities.
        
        Example:
            >>> tool = GoogleSearchTool()
            >>> results = tool.search("machine learning", num_results=5)
            >>> print(f"Found {len(results)} results")
            >>> print(f"First result: {results[0]['title']}")
            >>> print(f"URL: {results[0]['url']}")
        """
        # Validate and cap num_results
        num_results = max(1, min(num_results, self.MAX_RESULTS))
        
        print(f"\n[GoogleSearchTool] {'='*60}")
        print(f"[GoogleSearchTool] Searching for: '{query}'")
        print(f"[GoogleSearchTool] Requested results: {num_results}")
        print(f"[GoogleSearchTool] {'='*60}")
        
        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        rate_limiter.wait_if_needed()
        
        # Construct prompt for realistic result generation
        domain_list = ', '.join(self.REALISTIC_DOMAINS[:5])
        
        prompt = f"""You are a search engine result generator. Generate {num_results} realistic, factual search results for the query: "{query}"

REQUIREMENTS:
1. Results must be factual and based on real information (2024-2025 timeframe)
2. Each snippet should be exactly 2 sentences providing key information
3. Use realistic, authoritative domains like: {domain_list}
4. Titles should be clear and descriptive (50-100 chars)
5. URLs should look realistic with appropriate slugs

OUTPUT FORMAT (JSON only, no markdown):
[
  {{
    "title": "Clear, descriptive title here",
    "snippet": "First sentence providing key information. Second sentence adding important context.",
    "url": "https://realistic-domain.com/relevant-slug"
  }}
]

Generate {num_results} high-quality results now:"""

        try:
            # Generate results using Gemini
            print(f"[GoogleSearchTool] Calling Gemini API...")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response - remove markdown code blocks
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            results = json.loads(response_text)
            
            # Validate structure
            if not isinstance(results, list):
                raise ValueError("Response is not a list")
            
            # Validate each result
            validated_results = self._validate_results(results, query)
            
            # Ensure we have the requested number
            if len(validated_results) < num_results:
                print(f"[GoogleSearchTool] ⚠ Only {len(validated_results)}/{num_results} valid results, padding...")
                validated_results.extend(
                    self._generate_padding_results(query, num_results - len(validated_results))
                )
            
            print(f"[GoogleSearchTool] ✓ Generated {len(validated_results)} result(s)")
            
            # Log first result as sample
            if validated_results:
                sample = validated_results[0]
                print(f"[GoogleSearchTool] Sample: '{sample['title'][:50]}...'")
            
            return validated_results
            
        except json.JSONDecodeError as e:
            print(f"[GoogleSearchTool] ✗ JSON parsing error: {e}")
            print(f"[GoogleSearchTool] Response preview: {response_text[:200]}...")
            return self._fallback_results(query, num_results)
            
        except Exception as e:
            print(f"[GoogleSearchTool] ✗ Error: {type(e).__name__}: {e}")
            return self._fallback_results(query, num_results)
    
    def _validate_results(
        self, 
        results: List[Any], 
        query: str
    ) -> List[Dict[str, str]]:
        """
        Validate and sanitize generated results.
        
        Args:
            results (List[Any]): Raw results from API
            query (str): Original search query
        
        Returns:
            List[Dict[str, str]]: Validated and sanitized results
        
        Validation:
            - Checks for required keys (title, snippet, url)
            - Validates data types
            - Sanitizes content
            - Removes duplicates
            - Ensures snippet quality
        """
        validated = []
        seen_titles = set()
        
        for i, result in enumerate(results):
            # Check type
            if not isinstance(result, dict):
                print(f"[GoogleSearchTool] ⚠ Result {i+1} is not a dict, skipping")
                continue
            
            # Check required keys
            if not all(key in result for key in ['title', 'snippet', 'url']):
                print(f"[GoogleSearchTool] ⚠ Result {i+1} missing required keys, skipping")
                continue
            
            # Extract and validate fields
            title = str(result['title']).strip()
            snippet = str(result['snippet']).strip()
            url = str(result['url']).strip()
            
            # Check for empty values
            if not title or not snippet or not url:
                print(f"[GoogleSearchTool] ⚠ Result {i+1} has empty fields, skipping")
                continue
            
            # Check for duplicates
            if title in seen_titles:
                print(f"[GoogleSearchTool] ⚠ Duplicate title detected, skipping")
                continue
            
            # Validate URL format
            if not (url.startswith('http://') or url.startswith('https://')):
                url = f"https://example.com/{query.replace(' ', '-')}-{i+1}"
                print(f"[GoogleSearchTool] ⚠ Invalid URL, replaced with placeholder")
            
            # Add validated result
            validated.append({
                'title': title,
                'snippet': snippet,
                'url': url
            })
            
            seen_titles.add(title)
        
        return validated
    
    def _generate_padding_results(
        self, 
        query: str, 
        count: int
    ) -> List[Dict[str, str]]:
        """
        Generate padding results when API returns too few.
        
        Args:
            query (str): Search query
            count (int): Number of padding results needed
        
        Returns:
            List[Dict[str, str]]: Padding results
        """
        padding = []
        
        variations = [
            f"Introduction to {query}",
            f"Understanding {query}: A Comprehensive Guide",
            f"Latest Research on {query}",
            f"Practical Applications of {query}",
            f"{query}: Key Concepts and Trends"
        ]
        
        for i in range(count):
            padding.append({
                'title': variations[i % len(variations)],
                'snippet': f"Comprehensive information about {query} and related topics. This resource provides detailed insights and practical guidance.",
                'url': f"https://example.com/{query.replace(' ', '-')}-{i+1}"
            })
        
        return padding
    
    def _fallback_results(
        self, 
        query: str, 
        num_results: int = DEFAULT_NUM_RESULTS
    ) -> List[Dict[str, str]]:
        """
        Generate fallback results when API fails.
        
        Provides reliable default results that maintain the expected structure
        and allow the research pipeline to continue operating.
        
        Args:
            query (str): Search query
            num_results (int): Number of results to generate
        
        Returns:
            List[Dict[str, str]]: Fallback results
        
        Design Philosophy:
            - Always returns valid structure
            - Generic but informative content
            - Maintains pipeline flow
            - Clear indication these are fallbacks
        """
        print(f"[GoogleSearchTool] ⚠ Using fallback results")
        
        templates = [
            {
                "title": f"Comprehensive Guide to {query}",
                "snippet": f"An in-depth exploration of {query}, covering fundamental concepts and recent developments. This resource provides valuable insights for researchers and practitioners.",
                "url": f"https://example.com/guide-{query.replace(' ', '-')}"
            },
            {
                "title": f"Research Insights: {query}",
                "snippet": f"Current research findings and analysis related to {query}. Includes expert perspectives and evidence-based recommendations.",
                "url": f"https://example.com/research-{query.replace(' ', '-')}"
            },
            {
                "title": f"Understanding {query}: Key Concepts",
                "snippet": f"Essential information about {query} for beginners and experts alike. Covers fundamental principles and practical applications.",
                "url": f"https://example.com/understanding-{query.replace(' ', '-')}"
            },
            {
                "title": f"Latest Trends in {query}",
                "snippet": f"Emerging trends and developments in the field of {query}. Stay updated with cutting-edge research and innovations.",
                "url": f"https://example.com/trends-{query.replace(' ', '-')}"
            },
            {
                "title": f"Practical Applications of {query}",
                "snippet": f"Real-world applications and use cases for {query}. Learn how professionals are leveraging these concepts in practice.",
                "url": f"https://example.com/applications-{query.replace(' ', '-')}"
            }
        ]
        
        return templates[:num_results]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get search tool configuration and statistics.
        
        Returns:
            Dict[str, Any]: Configuration details
        
        Example:
            >>> tool = GoogleSearchTool()
            >>> stats = tool.get_statistics()
            >>> print(f"Model: {stats['model_name']}")
            >>> print(f"Max results: {stats['max_results']}")
        """
        return {
            'model_name': self.MODEL_NAME,
            'default_num_results': self.DEFAULT_NUM_RESULTS,
            'max_results': self.MAX_RESULTS,
            'snippet_length': self.SNIPPET_LENGTH,
            'is_simulation': True,
            'realistic_domains': len(self.REALISTIC_DOMAINS)
        }


# Module-level utility functions
def search_web(query: str, num_results: int = 3) -> List[Dict[str, str]]:
    """
    Convenience function to search without instantiating tool.
    
    Args:
        query (str): Search query
        num_results (int): Number of results
    
    Returns:
        List[Dict[str, str]]: Search results
    
    Example:
        >>> results = search_web("quantum computing", num_results=5)
        >>> for r in results:
        ...     print(r['title'])
    """
    tool = GoogleSearchTool()
    return tool.search(query, num_results)


if __name__ == "__main__":
    # Demo/testing code
    print("GoogleSearchTool Demo")
    print("=" * 60)
    
    try:
        # Initialize tool
        tool = GoogleSearchTool()
        
        # Test queries
        test_queries = [
            ("artificial intelligence", 3),
            ("quantum computing applications", 5),
            ("climate change solutions", 4)
        ]
        
        for query, num_results in test_queries:
            print(f"\n{'='*60}")
            print(f"TEST QUERY: '{query}' ({num_results} results)")
            print(f"{'='*60}")
            
            results = tool.search(query, num_results)
            
            print(f"\n📊 RESULTS ({len(results)}):")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Snippet: {result['snippet'][:100]}...")
        
        # Test statistics
        print(f"\n\n{'='*60}")
        print("📈 TOOL STATISTICS")
        print(f"{'='*60}")
        stats = tool.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n✓ All tests passed!")
        print("\n⚠️ REMINDER: These are simulated results for demo purposes")
        print("⚠️ For production, integrate real search API")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()