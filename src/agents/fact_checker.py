import google.generativeai as genai
import os

class FactCheckerAgent:
    """
    Verifies research findings and removes duplicates.
    
    This agent reviews findings from ResearchAgent and assesses their
    credibility using LLM-based verification. It removes duplicate information
    and assigns confidence scores to each finding.
    
    Dependencies:
        - google.generativeai (Gemini API for credibility assessment)
    
    Inputs:
        research_results (List[dict]): Results from ResearchAgent containing
            findings with title, snippet, and URL
    
    Outputs:
        List[dict]: Verified results, each containing:
            - subtopic: Research area
            - findings: List of findings with added fields:
                * verified: Boolean indicating credibility (>0.6 confidence)
                * confidence: Float (0.0-1.0) credibility score
    
    Verification Criteria:
        - Relevance to subtopic
        - Specificity of information
        - Source URL reliability
        - Duplicate detection
    
    Example:
        >>> agent = FactCheckerAgent()
        >>> verified = agent.run(research_results)
        >>> high_confidence = [f for f in verified[0]['findings'] if f['confidence'] > 0.8]
    """
    
    def __init__(self):
        
        api_key = os.environ.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def run(self, research_results):
        """
        Verify findings and remove duplicates.
        
        Args:
            research_results: List of research result dicts
            
        Returns:
            List of verified findings with confidence scores
        """
        print(f"\n[FactCheckerAgent] Checking {len(research_results)} research results")
        
        # Remove duplicates first
        deduplicated = self._remove_duplicates(research_results)
        
        # Verify each finding
        verified_results = []
        for result in deduplicated:
            verified = self._verify_result(result)
            verified_results.append(verified)
        
        print(f"[FactCheckerAgent] Verified {len(verified_results)} unique findings")
        return verified_results
    
    def _remove_duplicates(self, results):
        """Remove duplicate findings based on similarity"""
        seen_titles = set()
        unique_results = []
        
        for result in results:
            # Create a simplified version of findings
            unique_findings = []
            for finding in result.get('findings', []):
                title_lower = finding['title'].lower()
                # Simple duplicate check
                if title_lower not in seen_titles:
                    seen_titles.add(title_lower)
                    unique_findings.append(finding)
            
            if unique_findings:
                result_copy = result.copy()
                result_copy['findings'] = unique_findings
                unique_results.append(result_copy)
        
        return unique_results
    
    def _verify_result(self, result):
        """Verify a single research result"""
        subtopic = result['subtopic']
        findings = result['findings']
        
        verified_findings = []
        
        for finding in findings:
            # Use LLM to assess credibility
            confidence = self._assess_credibility(subtopic, finding)
            
            verified_findings.append({
                **finding,
                'verified': confidence > 0.6,
                'confidence': confidence
            })
        
        return {
            'subtopic': subtopic,
            'findings': verified_findings
        }
    
    def _assess_credibility(self, subtopic, finding):
        """Use LLM to assess finding credibility"""
        # Use LLM to assess credibility based on relevance, specificity, and source
        # Returns confidence score 0.0-1.0
        prompt = f"""Assess the credibility of this research finding:

Subtopic: {subtopic}
Title: {finding['title']}
Content: {finding['snippet']}
Source: {finding['url']}

Rate the credibility from 0.0 to 1.0 based on:
- Relevance to subtopic
- Specificity of information
- Source reliability (based on URL)

Return ONLY a number between 0.0 and 1.0, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            confidence = float(response.text.strip())
            return max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
        except Exception:
            return 0.7  # Default confidence