import json
import re
import google.generativeai as genai
import os

class QueryUnderstandingAgent:
    """
    Agent that analyzes user queries and breaks them into research subtopics.
    Also detects user preferences like "short", "detailed", "tweet thread", etc.
    """
    
    def __init__(self):
        # Configure Gemini API
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Load prompt template
        import os.path as path
        prompt_path = path.join(path.dirname(__file__), '..', '..', 'prompts', 'query_understanding.txt')
        with open(prompt_path, 'r') as f:
            self.prompt_template = f.read()
    
    def run(self, query: str):
        """
        Analyze query and return subtopics + detected preferences.
        
        Args:
            query: User's research question
            
        Returns:
            dict with 'subtopics' (list) and 'preferences' (dict)
        """
        print(f"\n[QueryUnderstandingAgent] Processing query: {query}")
        
        # Detect user preferences
        preferences = self._detect_preferences(query)
        
        # Generate subtopics using Gemini
        subtopics = self._generate_subtopics(query)
        
        result = {
            'subtopics': subtopics,
            'preferences': preferences
        }
        
        print(f"[QueryUnderstandingAgent] Generated {len(subtopics)} subtopics")
        print(f"[QueryUnderstandingAgent] Detected preferences: {preferences}")
        
        return result
    
    def _detect_preferences(self, query: str):
        """Detect user preferences from query text"""
        query_lower = query.lower()
        preferences = {}
        
        # Detect length preference
        if any(word in query_lower for word in ['short', 'brief', 'concise', 'quick']):
            preferences['length'] = 'short'
        elif any(word in query_lower for word in ['detailed', 'comprehensive', 'in-depth']):
            preferences['length'] = 'detailed'
        else:
            preferences['length'] = 'medium'
        
        # Detect format preference
        if 'tweet' in query_lower or 'twitter' in query_lower:
            preferences['format'] = 'tweet_thread'
        elif 'bullet' in query_lower or 'list' in query_lower:
            preferences['format'] = 'bullet_list'
        else:
            preferences['format'] = 'paragraph'
        
        return preferences
    
    def _generate_subtopics(self, query: str):
        """Use Gemini to generate research subtopics"""
        # Format prompt with query
        prompt = self.prompt_template.format(query=query)
        
        try:
            # Call Gemini
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse JSON response
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*|\s*```', '', response_text)
            subtopics = json.loads(response_text)
            
            # Validate it's a list
            if not isinstance(subtopics, list):
                raise ValueError("Response is not a list")
            
            # Ensure we have 3-5 subtopics
            if len(subtopics) < 3:
                subtopics = subtopics + ["general overview", "practical applications"]
            subtopics = subtopics[:5]  # Cap at 5
            
            return subtopics
            
        except Exception as e:
            print(f"[QueryUnderstandingAgent] Error generating subtopics: {e}")
            # Fallback: simple keyword-based splitting
            return self._fallback_subtopics(query)
    
    def _fallback_subtopics(self, query: str):
        """Simple fallback if API fails"""
        return [
            f"{query} - overview",
            f"{query} - current trends",
            f"{query} - practical applications"
        ]