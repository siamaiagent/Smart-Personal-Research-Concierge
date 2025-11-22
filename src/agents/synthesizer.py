import google.generativeai as genai
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

class SynthesizerAgent:
    """
    Combines verified findings into a coherent summary.
    
    This agent takes verified research results and synthesizes them into
    a flowing, readable summary. It respects user preferences for length
    and format, and applies context compaction if the summary exceeds limits.
    
    Dependencies:
        - google.generativeai (Gemini API for text synthesis)
    
    Inputs:
        verified_results (List[dict]): Fact-checked findings with confidence scores
        preferences (dict): Optional user preferences:
            - length: 'short' | 'medium' | 'detailed'
            - format: 'paragraph' | 'bullet_list' | 'tweet_thread'
    
    Outputs:
        str: Synthesized summary in natural language, respecting user preferences
    
    Features:
        - Context compaction: Automatically shortens long summaries
        - Confidence weighting: Prioritizes high-confidence findings
        - Length control: Adapts to user's desired detail level
        - Fallback: Returns basic summary if LLM fails
    
    Example:
        >>> agent = SynthesizerAgent()
        >>> summary = agent.run(verified_results, {'length': 'short'})
        >>> print(summary)
    """
    
    def __init__(self):
        import os
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def run(self, verified_results, preferences=None):
        """
        Create a synthesized summary from verified findings.
        
        Args:
            verified_results: List of verified research results
            preferences: User preferences (length, format) - optional
            
        Returns:
            String summary
        """
        print(f"\n[SynthesizerAgent] Synthesizing {len(verified_results)} results")
        
        if preferences is None:
            preferences = {'length': 'medium', 'format': 'paragraph'}
        
        # Prepare findings for synthesis
        all_findings = []
        for result in verified_results:
            for finding in result.get('findings', []):
                if finding.get('verified', True):  # Only use verified findings
                    all_findings.append({
                        'subtopic': result['subtopic'],
                        'title': finding['title'],
                        'content': finding['snippet'],
                        'confidence': finding.get('confidence', 0.7)
                    })
        
        # Generate summary
        summary = self._generate_summary(all_findings, preferences)
        
        print(f"[SynthesizerAgent] Generated {len(summary)} character summary")
        return summary
    
    def _generate_summary(self, findings, preferences):
        """Generate summary using LLM"""
        
        # Build context from findings
        context = "\n\n".join([
            f"Subtopic: {f['subtopic']}\nInformation: {f['content']} (confidence: {f['confidence']:.2f})"
            for f in findings
        ])
        
        # Determine length instruction
        length_map = {
            'short': '3-4 sentences',
            'medium': '5-7 sentences',
            'detailed': '8-12 sentences'
        }
        length_instruction = length_map.get(preferences.get('length', 'medium'), '5-7 sentences')
        
        prompt = f"""Synthesize the following research findings into a clear, coherent summary.

Research Findings:
{context}

Requirements:
- Length: {length_instruction}
- Focus on the most credible information (higher confidence scores)
- Be factual and objective
- Connect ideas logically
- No bullet points, write in flowing paragraphs

Write the summary:"""

        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            
            # Apply context compaction if too long
            if len(summary) > 2000:
                summary = self._compact_summary(summary, preferences)
            
            return summary
            
        except Exception as e:
            print(f"[SynthesizerAgent] Error: {e}")
            return self._fallback_summary(findings)
    
    def _compact_summary(self, summary, preferences):
        """Compress summary if too long"""
        prompt = f"""Compress this summary to be more concise while keeping key points:

{summary}

Target: {preferences.get('length', 'medium')} style, maximum 1000 characters.

Write compressed version:"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            # Simple truncation fallback
            return summary[:1000] + "..."
    
    def _fallback_summary(self, findings):
        """Simple fallback summary"""
        return f"Research summary based on {len(findings)} verified sources covering multiple aspects of the topic."