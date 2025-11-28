"""
Action Plan Agent Module

This module converts research summaries into concrete, actionable plans using Google's Gemini AI.
It generates structured action items and quick-start guides to help users immediately apply research findings.

Author: Google Hackathon Team
License: MIT
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.rate_limiter import get_rate_limiter, retry_on_rate_limit


class ActionPlanAgent:
    """
    Transforms research summaries into actionable execution plans.
    
    This agent serves as the final step in the research pipeline, converting 
    synthesized insights into concrete, measurable action items. It provides 
    both a comprehensive checklist and an immediate quick-start guide.
    
    Architecture:
        - Uses Google Gemini 2.0 Flash for rapid action generation
        - Implements rate limiting and retry logic for API reliability
        - Returns structured JSON output for easy integration
    
    Key Features:
        - Generates 5 specific, measurable action items
        - Creates 3-step quick-start guide for immediate execution
        - Includes fallback mechanism for API failures
        - Context-aware based on original query
    
    Attributes:
        model (GenerativeModel): Configured Gemini 2.0 Flash model instance
        
    Example Usage:
        >>> agent = ActionPlanAgent()
        >>> result = agent.run(summary="AI adoption requires...", 
        ...                    original_query="How to implement AI?")
        >>> print(f"Actions: {len(result['checklist'])}")
        >>> for action in result['checklist']:
        ...     print(f"☐ {action}")
    
    Dependencies:
        - google-generativeai: Gemini API client
        - python-dotenv: Environment variable management
        - Custom rate_limiter utility for API throttling
    """
    
    # Model configuration
    MODEL_NAME = "gemini-2.0-flash"
    CHECKLIST_SIZE = 5
    QUICK_START_SIZE = 3
    
    def __init__(self):
        """
        Initialize the ActionPlanAgent with Gemini API configuration.
        
        Raises:
            ValueError: If GOOGLE_API_KEY is not found in environment
        """
        # Retrieve API key with fallback
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. Please set it in your .env file or environment variables."
            )
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.MODEL_NAME)
        
        print(f"[ActionPlanAgent] Initialized with model: {self.MODEL_NAME}")
    
    def run(self, summary: str, original_query: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Generate a comprehensive action plan from research summary.
        
        This is the main entry point for action plan generation. It orchestrates
        the process of converting research insights into actionable steps.
        
        Args:
            summary (str): The synthesized research summary containing key findings
            original_query (str, optional): Original user query for additional context.
                                           Helps tailor actions to user's specific needs.
        
        Returns:
            Dict[str, List[str]]: Action plan containing:
                - 'checklist': List of 5 specific, measurable action items
                - 'quick_start': List of 3 immediate next steps
        
        Example:
            >>> agent = ActionPlanAgent()
            >>> plan = agent.run(
            ...     summary="Research shows AI adoption needs executive buy-in...",
            ...     original_query="How to implement AI in my company?"
            ... )
            >>> print(plan['quick_start'][0])
            "Step 1: Schedule meeting with C-suite to present AI benefits"
        """
        print(f"\n{'='*60}")
        print(f"[ActionPlanAgent] Starting action plan generation")
        print(f"{'='*60}")
        
        if original_query:
            print(f"[ActionPlanAgent] Context: {original_query[:80]}...")
        
        # Generate the action plan using LLM
        action_plan = self._generate_action_plan(summary, original_query)
        
        # Log results
        print(f"\n[ActionPlanAgent] ✓ Successfully created action plan:")
        print(f"  - {len(action_plan['checklist'])} checklist items")
        print(f"  - {len(action_plan['quick_start'])} quick-start steps")
        print(f"{'='*60}\n")
        
        return action_plan
    
    @retry_on_rate_limit(max_retries=3, backoff_factor=2)
    def _generate_action_plan(
        self, 
        summary: str, 
        original_query: Optional[str]
    ) -> Dict[str, List[str]]:
        """
        Generate actionable steps using Gemini LLM with rate limiting.
        
        This method constructs a carefully crafted prompt to ensure the LLM
        generates practical, specific actions. It includes retry logic and
        rate limiting to handle API constraints gracefully.
        
        Args:
            summary (str): Research summary to convert into actions
            original_query (str, optional): Original query for context
        
        Returns:
            Dict[str, List[str]]: Structured action plan with validated format
        
        Raises:
            Exception: Falls back to default plan if generation fails
        
        Implementation Notes:
            - Uses rate limiter to prevent API quota exhaustion
            - Requests JSON-only output to avoid parsing issues
            - Validates response structure before returning
            - Implements fallback for any failure scenario
        """
        # Apply rate limiting before API call
        rate_limiter = get_rate_limiter()
        rate_limiter.wait_if_needed()
        
        # Prepare context if original query provided
        query_context = ""
        if original_query:
            query_context = f"Original Question: {original_query}\n\n"
        
        # Construct prompt for action plan generation
        # Key aspects: specificity, measurability, immediate applicability
        prompt = f"""{query_context}Based on the following research summary, create a concrete action plan:

RESEARCH SUMMARY:
{summary}

REQUIREMENTS:
1. Generate a checklist of {self.CHECKLIST_SIZE} specific, measurable action items
   - Each item should be concrete and actionable
   - Items should be prioritized by importance
   - Include measurable outcomes where possible

2. Create a {self.QUICK_START_SIZE}-step quick start guide
   - Focus on immediate next steps (within 24-48 hours)
   - Each step should be achievable and clear
   - Steps should build upon each other

OUTPUT FORMAT:
Return ONLY valid JSON (no markdown, no explanation) in this exact structure:
{{
  "checklist": [
    "Action item 1 with specific details",
    "Action item 2 with specific details",
    "Action item 3 with specific details",
    "Action item 4 with specific details",
    "Action item 5 with specific details"
  ],
  "quick_start": [
    "Step 1: Concrete first action with timeline",
    "Step 2: Follow-up action building on step 1",
    "Step 3: Final immediate step to build momentum"
  ]
}}"""

        try:
            # Generate content using Gemini
            print("[ActionPlanAgent] Calling Gemini API...")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean potential markdown formatting
            response_text = (
                response_text
                .replace('```json', '')
                .replace('```', '')
                .strip()
            )
            
            # Parse JSON response
            action_plan = json.loads(response_text)
            
            # Validate required keys exist
            if 'checklist' not in action_plan or 'quick_start' not in action_plan:
                raise ValueError("Response missing required keys: 'checklist' or 'quick_start'")
            
            # Ensure correct list sizes (trim if too long, keep if shorter)
            action_plan['checklist'] = action_plan['checklist'][:self.CHECKLIST_SIZE]
            action_plan['quick_start'] = action_plan['quick_start'][:self.QUICK_START_SIZE]
            
            # Validate we have content
            if not action_plan['checklist'] or not action_plan['quick_start']:
                raise ValueError("Generated plan contains empty lists")
            
            print("[ActionPlanAgent] ✓ Successfully generated and validated action plan")
            return action_plan
            
        except json.JSONDecodeError as e:
            print(f"[ActionPlanAgent] ✗ JSON parsing error: {e}")
            print(f"[ActionPlanAgent] Response was: {response_text[:200]}...")
            return self._fallback_action_plan()
            
        except Exception as e:
            print(f"[ActionPlanAgent] ✗ Error during generation: {type(e).__name__}: {e}")
            return self._fallback_action_plan()
    
    def _fallback_action_plan(self) -> Dict[str, List[str]]:
        """
        Provide a generic fallback action plan when LLM generation fails.
        
        This ensures the system always returns a valid action plan structure,
        even if the AI service is unavailable. The fallback provides general
        but still useful guidance applicable to most research scenarios.
        
        Returns:
            Dict[str, List[str]]: Generic but practical action plan
        
        Design Philosophy:
            - Actions are universally applicable to research findings
            - Focus on analysis and planning rather than domain-specific steps
            - Maintains the same structure as AI-generated plans
        """
        print("[ActionPlanAgent] ⚠ Using fallback action plan")
        
        return {
            'checklist': [
                "Review all research findings and identify the top 3 most relevant insights",
                "Document key takeaways and how they apply to your specific situation",
                "Identify stakeholders who should be involved in implementation",
                "Create a realistic timeline with milestones for implementation",
                "Define measurable success metrics to track progress"
            ],
            'quick_start': [
                "Step 1: Within 24 hours, review the highest-priority finding and note immediate applications",
                "Step 2: Within 48 hours, gather any required resources or information identified in the research",
                "Step 3: Within 72 hours, take one concrete action toward implementation"
            ]
        }


# Module-level utility for standalone usage
def generate_action_plan(
    summary: str, 
    original_query: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    Convenience function to generate action plan without instantiating agent.
    
    Args:
        summary (str): Research summary
        original_query (str, optional): Original user query
    
    Returns:
        Dict[str, List[str]]: Action plan with checklist and quick_start
    
    Example:
        >>> plan = generate_action_plan("AI requires training data...")
        >>> print(plan['checklist'][0])
    """
    agent = ActionPlanAgent()
    return agent.run(summary, original_query)


if __name__ == "__main__":
    # Demo/testing code
    print("ActionPlanAgent Demo")
    print("=" * 60)
    
    demo_summary = """
    Research indicates that successful AI implementation requires three key components:
    1. Executive buy-in and clear business objectives
    2. High-quality training data and infrastructure
    3. Cross-functional team with both technical and domain expertise
    """
    
    demo_query = "How do I implement AI in my organization?"
    
    try:
        plan = generate_action_plan(demo_summary, demo_query)
        
        print("\n📋 CHECKLIST:")
        for i, item in enumerate(plan['checklist'], 1):
            print(f"  {i}. ☐ {item}")
        
        print("\n🚀 QUICK START:")
        for step in plan['quick_start']:
            print(f"  • {step}")
            
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")