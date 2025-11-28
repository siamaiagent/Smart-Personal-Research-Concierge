"""
Smart Personal Research Concierge - Main Entry Point

This is the main orchestrator for the research pipeline, coordinating all agents
and managing the complete research workflow from query to actionable insights.

Author: Google Hackathon Team
License: MIT
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from observability import get_logger, ObservabilityLogger
from agents.query_understanding import QueryUnderstandingAgent
from agents.research_agent import ResearchAgent
from agents.fact_checker import FactCheckerAgent
from agents.synthesizer import SynthesizerAgent
from agents.action_plan import ActionPlanAgent
from memory.session_memory import SessionMemory
from memory.long_term import LongTermMemory
from long_running import LongRunningJobManager, simulate_deep_research
from utils.rate_limiter import get_rate_limiter
import config


class ResearchPipeline:
    """
    Complete research pipeline orchestrator.
    
    This class manages the entire research workflow, coordinating agents,
    memory systems, and observability tracking. It provides both synchronous
    and asynchronous execution modes with comprehensive error handling.
    
    Pipeline Stages:
        1. Query Understanding: Decompose query into subtopics
        2. Research: Gather information from multiple sources
        3. Fact Checking: Verify credibility of findings
        4. Synthesis: Create coherent summary
        5. Action Planning: Generate actionable steps
    
    Features:
        - Progress tracking with observability
        - Session and long-term memory integration
        - Configurable rate limiting
        - Error recovery and logging
        - Memory persistence
    
    Example:
        >>> pipeline = ResearchPipeline()
        >>> results = pipeline.run("What is quantum computing?")
        >>> print(results['summary'])
        >>> print(results['action_plan'])
    """
    
    def __init__(
        self,
        use_scraper: bool = False,
        parallel_research: bool = True,
        enable_fact_checking: bool = True
    ):
        """
        Initialize research pipeline with configuration.
        
        Args:
            use_scraper (bool): Enable web scraping for content enrichment
            parallel_research (bool): Enable parallel research execution
            enable_fact_checking (bool): Enable fact verification
        """
        # Initialize observability
        self.logger = get_logger()
        
        # Initialize memory systems
        self.session_memory = SessionMemory()
        self.long_term_memory = LongTermMemory()
        
        # Configuration
        self.use_scraper = use_scraper
        self.parallel_research = parallel_research
        self.enable_fact_checking = enable_fact_checking
        
        # Configure rate limiter
        self.rate_limiter = get_rate_limiter(
            requests_per_minute=config.RATE_LIMIT.requests_per_minute
        )
        
        logging.info("="*80)
        logging.info("ResearchPipeline initialized")
        logging.info(f"Configuration:")
        logging.info(f"  - Scraping: {self.use_scraper}")
        logging.info(f"  - Parallel: {self.parallel_research}")
        logging.info(f"  - Fact checking: {self.enable_fact_checking}")
        logging.info(f"  - Rate limit: {config.RATE_LIMIT.requests_per_minute} req/min")
        logging.info("="*80)
    
    def run(self, query: str, preferences: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute complete research pipeline.
        
        Args:
            query (str): Research query
            preferences (Dict[str, str], optional): User preferences for output
        
        Returns:
            Dict[str, Any]: Complete research results including:
                - summary: Synthesized research summary
                - action_plan: Actionable recommendations
                - subtopics: Research areas covered
                - session_id: Session identifier
                - verified_findings_count: Number of verified findings
        
        Example:
            >>> pipeline = ResearchPipeline()
            >>> results = pipeline.run("Impact of AI on healthcare")
            >>> print(f"Summary: {results['summary']}")
            >>> print(f"Actions: {len(results['action_plan']['checklist'])}")
        """
        # Create new session
        session_id = self.session_memory.new_session()
        self.logger.log_event("SESSION", f"New session created: {session_id}")
        
        # Save query to long-term memory
        self.long_term_memory.add_query(query)
        
        print("\n" + "="*80)
        print("🤖 SMART PERSONAL RESEARCH CONCIERGE")
        print("="*80)
        print(f"Session ID: {session_id}")
        print(f"Query: {query}")
        print("="*80 + "\n")
        
        try:
            # Execute pipeline stages
            understanding = self._stage_query_understanding(query, session_id)
            research_results = self._stage_research(understanding['subtopics'], session_id)
            
            if self.enable_fact_checking:
                verified_results = self._stage_fact_checking(research_results, session_id)
            else:
                verified_results = research_results
                print("\n⚠️  Fact checking disabled - using unverified results")
            
            # Merge preferences
            final_preferences = {**understanding['preferences'], **(preferences or {})}
            
            summary = self._stage_synthesis(verified_results, final_preferences, session_id)
            action_plan = self._stage_action_plan(summary, query, session_id)
            
            # Compile results
            results = {
                'summary': summary,
                'action_plan': action_plan,
                'subtopics': understanding['subtopics'],
                'session_id': session_id,
                'verified_findings_count': sum(len(r.get('findings', [])) for r in verified_results),
                'preferences': final_preferences
            }
            
            # Display results
            self._display_results(results)
            
            # Show memory status
            self._display_memory_status(session_id)
            
            # Save metrics and show summary
            self.logger.save_metrics()
            self.logger.print_summary()
            
            logging.info("✓ Pipeline completed successfully")
            
            return results
            
        except Exception as e:
            logging.error(f"✗ Pipeline failed: {type(e).__name__}: {e}")
            self.logger.log_event("ERROR", f"Pipeline failed: {e}")
            raise
    
    def _stage_query_understanding(self, query: str, session_id: str) -> Dict[str, Any]:
        """Execute query understanding stage."""
        self._print_stage_header(1, "Understanding Query")
        
        start_time = self.logger.start_timer("QueryUnderstandingAgent")
        
        try:
            agent = QueryUnderstandingAgent()
            understanding = agent.run(query)
            
            self.logger.end_timer("QueryUnderstandingAgent", start_time, success=True)
            
            # Store in session and long-term memory
            self.session_memory.set(session_id, 'understanding', understanding)
            
            for key, value in understanding['preferences'].items():
                self.long_term_memory.set_preference(f'default_{key}', value)
            
            # Display subtopics
            print(f"\n✓ Identified {len(understanding['subtopics'])} subtopic(s):")
            for i, subtopic in enumerate(understanding['subtopics'], 1):
                print(f"  {i}. {subtopic}")
            
            return understanding
            
        except Exception as e:
            self.logger.end_timer("QueryUnderstandingAgent", start_time, success=False, error=e)
            raise
    
    def _stage_research(self, subtopics: list, session_id: str) -> list:
        """Execute research stage."""
        self._print_stage_header(2, "Conducting Research")
        
        start_time = self.logger.start_timer("ResearchAgent")
        
        try:
            agent = ResearchAgent(
                parallel=self.parallel_research,
                use_scraper=self.use_scraper
            )
            research_results = agent.run(subtopics)
            
            self.logger.end_timer("ResearchAgent", start_time, success=True)
            
            # Store in session
            self.session_memory.set(session_id, 'research_results', research_results)
            
            total_findings = sum(len(r.get('findings', [])) for r in research_results)
            print(f"\n✓ Found {total_findings} total finding(s)")
            
            return research_results
            
        except Exception as e:
            self.logger.end_timer("ResearchAgent", start_time, success=False, error=e)
            raise
    
    def _stage_fact_checking(self, research_results: list, session_id: str) -> list:
        """Execute fact checking stage."""
        self._print_stage_header(3, "Fact Checking")
        
        start_time = self.logger.start_timer("FactCheckerAgent")
        
        try:
            agent = FactCheckerAgent()
            verified_results = agent.run(research_results)
            
            self.logger.end_timer("FactCheckerAgent", start_time, success=True)
            
            # Store in session
            self.session_memory.set(session_id, 'verified_results', verified_results)
            
            verified_count = sum(
                1 for r in verified_results 
                for f in r.get('findings', []) 
                if f.get('verified', False)
            )
            total_count = sum(len(r.get('findings', [])) for r in verified_results)
            
            print(f"\n✓ Verified {verified_count}/{total_count} finding(s)")
            
            return verified_results
            
        except Exception as e:
            self.logger.end_timer("FactCheckerAgent", start_time, success=False, error=e)
            raise
    
    def _stage_synthesis(
        self, 
        verified_results: list, 
        preferences: dict, 
        session_id: str
    ) -> str:
        """Execute synthesis stage."""
        self._print_stage_header(4, "Synthesizing Summary")
        
        start_time = self.logger.start_timer("SynthesizerAgent")
        
        try:
            agent = SynthesizerAgent()
            summary = agent.run(verified_results, preferences)
            
            self.logger.end_timer("SynthesizerAgent", start_time, success=True)
            
            # Store in session
            self.session_memory.set(session_id, 'summary', summary)
            
            print(f"\n✓ Generated summary ({len(summary)} characters)")
            
            return summary
            
        except Exception as e:
            self.logger.end_timer("SynthesizerAgent", start_time, success=False, error=e)
            raise
    
    def _stage_action_plan(self, summary: str, query: str, session_id: str) -> dict:
        """Execute action planning stage."""
        self._print_stage_header(5, "Creating Action Plan")
        
        start_time = self.logger.start_timer("ActionPlanAgent")
        
        try:
            agent = ActionPlanAgent()
            action_plan = agent.run(summary, query)
            
            self.logger.end_timer("ActionPlanAgent", start_time, success=True)
            
            # Store in session
            self.session_memory.set(session_id, 'action_plan', action_plan)
            
            print(f"\n✓ Created action plan:")
            print(f"  - {len(action_plan['checklist'])} checklist items")
            print(f"  - {len(action_plan['quick_start'])} quick-start steps")
            
            return action_plan
            
        except Exception as e:
            self.logger.end_timer("ActionPlanAgent", start_time, success=False, error=e)
            raise
    
    def _print_stage_header(self, stage_num: int, stage_name: str) -> None:
        """Print formatted stage header."""
        print("\n" + "─"*80)
        print(f"STAGE {stage_num}/5: {stage_name}")
        print("─"*80)
    
    def _display_results(self, results: Dict[str, Any]) -> None:
        """Display final results in formatted output."""
        print("\n" + "="*80)
        print("📊 FINAL RESULTS")
        print("="*80)
        
        print("\n📝 SUMMARY:")
        print("─"*80)
        print(results['summary'])
        
        print("\n\n✅ ACTION CHECKLIST:")
        print("─"*80)
        for i, item in enumerate(results['action_plan']['checklist'], 1):
            print(f"  {i}. {item}")
        
        print("\n\n🚀 QUICK START (3 Steps):")
        print("─"*80)
        for step in results['action_plan']['quick_start']:
            print(f"  • {step}")
        
        print("\n" + "="*80)
        print("✨ Research Complete!")
        print("="*80)
    
    def _display_memory_status(self, session_id: str) -> None:
        """Display memory system status."""
        print("\n" + "="*80)
        print("💾 MEMORY STATUS")
        print("="*80)
        
        session_data = self.session_memory.get_all(session_id)
        query_history = self.long_term_memory.get_query_history()
        preferences = self.long_term_memory.get_all_preferences()
        
        print(f"  • Session data: {len(session_data)} item(s)")
        print(f"  • Query history: {len(query_history)} recent quer(y/ies)")
        print(f"  • Saved preferences: {len(preferences)} preference(s)")
        
        if preferences:
            print(f"\n  Preferences:")
            for key, value in list(preferences.items())[:3]:  # Show first 3
                print(f"    - {key}: {value}")
            if len(preferences) > 3:
                print(f"    ... and {len(preferences) - 3} more")


def main():
    """
    Main entry point for the research pipeline.
    
    Executes a complete research workflow with a sample query,
    demonstrating all pipeline stages and features.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize pipeline
    pipeline = ResearchPipeline(
        use_scraper=config.RESEARCH.enable_scraping,
        parallel_research=config.RESEARCH.parallel_research,
        enable_fact_checking=config.RESEARCH.enable_fact_checking
    )
    
    # Sample query
    query = "What's the impact of AI automation on small businesses?"
    
    # Execute research
    results = pipeline.run(query)
    
    # Results are automatically displayed and stored
    logging.info(f"Session ID: {results['session_id']}")
    logging.info(f"Verified findings: {results['verified_findings_count']}")


def demo_long_running_operations():
    """
    Demonstrate long-running operations with pause/resume capability.
    
    This shows how the system handles operations that take minutes to complete,
    with full state persistence across program restarts.
    
    Features:
        - Job creation and tracking
        - Progress monitoring
        - Pause/resume capability
        - Status checking
    """
    print("\n" + "="*80)
    print("🔄 LONG-RUNNING OPERATIONS DEMO")
    print("="*80)
    
    job_manager = LongRunningJobManager()
    
    # Start a deep research job
    query = "Deep research: AI impact on healthcare in 2024-2025"
    job_id = job_manager.start_deep_research(
        query,
        config={
            'depth': 'comprehensive',
            'parallel': True,
            'enable_scraping': True
        }
    )
    
    print(f"\n✅ Started long-running job")
    print(f"  • Job ID: {job_id}")
    print(f"  • Query: {query}")
    
    # Check initial status
    status = job_manager.check_status(job_id)
    print(f"\n📊 Job Status:")
    print(f"  • Status: {status['status']}")
    print(f"  • Progress: {status['progress']}%")
    
    # Provide resume instructions
    print(f"\n💡 Job Management Commands:")
    print(f"\n  Resume job:")
    print(f"    python -c \"from src.long_running import LongRunningJobManager; "
          f"mgr = LongRunningJobManager(); mgr.resume_job('{job_id}')\"")
    
    print(f"\n  Check status:")
    print(f"    python -c \"from src.long_running import LongRunningJobManager; "
          f"print(LongRunningJobManager().check_status('{job_id}'))\"")
    
    print(f"\n  List all jobs:")
    print(f"    python -c \"from src.long_running import LongRunningJobManager; "
          f"import json; print(json.dumps(LongRunningJobManager().list_jobs(), indent=2))\"")
    
    # Show statistics
    stats = job_manager.get_statistics()
    print(f"\n📈 Job Statistics:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    print("\n" + "="*80)


def demo_configuration():
    """
    Display current configuration settings.
    
    Shows all active configuration values and provides guidance
    on customization via environment variables.
    """
    print("\n" + "="*80)
    print("⚙️  CONFIGURATION DEMO")
    print("="*80)
    
    # Print configuration summary
    config.print_config_summary()
    
    # Show environment override examples
    print("\n💡 Environment Variable Overrides:")
    print("="*80)
    print("\nExample usage:")
    print("  export GEMINI_MODEL='gemini-pro'")
    print("  export RATE_LIMIT_RPM='20'")
    print("  export LOG_LEVEL='DEBUG'")
    print("  export ENABLE_SCRAPING='true'")
    print("\nThen run:")
    print("  python src/main.py")
    print("\n" + "="*80)


def demo_interactive():
    """
    Interactive mode for user queries.
    
    Allows users to input custom queries and see the complete
    research pipeline in action.
    """
    print("\n" + "="*80)
    print("💬 INTERACTIVE RESEARCH MODE")
    print("="*80)
    print("\nEnter your research query (or 'quit' to exit):\n")
    
    pipeline = ResearchPipeline(
        use_scraper=config.RESEARCH.enable_scraping,
        parallel_research=config.RESEARCH.parallel_research,
        enable_fact_checking=config.RESEARCH.enable_fact_checking
    )
    
    while True:
        try:
            query = input("\n🔍 Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not query:
                print("⚠️  Please enter a query")
                continue
            
            # Execute research
            results = pipeline.run(query)
            
            # Ask if user wants to continue
            continue_prompt = input("\n\nContinue with another query? (y/n): ").strip().lower()
            if continue_prompt != 'y':
                print("\n👋 Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logging.exception("Error in interactive mode")


if __name__ == "__main__":
    """
    Main entry point with command-line argument handling.
    
    Usage:
        python src/main.py                    # Run default demo
        python src/main.py --long-running     # Demo job management
        python src/main.py --config           # Show configuration
        python src/main.py --interactive      # Interactive mode
    """
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--long-running', '--long-running-demo', '-l']:
            demo_long_running_operations()
        elif arg in ['--config', '--configuration', '-c']:
            demo_configuration()
        elif arg in ['--interactive', '--interactive-mode', '-i']:
            demo_interactive()
        else:
            print(f"Unknown argument: {arg}")
            print("\nUsage:")
            print("  python src/main.py                # Default demo")
            print("  python src/main.py --long-running # Job management demo")
            print("  python src/main.py --config       # Show configuration")
            print("  python src/main.py --interactive  # Interactive mode")
            sys.exit(1)
    else:
        # Run default demo
        main()