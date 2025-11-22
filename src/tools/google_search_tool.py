import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

class GoogleSearchTool:
    """
    Simulates Google Search using Gemini to generate realistic search results.
    For production, replace with actual Google Search API.
    """
    
    def __init__(self):
        import os
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def search(self, query: str, num_results: int = 3):
        """
        Simulate search results for a query.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of dicts with 'title', 'snippet', 'url'
        """
        print(f"[GoogleSearchTool] Searching for: {query}")
        
        prompt = f"""Generate {num_results} realistic search results for the query: "{query}"

Return ONLY a JSON array with this exact format:
[
  {{
    "title": "Article title",
    "snippet": "Brief 2-sentence summary of key information",
    "url": "https://example.com/article"
  }}
]

Make the results factual, current (2024-2025), and relevant. Use realistic domains like .com, .org, .edu"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response - remove markdown code blocks
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            results = json.loads(response_text)
            
            print(f"[GoogleSearchTool] Found {len(results)} results")
            return results
            
        except Exception as e:
            print(f"[GoogleSearchTool] Error: {e}")
            return self._fallback_results(query)
    
    def _fallback_results(self, query):
        """Fallback if API fails"""
        return [
            {
                "title": f"Research on {query}",
                "snippet": f"Comprehensive information about {query} and related topics.",
                "url": "https://example.com/research"
            }
        ]