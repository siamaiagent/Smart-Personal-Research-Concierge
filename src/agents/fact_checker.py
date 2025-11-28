"""
Fact Checker Agent Module

This module verifies research findings for credibility and removes duplicates using AI-powered analysis.
It serves as a quality control layer in the research pipeline, ensuring only reliable information proceeds.

Author: Google Hackathon Team
License: MIT
"""

import os
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


class FactCheckerAgent:
    """
    AI-powered verification system for research findings with duplicate detection.
    
    This agent acts as a quality control layer in the research pipeline, performing
    two critical functions:
    1. Deduplication: Removes redundant information based on title similarity
    2. Verification: Assesses credibility using AI analysis of content and sources
    
    The verification process evaluates findings across multiple dimensions:
    - Relevance to the research subtopic
    - Specificity and depth of information
    - Source reliability based on URL analysis
    - Overall confidence scoring (0.0 to 1.0 scale)
    
    Architecture:
        - Uses Google Gemini 2.0 Flash for rapid credibility assessment
        - Implements rate limiting to prevent API quota exhaustion
        - Applies threshold-based filtering (default: 0.6 confidence)
        - Preserves original finding metadata while adding verification scores
    
    Attributes:
        model (GenerativeModel): Configured Gemini model for credibility assessment
        CONFIDENCE_THRESHOLD (float): Minimum confidence for verified status
        DEFAULT_CONFIDENCE (float): Fallback confidence on assessment failure
    
    Example Usage:
        >>> agent = FactCheckerAgent()
        >>> research_data = [
        ...     {
        ...         'subtopic': 'AI Applications',
        ...         'findings': [
        ...             {'title': 'ML in Healthcare', 'snippet': '...', 'url': '...'},
        ...             {'title': 'ML in Healthcare', 'snippet': '...', 'url': '...'}  # Duplicate
        ...         ]
        ...     }
        ... ]
        >>> verified = agent.run(research_data)
        >>> high_quality = [f for f in verified[0]['findings'] if f['confidence'] > 0.8]
    
    Dependencies:
        - google-generativeai: Gemini API for credibility assessment
        - python-dotenv: Environment variable management
        - Custom rate_limiter: API throttling and retry logic
    """
    
    # Configuration constants
    MODEL_NAME = "gemini-2.0-flash"
    CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for 'verified' status
    DEFAULT_CONFIDENCE = 0.7    # Fallback when assessment fails
    
    def __init__(self):
        """
        Initialize the FactCheckerAgent with Gemini API configuration.
        
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
        
        print(f"[FactCheckerAgent] Initialized with model: {self.MODEL_NAME}")
        print(f"[FactCheckerAgent] Confidence threshold: {self.CONFIDENCE_THRESHOLD}")
    
    def run(self, research_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute complete fact-checking pipeline: deduplication + verification.
        
        This is the main entry point that orchestrates the two-phase verification process:
        Phase 1: Remove duplicate findings based on title similarity
        Phase 2: Assess credibility of each unique finding using AI
        
        Args:
            research_results (List[Dict[str, Any]]): Research data from ResearchAgent.
                Expected structure:
                [
                    {
                        'subtopic': str,
                        'findings': [
                            {
                                'title': str,
                                'snippet': str,
                                'url': str
                            },
                            ...
                        ]
                    },
                    ...
                ]
        
        Returns:
            List[Dict[str, Any]]: Verified results with added verification metadata.
                Structure:
                [
                    {
                        'subtopic': str,
                        'findings': [
                            {
                                'title': str,
                                'snippet': str,
                                'url': str,
                                'verified': bool,      # True if confidence > threshold
                                'confidence': float    # Score 0.0-1.0
                            },
                            ...
                        ]
                    },
                    ...
                ]
        
        Example:
            >>> results = [{'subtopic': 'AI Ethics', 'findings': [...]}]
            >>> verified = agent.run(results)
            >>> verified_count = sum(
            ...     1 for r in verified 
            ...     for f in r['findings'] 
            ...     if f['verified']
            ... )
        """
        print(f"\n{'='*60}")
        print(f"[FactCheckerAgent] Starting fact-checking pipeline")
        print(f"{'='*60}")
        print(f"[FactCheckerAgent] Input: {len(research_results)} research result(s)")
        
        # Count total findings before processing
        total_findings = sum(
            len(result.get('findings', [])) 
            for result in research_results
        )
        print(f"[FactCheckerAgent] Total findings to process: {total_findings}")
        
        # Phase 1: Remove duplicates
        print(f"\n[FactCheckerAgent] Phase 1: Deduplication")
        deduplicated = self._remove_duplicates(research_results)
        
        unique_findings = sum(
            len(result.get('findings', [])) 
            for result in deduplicated
        )
        removed_count = total_findings - unique_findings
        print(f"[FactCheckerAgent] ✓ Removed {removed_count} duplicate(s)")
        print(f"[FactCheckerAgent] ✓ {unique_findings} unique finding(s) remain")
        
        # Phase 2: Verify each finding
        print(f"\n[FactCheckerAgent] Phase 2: Credibility Verification")
        verified_results = []
        verified_count = 0
        
        for idx, result in enumerate(deduplicated, 1):
            print(f"[FactCheckerAgent] Verifying subtopic {idx}/{len(deduplicated)}: '{result['subtopic']}'")
            verified = self._verify_result(result)
            verified_results.append(verified)
            
            # Count verified findings
            verified_count += sum(
                1 for f in verified['findings'] 
                if f.get('verified', False)
            )
        
        # Final summary
        print(f"\n[FactCheckerAgent] ✓ Verification complete:")
        print(f"  - Total findings: {unique_findings}")
        print(f"  - Verified (confidence > {self.CONFIDENCE_THRESHOLD}): {verified_count}")
        print(f"  - Unverified: {unique_findings - verified_count}")
        print(f"  - Success rate: {verified_count/unique_findings*100:.1f}%")
        print(f"{'='*60}\n")
        
        return verified_results
    
    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate findings based on title similarity.
        
        Uses case-insensitive title matching to identify duplicates. This simple
        but effective approach catches exact and near-exact duplicates that often
        occur when multiple sources report the same information.
        
        Args:
            results (List[Dict[str, Any]]): Research results with potential duplicates
        
        Returns:
            List[Dict[str, Any]]: Results with duplicates removed
        
        Implementation Notes:
            - Uses set-based tracking for O(1) duplicate detection
            - Preserves first occurrence of each unique finding
            - Maintains original structure of result dictionaries
            - Filters out results with no remaining findings
        
        Future Enhancements:
            - Fuzzy matching for near-duplicate detection
            - URL-based deduplication for same-source content
            - Semantic similarity using embeddings
        """
        seen_titles = set()
        unique_results = []
        
        for result in results:
            unique_findings = []
            
            for finding in result.get('findings', []):
                # Normalize title for comparison
                title_normalized = finding['title'].lower().strip()
                
                # Check if we've seen this title before
                if title_normalized not in seen_titles:
                    seen_titles.add(title_normalized)
                    unique_findings.append(finding)
            
            # Only include results that still have findings after deduplication
            if unique_findings:
                result_copy = result.copy()
                result_copy['findings'] = unique_findings
                unique_results.append(result_copy)
        
        return unique_results
    
    def _verify_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify all findings within a single research result.
        
        Iterates through each finding in the result and assesses its credibility
        using AI-powered analysis. Adds verification metadata to each finding.
        
        Args:
            result (Dict[str, Any]): Single research result containing:
                - subtopic: Research area context
                - findings: List of findings to verify
        
        Returns:
            Dict[str, Any]: Result with verified findings containing:
                - Original fields (title, snippet, url)
                - verified: Boolean (True if confidence > threshold)
                - confidence: Float score (0.0-1.0)
        
        Process:
            1. Extract subtopic for context
            2. Assess each finding's credibility
            3. Add verification metadata
            4. Return enhanced result structure
        """
        subtopic = result['subtopic']
        findings = result.get('findings', [])
        
        verified_findings = []
        
        for finding in findings:
            # Assess credibility using AI
            confidence = self._assess_credibility(subtopic, finding)
            
            # Determine verification status based on threshold
            is_verified = confidence > self.CONFIDENCE_THRESHOLD
            
            # Create enhanced finding with verification metadata
            verified_finding = {
                **finding,  # Preserve all original fields
                'verified': is_verified,
                'confidence': confidence
            }
            
            verified_findings.append(verified_finding)
        
        return {
            'subtopic': subtopic,
            'findings': verified_findings
        }
    
    @retry_on_rate_limit(max_retries=2, backoff_factor=2)
    def _assess_credibility(
        self, 
        subtopic: str, 
        finding: Dict[str, Any]
    ) -> float:
        """
        Assess credibility of a single finding using AI-powered analysis.
        
        Uses Gemini to evaluate finding quality across multiple dimensions:
        - Relevance: How well does the finding relate to the subtopic?
        - Specificity: Does it provide concrete, actionable information?
        - Source Reliability: Is the URL from a trustworthy domain?
        
        The AI returns a confidence score from 0.0 (not credible) to 1.0 (highly credible).
        
        Args:
            subtopic (str): Research area for context
            finding (Dict[str, Any]): Finding to assess with keys:
                - title: Finding headline
                - snippet: Content preview
                - url: Source URL
        
        Returns:
            float: Confidence score between 0.0 and 1.0
        
        Error Handling:
            - Rate limiting: Handled by decorator and rate_limiter
            - API failures: Returns DEFAULT_CONFIDENCE (0.7)
            - Invalid responses: Clamped to [0.0, 1.0] range
        
        Example:
            >>> finding = {
            ...     'title': 'AI in Healthcare Study',
            ...     'snippet': 'New research shows 95% accuracy...',
            ...     'url': 'https://nature.com/article'
            ... }
            >>> confidence = agent._assess_credibility('AI Applications', finding)
            >>> print(f"Confidence: {confidence:.2f}")
        """
        # Apply rate limiting before API call
        rate_limiter = get_rate_limiter()
        rate_limiter.wait_if_needed()
        
        # Construct credibility assessment prompt
        prompt = f"""You are a research quality assessor. Evaluate the credibility of this finding.

CONTEXT:
Research Subtopic: {subtopic}

FINDING TO ASSESS:
Title: {finding['title']}
Content: {finding['snippet']}
Source URL: {finding['url']}

EVALUATION CRITERIA:
1. Relevance (0.0-1.0): How directly does this finding relate to "{subtopic}"?
   - 1.0: Highly relevant, directly addresses subtopic
   - 0.5: Somewhat relevant, tangentially related
   - 0.0: Irrelevant, unrelated to subtopic

2. Specificity (0.0-1.0): Does it provide concrete, actionable information?
   - 1.0: Specific facts, data, or actionable insights
   - 0.5: General information with some details
   - 0.0: Vague, generic, or marketing content

3. Source Reliability (0.0-1.0): Based on the URL, is this a trustworthy source?
   - 1.0: Academic (.edu), government (.gov), reputable news/journals
   - 0.5: Professional blogs, industry sites, unknown domains
   - 0.0: Suspicious domains, known unreliable sources

INSTRUCTIONS:
Calculate an overall credibility score (0.0 to 1.0) weighing all three criteria.
Return ONLY the numerical score as a decimal number, nothing else.

Example valid responses: 0.85, 0.6, 0.92"""

        try:
            # Generate credibility assessment
            response = self.model.generate_content(prompt)
            confidence_str = response.text.strip()
            
            # Parse confidence score
            confidence = float(confidence_str)
            
            # Clamp to valid range [0.0, 1.0]
            confidence = max(0.0, min(1.0, confidence))
            
            return confidence
            
        except ValueError as e:
            # Failed to parse as float
            print(f"[FactCheckerAgent] ⚠ Invalid confidence format: {response.text[:50]}")
            print(f"[FactCheckerAgent] Using default confidence: {self.DEFAULT_CONFIDENCE}")
            return self.DEFAULT_CONFIDENCE
            
        except Exception as e:
            # API error or other failure
            print(f"[FactCheckerAgent] ⚠ Credibility assessment failed: {type(e).__name__}")
            print(f"[FactCheckerAgent] Using default confidence: {self.DEFAULT_CONFIDENCE}")
            return self.DEFAULT_CONFIDENCE


# Module-level utility functions
def verify_findings(
    research_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Convenience function to verify findings without instantiating agent.
    
    Args:
        research_results (List[Dict[str, Any]]): Research data to verify
    
    Returns:
        List[Dict[str, Any]]: Verified results with confidence scores
    
    Example:
        >>> results = [{'subtopic': 'AI', 'findings': [...]}]
        >>> verified = verify_findings(results)
        >>> high_conf = [f for r in verified for f in r['findings'] if f['confidence'] > 0.8]
    """
    agent = FactCheckerAgent()
    return agent.run(research_results)


def filter_by_confidence(
    verified_results: List[Dict[str, Any]], 
    min_confidence: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Filter verified results to only include high-confidence findings.
    
    Args:
        verified_results (List[Dict[str, Any]]): Results from FactCheckerAgent
        min_confidence (float): Minimum confidence threshold (default: 0.8)
    
    Returns:
        List[Dict[str, Any]]: Filtered results with only high-confidence findings
    
    Example:
        >>> verified = verify_findings(research_data)
        >>> high_quality = filter_by_confidence(verified, min_confidence=0.85)
    """
    filtered = []
    
    for result in verified_results:
        high_conf_findings = [
            f for f in result['findings'] 
            if f.get('confidence', 0.0) >= min_confidence
        ]
        
        if high_conf_findings:
            filtered.append({
                'subtopic': result['subtopic'],
                'findings': high_conf_findings
            })
    
    return filtered


if __name__ == "__main__":
    # Demo/testing code
    print("FactCheckerAgent Demo")
    print("=" * 60)
    
    # Sample research results with intentional duplicates
    demo_results = [
        {
            'subtopic': 'Machine Learning Applications',
            'findings': [
                {
                    'title': 'AI in Healthcare Diagnostics',
                    'snippet': 'Recent studies show 95% accuracy in detecting diseases using deep learning models.',
                    'url': 'https://nature.com/articles/ai-healthcare'
                },
                {
                    'title': 'AI in Healthcare Diagnostics',  # Duplicate
                    'snippet': 'ML models achieve high accuracy in medical imaging.',
                    'url': 'https://example.com/duplicate'
                },
                {
                    'title': 'Best AI Tools for Marketers',
                    'snippet': 'Top 10 AI tools that will revolutionize your marketing.',
                    'url': 'https://spam-site.com/listicle'
                }
            ]
        }
    ]
    
    try:
        # Run fact-checking
        verified = verify_findings(demo_results)
        
        # Display results
        print("\n📊 VERIFICATION RESULTS:")
        for result in verified:
            print(f"\n  Subtopic: {result['subtopic']}")
            print(f"  Findings: {len(result['findings'])}")
            
            for i, finding in enumerate(result['findings'], 1):
                status = "✓ VERIFIED" if finding['verified'] else "✗ UNVERIFIED"
                print(f"\n  {i}. {status} (confidence: {finding['confidence']:.2f})")
                print(f"     Title: {finding['title']}")
                print(f"     Source: {finding['url']}")
        
        # Show high-confidence findings only
        print("\n\n🎯 HIGH-CONFIDENCE FINDINGS (>0.8):")
        high_conf = filter_by_confidence(verified, min_confidence=0.8)
        for result in high_conf:
            for finding in result['findings']:
                print(f"  • {finding['title']} ({finding['confidence']:.2f})")
                
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()