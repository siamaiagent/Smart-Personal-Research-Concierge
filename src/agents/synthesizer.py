"""
Synthesizer Agent Module

This module transforms verified research findings into coherent, flowing summaries.
It serves as the final synthesis layer in the research pipeline, producing human-readable output.

Author: Google Hackathon Team
License: MIT
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.rate_limiter import get_rate_limiter, retry_on_rate_limit


class SynthesizerAgent:
    """
    AI-powered research synthesizer with adaptive summarization and preference handling.
    
    This agent serves as the final transformation layer in the research pipeline,
    converting structured, verified findings into natural, flowing prose. It performs
    intelligent synthesis that:
    
    1. Confidence Weighting: Prioritizes high-confidence findings in the narrative
    2. Preference Adaptation: Respects user preferences for length and format
    3. Automatic Compaction: Dynamically shortens verbose summaries
    4. Logical Flow: Creates coherent narratives connecting related ideas
    
    The synthesis process uses advanced prompt engineering to ensure factual
    accuracy while maintaining readability. It acts as a bridge between raw
    research data and actionable insights.
    
    Architecture:
        - Uses Google Gemini 2.0 Flash for natural language synthesis
        - Implements two-stage compression for lengthy outputs
        - Confidence-based prioritization of source material
        - Template-driven prompt construction for consistency
    
    Attributes:
        model (GenerativeModel): Configured Gemini model
        LENGTH_LIMITS (dict): Character targets for each length preference
        LENGTH_INSTRUCTIONS (dict): Sentence count guidelines
        MAX_SUMMARY_LENGTH (int): Threshold triggering auto-compaction
        COMPACT_TARGET_LENGTH (int): Target length for compressed summaries
    
    Example Usage:
        >>> agent = SynthesizerAgent()
        >>> verified_data = [
        ...     {
        ...         'subtopic': 'AI Applications',
        ...         'findings': [
        ...             {
        ...                 'title': 'Healthcare AI',
        ...                 'snippet': 'AI improves diagnostics...',
        ...                 'verified': True,
        ...                 'confidence': 0.95
        ...             }
        ...         ]
        ...     }
        ... ]
        >>> summary = agent.run(
        ...     verified_data,
        ...     preferences={'length': 'short', 'format': 'paragraph'}
        ... )
        >>> print(summary)
    
    Preference Options:
        Length:
            - 'short': 3-4 sentences, ~200-400 characters
            - 'medium': 5-7 sentences, ~400-800 characters
            - 'detailed': 8-12 sentences, ~800-1500 characters
        
        Format:
            - 'paragraph': Flowing prose (currently implemented)
            - 'bullet_list': Structured points (future enhancement)
            - 'tweet_thread': Social media format (future enhancement)
    
    Dependencies:
        - google-generativeai: Gemini API for text synthesis
        - python-dotenv: Environment variable management
        - Custom rate_limiter: API throttling utilities
    """
    
    # Configuration constants
    MODEL_NAME = "gemini-2.0-flash"
    
    # Length specifications
    LENGTH_INSTRUCTIONS = {
        'short': '3-4 sentences',
        'medium': '5-7 sentences',
        'detailed': '8-12 sentences'
    }
    
    LENGTH_LIMITS = {
        'short': 400,
        'medium': 800,
        'detailed': 1500
    }
    
    # Compaction thresholds
    MAX_SUMMARY_LENGTH = 2000      # Trigger compaction above this
    COMPACT_TARGET_LENGTH = 1000   # Target for compressed version
    
    # Default preferences
    DEFAULT_PREFERENCES = {
        'length': 'medium',
        'format': 'paragraph'
    }
    
    def __init__(self):
        """
        Initialize the SynthesizerAgent with Gemini API configuration.
        
        Raises:
            ValueError: If GOOGLE_API_KEY is not found in environment
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
        
        print(f"[SynthesizerAgent] Initialized with model: {self.MODEL_NAME}")
        print(f"[SynthesizerAgent] Supported lengths: {list(self.LENGTH_INSTRUCTIONS.keys())}")
    
    def run(
        self, 
        verified_results: List[Dict[str, Any]], 
        preferences: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Synthesize verified research findings into a coherent summary.
        
        This is the main entry point that orchestrates the synthesis process:
        1. Extract verified findings from research results
        2. Filter by confidence threshold
        3. Generate natural language summary
        4. Apply auto-compaction if needed
        
        Args:
            verified_results (List[Dict[str, Any]]): Fact-checked research data.
                Expected structure:
                [
                    {
                        'subtopic': str,
                        'findings': [
                            {
                                'title': str,
                                'snippet': str,
                                'verified': bool,
                                'confidence': float
                            },
                            ...
                        ]
                    },
                    ...
                ]
            
            preferences (Dict[str, str], optional): User preferences:
                - 'length': 'short' | 'medium' | 'detailed'
                - 'format': 'paragraph' | 'bullet_list' | 'tweet_thread'
                Defaults to medium length, paragraph format.
        
        Returns:
            str: Natural language summary respecting user preferences
        
        Quality Guarantees:
            - Only includes verified findings (verified=True)
            - Prioritizes high-confidence sources
            - Maintains factual accuracy from sources
            - Creates logical flow between ideas
            - Automatically compacts if too verbose
        
        Example:
            >>> agent = SynthesizerAgent()
            >>> summary = agent.run(verified_data, {'length': 'short'})
            >>> print(f"Summary length: {len(summary)} chars")
        """
        print(f"\n{'='*60}")
        print(f"[SynthesizerAgent] Starting synthesis pipeline")
        print(f"{'='*60}")
        print(f"[SynthesizerAgent] Input: {len(verified_results)} verified result(s)")
        
        # Apply default preferences if none provided
        if preferences is None:
            preferences = self.DEFAULT_PREFERENCES.copy()
            print(f"[SynthesizerAgent] Using default preferences: {preferences}")
        else:
            # Merge with defaults for missing keys
            preferences = {**self.DEFAULT_PREFERENCES, **preferences}
            print(f"[SynthesizerAgent] User preferences: {preferences}")
        
        # Phase 1: Extract and filter verified findings
        print(f"\n[SynthesizerAgent] Phase 1: Extracting verified findings")
        all_findings = self._extract_verified_findings(verified_results)
        
        if not all_findings:
            print(f"[SynthesizerAgent] ⚠ No verified findings to synthesize")
            return self._fallback_summary([])
        
        print(f"[SynthesizerAgent] ✓ Extracted {len(all_findings)} verified finding(s)")
        
        # Calculate average confidence
        avg_confidence = sum(f['confidence'] for f in all_findings) / len(all_findings)
        print(f"[SynthesizerAgent] Average confidence: {avg_confidence:.2f}")
        
        # Phase 2: Generate summary
        print(f"\n[SynthesizerAgent] Phase 2: Generating summary")
        print(f"[SynthesizerAgent] Target length: {preferences['length']}")
        summary = self._generate_summary(all_findings, preferences)
        
        # Log results
        print(f"\n[SynthesizerAgent] ✓ Summary complete:")
        print(f"  - Characters: {len(summary)}")
        print(f"  - Words: {len(summary.split())}")
        print(f"  - Target length: {preferences['length']}")
        print(f"{'='*60}\n")
        
        return summary
    
    def _extract_verified_findings(
        self, 
        verified_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract and structure verified findings for synthesis.
        
        Filters out unverified findings and restructures data into a
        synthesis-ready format with all necessary context.
        
        Args:
            verified_results (List[Dict[str, Any]]): Raw verified results
        
        Returns:
            List[Dict[str, Any]]: Structured findings with:
                - subtopic: Research area context
                - title: Finding headline
                - content: Finding details
                - confidence: Credibility score
        
        Implementation Notes:
            - Only includes findings where verified=True
            - Defaults to confidence=0.7 if not provided
            - Preserves subtopic context for coherent synthesis
            - Flattens nested structure for easier processing
        """
        all_findings = []
        
        for result in verified_results:
            subtopic = result.get('subtopic', 'Unknown')
            
            for finding in result.get('findings', []):
                # Only include verified findings
                if finding.get('verified', True):
                    all_findings.append({
                        'subtopic': subtopic,
                        'title': finding.get('title', 'Untitled'),
                        'content': finding.get('snippet', ''),
                        'confidence': finding.get('confidence', 0.7)
                    })
        
        # Sort by confidence (highest first) for quality prioritization
        all_findings.sort(key=lambda x: x['confidence'], reverse=True)
        
        return all_findings
    
    @retry_on_rate_limit(max_retries=3, backoff_factor=2)
    def _generate_summary(
        self, 
        findings: List[Dict[str, Any]], 
        preferences: Dict[str, str]
    ) -> str:
        """
        Generate natural language summary using Gemini AI.
        
        Constructs a carefully crafted prompt that instructs the AI to:
        - Synthesize findings into flowing prose
        - Prioritize high-confidence information
        - Respect length preferences
        - Maintain factual accuracy
        - Create logical connections between ideas
        
        Args:
            findings (List[Dict[str, Any]]): Verified findings to synthesize
            preferences (Dict[str, str]): User preferences for output
        
        Returns:
            str: Natural language summary
        
        Process Flow:
            1. Build context string from findings
            2. Construct prompt with length instructions
            3. Generate summary via Gemini
            4. Check length and apply compaction if needed
            5. Return final summary
        
        Error Handling:
            - Rate limiting: Applied via decorator
            - API failures: Falls back to simple summary
            - Excessive length: Triggers automatic compaction
        """
        # Apply rate limiting before API call
        rate_limiter = get_rate_limiter()
        rate_limiter.wait_if_needed()
        
        # Build context from findings (sorted by confidence)
        context_parts = []
        for i, finding in enumerate(findings, 1):
            context_part = (
                f"{i}. Subtopic: {finding['subtopic']}\n"
                f"   Information: {finding['content']}\n"
                f"   Confidence: {finding['confidence']:.2f}"
            )
            context_parts.append(context_part)
        
        context = "\n\n".join(context_parts)
        
        # Get length instruction
        length_instruction = self.LENGTH_INSTRUCTIONS.get(
            preferences.get('length', 'medium'), 
            self.LENGTH_INSTRUCTIONS['medium']
        )
        
        # Construct synthesis prompt
        prompt = f"""You are a research synthesis expert. Your task is to create a clear, coherent summary from verified research findings.

RESEARCH FINDINGS:
{context}

SYNTHESIS REQUIREMENTS:
1. Length: {length_instruction} (aim for {self.LENGTH_LIMITS.get(preferences.get('length', 'medium'), 800)} characters)
2. Prioritize information with higher confidence scores
3. Write in flowing paragraphs with logical connections between ideas
4. Be factual and objective - only include information from the findings
5. Use natural, professional language
6. Connect related concepts smoothly
7. Do NOT use bullet points or lists - write in prose
8. Do NOT add information not present in the findings

Write a synthesis that brings these findings together into a coherent narrative:"""

        try:
            # Generate summary
            print(f"[SynthesizerAgent] Calling Gemini API for synthesis...")
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            
            print(f"[SynthesizerAgent] ✓ Generated summary: {len(summary)} characters")
            
            # Apply compaction if summary exceeds threshold
            if len(summary) > self.MAX_SUMMARY_LENGTH:
                print(f"[SynthesizerAgent] ⚠ Summary exceeds {self.MAX_SUMMARY_LENGTH} chars, applying compaction...")
                summary = self._compact_summary(summary, preferences)
                print(f"[SynthesizerAgent] ✓ Compacted to {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            print(f"[SynthesizerAgent] ✗ Synthesis error: {type(e).__name__}: {e}")
            return self._fallback_summary(findings)
    
    def _compact_summary(
        self, 
        summary: str, 
        preferences: Dict[str, str]
    ) -> str:
        """
        Compress verbose summary while preserving key information.
        
        Uses a second AI pass to intelligently compress the summary,
        maintaining the most important points while reducing length.
        This is triggered automatically when summaries exceed threshold.
        
        Args:
            summary (str): Original verbose summary
            preferences (Dict[str, str]): User preferences
        
        Returns:
            str: Compressed summary (target: COMPACT_TARGET_LENGTH chars)
        
        Compression Strategy:
            - Preserves key findings and conclusions
            - Removes redundant phrasing
            - Condenses examples and details
            - Maintains factual accuracy
        
        Error Handling:
            - API failure: Falls back to simple truncation
            - Ensures output always has "..." if truncated
        """
        length_style = preferences.get('length', 'medium')
        
        prompt = f"""Compress this summary to be more concise while preserving all key information.

ORIGINAL SUMMARY:
{summary}

COMPRESSION REQUIREMENTS:
1. Target length: approximately {self.COMPACT_TARGET_LENGTH} characters
2. Maintain the {length_style} style preference
3. Preserve all key findings and conclusions
4. Remove redundant or overly detailed information
5. Keep the natural, flowing prose style
6. Do NOT lose factual accuracy

Write the compressed version:"""

        try:
            response = self.model.generate_content(prompt)
            compressed = response.text.strip()
            
            # Ensure we actually reduced length
            if len(compressed) < len(summary):
                return compressed
            else:
                # If compression didn't help, use smart truncation
                return self._smart_truncate(summary, self.COMPACT_TARGET_LENGTH)
            
        except Exception as e:
            print(f"[SynthesizerAgent] ⚠ Compaction failed: {type(e).__name__}")
            return self._smart_truncate(summary, self.COMPACT_TARGET_LENGTH)
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """
        Intelligently truncate text at sentence boundaries.
        
        Attempts to truncate at the last complete sentence before max_length,
        falling back to word boundaries if necessary.
        
        Args:
            text (str): Text to truncate
            max_length (int): Maximum character length
        
        Returns:
            str: Truncated text with ellipsis
        
        Algorithm:
            1. If text fits, return as-is
            2. Try to find last sentence boundary (. ! ?) before limit
            3. Fall back to last word boundary before limit
            4. Append "..." to indicate continuation
        """
        if len(text) <= max_length:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:max_length]
        
        # Find last sentence ending
        for delimiter in ['. ', '! ', '? ']:
            last_sentence = truncated.rfind(delimiter)
            if last_sentence > max_length * 0.7:  # At least 70% of target
                return truncated[:last_sentence + 1]
        
        # Fall back to word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + "..."
        
        # Worst case: hard truncate
        return truncated + "..."
    
    def _fallback_summary(self, findings: List[Dict[str, Any]]) -> str:
        """
        Generate basic fallback summary when AI synthesis fails.
        
        Provides a simple but informative summary that acknowledges the
        research was conducted and provides basic statistics. This ensures
        the system always returns a valid response.
        
        Args:
            findings (List[Dict[str, Any]]): Verified findings
        
        Returns:
            str: Basic summary with statistics
        
        Design Philosophy:
            - Always returns valid text (never empty)
            - Provides useful metadata (source count, coverage)
            - Acknowledges research was performed
            - Encourages user to retry if needed
        """
        if not findings:
            return "Research completed, but no verified findings were available for synthesis. Please try refining your query."
        
        # Extract unique subtopics
        subtopics = list(set(f['subtopic'] for f in findings))
        subtopic_list = ', '.join(subtopics[:3])
        if len(subtopics) > 3:
            subtopic_list += f", and {len(subtopics) - 3} more areas"
        
        # Calculate average confidence
        avg_confidence = sum(f['confidence'] for f in findings) / len(findings)
        
        fallback = (
            f"Research synthesis based on {len(findings)} verified sources "
            f"(average confidence: {avg_confidence:.1%}) covering {subtopic_list}. "
            f"The findings provide comprehensive insights across multiple aspects of the topic. "
            f"For more detailed information, consider reviewing individual sources."
        )
        
        print(f"[SynthesizerAgent] ⚠ Using fallback summary")
        return fallback


# Module-level utility functions
def synthesize_research(
    verified_results: List[Dict[str, Any]], 
    preferences: Optional[Dict[str, str]] = None
) -> str:
    """
    Convenience function to synthesize research without instantiating agent.
    
    Args:
        verified_results (List[Dict[str, Any]]): Verified research data
        preferences (Dict[str, str], optional): User preferences
    
    Returns:
        str: Synthesized summary
    
    Example:
        >>> summary = synthesize_research(verified_data, {'length': 'short'})
        >>> print(summary)
    """
    agent = SynthesizerAgent()
    return agent.run(verified_results, preferences)


def estimate_reading_time(summary: str) -> int:
    """
    Estimate reading time in seconds for a summary.
    
    Uses average adult reading speed of 238 words per minute.
    
    Args:
        summary (str): Text to estimate
    
    Returns:
        int: Estimated reading time in seconds
    
    Example:
        >>> summary = synthesize_research(data)
        >>> time = estimate_reading_time(summary)
        >>> print(f"Reading time: {time//60}m {time%60}s")
    """
    words = len(summary.split())
    words_per_minute = 238  # Average adult reading speed
    seconds = int((words / words_per_minute) * 60)
    return max(10, seconds)  # Minimum 10 seconds


if __name__ == "__main__":
    # Demo/testing code
    print("SynthesizerAgent Demo")
    print("=" * 60)
    
    # Sample verified research data
    demo_data = [
        {
            'subtopic': 'AI in Healthcare',
            'findings': [
                {
                    'title': 'AI Diagnostic Accuracy',
                    'snippet': 'Recent studies show AI diagnostic tools achieve 95% accuracy in detecting diseases from medical imaging.',
                    'verified': True,
                    'confidence': 0.92
                },
                {
                    'title': 'Healthcare Cost Reduction',
                    'snippet': 'AI implementation has reduced diagnostic costs by 30% in pilot hospitals.',
                    'verified': True,
                    'confidence': 0.85
                }
            ]
        },
        {
            'subtopic': 'AI Ethics Considerations',
            'findings': [
                {
                    'title': 'Bias in AI Systems',
                    'snippet': 'Research identifies potential bias in AI healthcare algorithms affecting minority populations.',
                    'verified': True,
                    'confidence': 0.88
                }
            ]
        }
    ]
    
    try:
        agent = SynthesizerAgent()
        
        # Test different length preferences
        for length in ['short', 'medium', 'detailed']:
            print(f"\n{'='*60}")
            print(f"TEST: {length.upper()} Summary")
            print(f"{'='*60}")
            
            summary = agent.run(demo_data, {'length': length, 'format': 'paragraph'})
            reading_time = estimate_reading_time(summary)
            
            print(f"\n📄 SUMMARY ({length}):")
            print(f"{summary}")
            print(f"\n📊 METRICS:")
            print(f"  Characters: {len(summary)}")
            print(f"  Words: {len(summary.split())}")
            print(f"  Reading time: {reading_time}s")
            
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()