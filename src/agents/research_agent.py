from tools.google_search_tool import GoogleSearchTool
from tools.custom_scraper import CustomScraper
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

class ResearchAgent:
    """
    Agent that conducts research on multiple subtopics.
    Can run searches in parallel and optionally scrape content for deeper analysis.
    """
    
    def __init__(self, parallel=True, use_scraper=False):
        self.search_tool = GoogleSearchTool()
        self.scraper = CustomScraper() if use_scraper else None
        self.parallel = parallel
        self.use_scraper = use_scraper
    
    def run(self, subtopics):
        """
        Research all subtopics and return findings.
        
        Args:
            subtopics: List of subtopic strings
            
        Returns:
            List of dicts with subtopic and findings
        """
        print(f"\n[ResearchAgent] Starting research on {len(subtopics)} subtopics")
        if self.use_scraper:
            print(f"[ResearchAgent] Web scraping enabled for content enrichment")
        
        start_time = time.time()
        
        if self.parallel and len(subtopics) > 1:
            results = self._parallel_research(subtopics)
        else:
            results = self._sequential_research(subtopics)
        
        elapsed = time.time() - start_time
        print(f"[ResearchAgent] Completed research in {elapsed:.2f}s")
        
        return results
    
    def _parallel_research(self, subtopics):
        """Research multiple subtopics in parallel"""
        results = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all research tasks
            future_to_subtopic = {
                executor.submit(self._research_subtopic, subtopic): subtopic 
                for subtopic in subtopics
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_subtopic):
                subtopic = future_to_subtopic[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"[ResearchAgent] Error researching '{subtopic}': {e}")
                    results.append({
                        'subtopic': subtopic,
                        'findings': [],
                        'error': str(e)
                    })
        
        return results
    
    def _sequential_research(self, subtopics):
        """Research subtopics one by one"""
        results = []
        
        for subtopic in subtopics:
            result = self._research_subtopic(subtopic)
            results.append(result)
        
        return results
    
    def _research_subtopic(self, subtopic):
        """Research a single subtopic"""
        print(f"[ResearchAgent] Researching: {subtopic}")
        
        # Step 1: Search for information
        findings = self.search_tool.search(subtopic, num_results=3)
        
        # Step 2: Optionally enrich with scraped content
        if self.use_scraper and findings:
            findings = self._enrich_with_scraping(findings)
        
        return {
            'subtopic': subtopic,
            'findings': findings
        }
    
    def _enrich_with_scraping(self, findings):
        """
        Enrich search findings by scraping actual content from URLs.
        This provides more detailed information for fact-checking.
        """
        enriched_findings = []
        
        for finding in findings:
            url = finding.get('url', '')
            
            # Only scrape if URL looks real (not example.com)
            if url and 'example.com' not in url:
                scraped_text = self.scraper.fetch_text(url)
                
                if scraped_text:
                    # Add scraped content to finding
                    finding['scraped_content'] = scraped_text[:1000]  # First 1000 chars
                    finding['content_enriched'] = True
                else:
                    finding['content_enriched'] = False
            else:
                finding['content_enriched'] = False
            
            enriched_findings.append(finding)
        
        return enriched_findings