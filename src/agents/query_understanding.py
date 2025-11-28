"""
Query Understanding Agent Module

This module analyzes natural language queries and decomposes them into focused research subtopics.
It serves as the entry point to the research pipeline, extracting intent and user preferences.

Author: Google Hackathon Team
License: MIT
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.rate_limiter import get_rate_limiter, retry_on_rate_limit


class QueryUnderstandingAgent:
    """
    Natural language query analyzer with intelligent subtopic decomposition.
    
    This agent serves as the intelligent entry point to the research pipeline,
    performing two critical functions:
    
    1. Query Decomposition: Breaks down complex queries into 3-5 focused,
       researchable subtopics that can be investigated independently
    
    2. Preference Detection: Extracts user preferences from natural language:
       - Length: short, medium, detailed
       - Format: paragraph, bullet_list, tweet_thread
    
    The decomposition strategy uses AI to identify key aspects of a query,
    ensuring comprehensive coverage while maintaining focus. Each subtopic
    is designed to be independently researchable and collectively exhaustive.
    
    Architecture:
        - Uses Google Gemini 2.0 Flash for intelligent query analysis
        - Template-based prompting for consistent subtopic generation
        - Keyword-based preference detection for reliability
        - Fallback mechanisms for robustness
    
    Attributes:
        model (GenerativeModel): Configured Gemini model
        prompt_template (str): Loaded prompt template for subtopic generation
        MIN_SUBTOPICS (int): Minimum required subtopics (default: 3)
        MAX_SUBTOPICS (int): Maximum allowed subtopics (default: 5)
    
    Example Usage:
        >>> agent = QueryUnderstandingAgent()
        >>> result = agent.run("How can AI improve healthcare outcomes?")
        >>> print(result['subtopics'])
        ['AI diagnostic tools', 'Predictive analytics in healthcare', 
         'Treatment personalization', 'Healthcare automation']
        >>> print(result['preferences'])
        {'length': 'medium', 'format': 'paragraph'}
    
    Dependencies:
        - google-generativeai: Gemini API for query analysis
        - python-dotenv: Environment variable management
        - prompts/query_understanding.txt: Prompt template file
        - Custom rate_limiter: API throttling utilities
    """
    
    # Configuration constants
    MODEL_NAME = "gemini-2.0-flash"
    MIN_SUBTOPICS = 3
    MAX_SUBTOPICS = 5
    PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / 'prompts' / 'query_understanding.txt'
    
    # Preference detection keywords
    LENGTH_KEYWORDS = {
        'short': ['short', 'brief', 'concise', 'quick', 'summary', 'tldr'],
        'detailed': ['detailed', 'comprehensive', 'in-depth', 'thorough', 'complete', 'extensive'],
    }
    
    FORMAT_KEYWORDS = {
        'tweet_thread': ['tweet', 'twitter', 'thread'],
        'bullet_list': ['bullet', 'list', 'points', 'items'],
    }
    
    def __init__(self):
        """
        Initialize the QueryUnderstandingAgent with Gemini API and prompt template.
        
        Raises:
            ValueError: If GOOGLE_API_KEY is not found in environment
            FileNotFoundError: If prompt template file is missing
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
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        print(f"[QueryUnderstandingAgent] Initialized with model: {self.MODEL_NAME}")
        print(f"[QueryUnderstandingAgent] Subtopic range: {self.MIN_SUBTOPICS}-{self.MAX_SUBTOPICS}")
    
    def _load_prompt_template(self) -> str:
        """
        Load the query understanding prompt template from file.
        
        Returns:
            str: Prompt template content with {query} placeholder
        
        Raises:
            FileNotFoundError: If template file doesn't exist
        
        Implementation Notes:
            - Uses Path for cross-platform compatibility
            - Expects template with {query} placeholder
            - Caches template in memory after loading
        """
        try:
            with open(self.PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                template = f.read()
            
            print(f"[QueryUnderstandingAgent] ✓ Loaded prompt template from {self.PROMPT_TEMPLATE_PATH.name}")
            return template
            
        except FileNotFoundError:
            error_msg = (
                f"Prompt template not found at: {self.PROMPT_TEMPLATE_PATH}\n"
                f"Please ensure the file exists in the prompts directory."
            )
            print(f"[QueryUnderstandingAgent] ✗ {error_msg}")
            raise FileNotFoundError(error_msg)
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Analyze query and decompose into subtopics with detected preferences.
        
        This is the main entry point that orchestrates the complete query
        understanding process:
        1. Detect user preferences from natural language hints
        2. Generate focused research subtopics using AI
        3. Validate and normalize output
        
        Args:
            query (str): User's natural language research question
        
        Returns:
            Dict[str, Any]: Analysis results containing:
                - 'subtopics': List[str] - 3-5 focused research areas
                - 'preferences': Dict[str, str] - Detected user preferences
                    * 'length': 'short' | 'medium' | 'detailed'
                    * 'format': 'paragraph' | 'bullet_list' | 'tweet_thread'
        
        Example:
            >>> agent = QueryUnderstandingAgent()
            >>> result = agent.run("Give me a brief overview of quantum computing")
            >>> result['preferences']['length']
            'short'
            >>> len(result['subtopics'])
            4
        """
        print(f"\n{'='*60}")
        print(f"[QueryUnderstandingAgent] Processing query")
        print(f"{'='*60}")
        print(f"[QueryUnderstandingAgent] Query: '{query}'")
        
        # Phase 1: Detect user preferences
        print(f"\n[QueryUnderstandingAgent] Phase 1: Preference Detection")
        preferences = self._detect_preferences(query)
        print(f"[QueryUnderstandingAgent] ✓ Detected preferences:")
        print(f"  - Length: {preferences['length']}")
        print(f"  - Format: {preferences['format']}")
        
        # Phase 2: Generate research subtopics
        print(f"\n[QueryUnderstandingAgent] Phase 2: Subtopic Generation")
        subtopics = self._generate_subtopics(query)
        print(f"[QueryUnderstandingAgent] ✓ Generated {len(subtopics)} subtopic(s):")
        for i, subtopic in enumerate(subtopics, 1):
            print(f"  {i}. {subtopic}")
        
        # Compile results
        result = {
            'subtopics': subtopics,
            'preferences': preferences
        }
        
        print(f"\n{'='*60}")
        print(f"[QueryUnderstandingAgent] ✓ Query understanding complete")
        print(f"{'='*60}\n")
        
        return result
    
    def _detect_preferences(self, query: str) -> Dict[str, str]:
        """
        Extract user preferences from natural language query.
        
        Uses keyword matching to detect implicit user preferences about
        desired output length and format. This provides a simple but
        effective way to customize research output without explicit commands.
        
        Args:
            query (str): User's query text
        
        Returns:
            Dict[str, str]: Detected preferences:
                - length: 'short' | 'medium' | 'detailed'
                - format: 'paragraph' | 'bullet_list' | 'tweet_thread'
        
        Detection Logic:
            - Length: Scans for keywords like 'brief', 'detailed', 'comprehensive'
            - Format: Detects requests for specific formats like 'bullet points' or 'tweet'
            - Defaults: Returns 'medium' and 'paragraph' if no keywords found
        
        Example:
            >>> agent._detect_preferences("Give me a quick summary in bullet points")
            {'length': 'short', 'format': 'bullet_list'}
        """
        query_lower = query.lower()
        preferences = {}
        
        # Detect length preference
        length_detected = False
        for length_type, keywords in self.LENGTH_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                preferences['length'] = length_type
                length_detected = True
                break
        
        if not length_detected:
            preferences['length'] = 'medium'  # Default
        
        # Detect format preference
        format_detected = False
        for format_type, keywords in self.FORMAT_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                preferences['format'] = format_type
                format_detected = True
                break
        
        if not format_detected:
            preferences['format'] = 'paragraph'  # Default
        
        return preferences
    
    @retry_on_rate_limit(max_retries=3, backoff_factor=2)
    def _generate_subtopics(self, query: str) -> List[str]:
        """
        Generate focused research subtopics using Gemini AI.
        
        Uses a carefully crafted prompt template to instruct the AI to
        decompose the query into 3-5 independently researchable subtopics.
        Each subtopic should be:
        - Specific enough to research effectively
        - Broad enough to yield meaningful results
        - Collectively comprehensive for the original query
        
        Args:
            query (str): User's research question
        
        Returns:
            List[str]: 3-5 focused subtopic strings
        
        Error Handling:
            - Rate limiting: Applied before API call
            - JSON parsing: Handles both clean and markdown-wrapped responses
            - Validation: Ensures minimum/maximum subtopic counts
            - Fallback: Returns generic subtopics if AI fails
        
        Implementation Notes:
            - Expects JSON array response from AI
            - Strips markdown code fences automatically
            - Pads with generic subtopics if too few returned
            - Truncates if too many returned
        """
        # Apply rate limiting before API call
        rate_limiter = get_rate_limiter()
        rate_limiter.wait_if_needed()
        
        # Format prompt template with user's query
        prompt = self.prompt_template.format(query=query)
        
        try:
            # Generate subtopics using Gemini
            print(f"[QueryUnderstandingAgent] Calling Gemini API for subtopic generation...")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response - remove markdown code blocks
            # Handles formats like: ```json\n[...]\n``` or ```[...]```
            response_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            
            # Parse JSON response
            subtopics = json.loads(response_text)
            
            # Validate response is a list
            if not isinstance(subtopics, list):
                raise ValueError(f"Expected list, got {type(subtopics).__name__}")
            
            # Validate all items are strings
            if not all(isinstance(item, str) for item in subtopics):
                raise ValueError("Subtopics list contains non-string items")
            
            # Ensure minimum subtopic count
            if len(subtopics) < self.MIN_SUBTOPICS:
                print(f"[QueryUnderstandingAgent] ⚠ Only {len(subtopics)} subtopics generated, padding to {self.MIN_SUBTOPICS}")
                subtopics.extend([
                    f"{query} - general overview",
                    f"{query} - practical applications",
                    f"{query} - current trends"
                ][:self.MIN_SUBTOPICS - len(subtopics)])
            
            # Cap at maximum subtopic count
            if len(subtopics) > self.MAX_SUBTOPICS:
                print(f"[QueryUnderstandingAgent] ⚠ {len(subtopics)} subtopics generated, capping at {self.MAX_SUBTOPICS}")
                subtopics = subtopics[:self.MAX_SUBTOPICS]
            
            print(f"[QueryUnderstandingAgent] ✓ Successfully generated {len(subtopics)} subtopic(s)")
            return subtopics
            
        except json.JSONDecodeError as e:
            print(f"[QueryUnderstandingAgent] ✗ JSON parsing error: {e}")
            print(f"[QueryUnderstandingAgent] Response was: {response_text[:200]}...")
            return self._fallback_subtopics(query)
            
        except ValueError as e:
            print(f"[QueryUnderstandingAgent] ✗ Validation error: {e}")
            return self._fallback_subtopics(query)
            
        except Exception as e:
            print(f"[QueryUnderstandingAgent] ✗ Error during generation: {type(e).__name__}: {e}")
            return self._fallback_subtopics(query)
    
    def _fallback_subtopics(self, query: str) -> List[str]:
        """
        Generate generic fallback subtopics when AI generation fails.
        
        Provides a reliable fallback that works for any query. The subtopics
        are intentionally generic but still provide comprehensive coverage:
        - Overview: Foundation and background
        - Current Trends: Recent developments
        - Practical Applications: Real-world use cases
        
        Args:
            query (str): Original user query
        
        Returns:
            List[str]: Generic subtopics based on query
        
        Design Philosophy:
            - Always returns exactly 3 subtopics (minimum required)
            - Subtopics are broadly applicable to any topic
            - Maintains consistent structure for downstream processing
        """
        print(f"[QueryUnderstandingAgent] ⚠ Using fallback subtopic generation")
        
        fallback_subtopics = [
            f"{query} - overview and fundamentals",
            f"{query} - current trends and developments",
            f"{query} - practical applications and use cases"
        ]
        
        return fallback_subtopics


# Module-level utility functions
def analyze_query(query: str) -> Dict[str, Any]:
    """
    Convenience function to analyze query without instantiating agent.
    
    Args:
        query (str): User's research question
    
    Returns:
        Dict[str, Any]: Analysis with subtopics and preferences
    
    Example:
        >>> result = analyze_query("What is machine learning?")
        >>> print(result['subtopics'])
    """
    agent = QueryUnderstandingAgent()
    return agent.run(query)


def extract_subtopics(query: str) -> List[str]:
    """
    Quick utility to extract only subtopics without preferences.
    
    Args:
        query (str): User's research question
    
    Returns:
        List[str]: Generated subtopics
    
    Example:
        >>> subtopics = extract_subtopics("AI in education")
        >>> for subtopic in subtopics:
        ...     print(f"- {subtopic}")
    """
    result = analyze_query(query)
    return result['subtopics']


if __name__ == "__main__":
    # Demo/testing code
    print("QueryUnderstandingAgent Demo")
    print("=" * 60)
    
    # Test various query types
    test_queries = [
        "What is quantum computing?",
        "Give me a brief summary of AI ethics in bullet points",
        "Explain blockchain technology in detail",
        "How can I use machine learning in my business? Keep it short."
    ]
    
    try:
        agent = QueryUnderstandingAgent()
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*60}")
            print(f"TEST {i}: {query}")
            print(f"{'='*60}")
            
            result = agent.run(query)
            
            print(f"\n📋 SUBTOPICS:")
            for j, subtopic in enumerate(result['subtopics'], 1):
                print(f"  {j}. {subtopic}")
            
            print(f"\n⚙️ PREFERENCES:")
            print(f"  Length: {result['preferences']['length']}")
            print(f"  Format: {result['preferences']['format']}")
            
            print()  # Spacing between tests
            
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()