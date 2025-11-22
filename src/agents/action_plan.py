import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

class ActionPlanAgent:
    """
    Agent that converts research summary into actionable steps.
    """
    
    def __init__(self):
        import os
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def run(self, summary: str, original_query: str = None):
        """
        Generate action plan from summary.
        
        Args:
            summary: Research summary text
            original_query: Original user query for context
            
        Returns:
            Dict with 'checklist' and 'quick_start'
        """
        print(f"\n[ActionPlanAgent] Generating action plan")
        
        action_plan = self._generate_action_plan(summary, original_query)
        
        print(f"[ActionPlanAgent] Created {len(action_plan['checklist'])} action items")
        return action_plan
    
    def _generate_action_plan(self, summary: str, original_query: str):
        """Generate actionable steps using LLM"""
        
        query_context = f"Original question: {original_query}\n\n" if original_query else ""
        
        prompt = f"""{query_context}Based on this research summary, create an actionable plan:

{summary}

Generate:
1. A checklist of 5 specific action items (concrete, measurable steps)
2. A 3-step quick start guide (immediate next steps)

Return ONLY valid JSON in this exact format:
{{
  "checklist": [
    "Action item 1",
    "Action item 2",
    "Action item 3",
    "Action item 4",
    "Action item 5"
  ],
  "quick_start": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ]
}}"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean JSON
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            action_plan = json.loads(response_text)
            
            # Validate structure
            if 'checklist' not in action_plan or 'quick_start' not in action_plan:
                raise ValueError("Invalid format")
            
            # Ensure we have exactly 5 checklist items and 3 quick start steps
            action_plan['checklist'] = action_plan['checklist'][:5]
            action_plan['quick_start'] = action_plan['quick_start'][:3]
            
            return action_plan
            
        except Exception as e:
            print(f"[ActionPlanAgent] Error: {e}")
            return self._fallback_action_plan()
    
    def _fallback_action_plan(self):
        """Fallback action plan"""
        return {
            'checklist': [
                "Review the research findings thoroughly",
                "Identify key insights relevant to your situation",
                "Consult with relevant stakeholders",
                "Create an implementation timeline",
                "Set measurable success metrics"
            ],
            'quick_start': [
                "Step 1: Start with the highest-priority finding",
                "Step 2: Gather necessary resources",
                "Step 3: Take the first concrete action within 24 hours"
            ]
        }