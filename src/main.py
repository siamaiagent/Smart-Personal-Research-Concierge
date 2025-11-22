from observability import get_logger
import logging
from agents.query_understanding import QueryUnderstandingAgent
from agents.research_agent import ResearchAgent
from agents.fact_checker import FactCheckerAgent
from agents.synthesizer import SynthesizerAgent
from agents.action_plan import ActionPlanAgent
from memory.session_memory import SessionMemory
from memory.long_term import LongTermMemory
import json

def main():
    """Complete pipeline demonstration with memory and observability"""
    
    # Initialize observability
    obs_logger = get_logger()
    logging.info("="*80)
    logging.info("Starting Smart Personal Research Concierge")
    logging.info("="*80)
    
    # Initialize memory systems
    session_memory = SessionMemory()
    long_term_memory = LongTermMemory()
    
    # Create new session
    session_id = session_memory.new_session()
    obs_logger.log_event("SESSION", f"New session created: {session_id}")
    
    # Sample query
    query = "What's the impact of AI automation on small businesses?"
    
    # Save query to long-term memory
    long_term_memory.add_query(query)
    
    print("="*80)
    print("🤖 SMART PERSONAL RESEARCH CONCIERGE")
    print("="*80)
    print(f"Session ID: {session_id}")
    print(f"Query: {query}\n")
    
    # Step 1: Query Understanding
    print("\n" + "-"*80)
    print("STEP 1: Understanding Query")
    print("-"*80)
    
    start_time = obs_logger.start_timer("QueryUnderstandingAgent")
    try:
        q_agent = QueryUnderstandingAgent()
        understanding = q_agent.run(query)
        subtopics = understanding['subtopics']
        preferences = understanding['preferences']
        obs_logger.end_timer("QueryUnderstandingAgent", start_time, success=True)
    except Exception as e:
        obs_logger.end_timer("QueryUnderstandingAgent", start_time, success=False, error=e)
        raise
    
    # Store preferences in session memory
    session_memory.set(session_id, 'preferences', preferences)
    
    # Also save to long-term memory
    for key, value in preferences.items():
        long_term_memory.set_preference(f'default_{key}', value)
    
    print(f"\nSubtopics identified:")
    for i, subtopic in enumerate(subtopics, 1):
        print(f"  {i}. {subtopic}")
    
    # Step 2: Research
    print("\n" + "-"*80)
    print("STEP 2: Conducting Research")
    print("-"*80)
    
    start_time = obs_logger.start_timer("ResearchAgent")
    try:
        USE_SCRAPER = False
        r_agent = ResearchAgent(parallel=True, use_scraper=USE_SCRAPER)
        research_results = r_agent.run(subtopics)
        obs_logger.end_timer("ResearchAgent", start_time, success=True)
    except Exception as e:
        obs_logger.end_timer("ResearchAgent", start_time, success=False, error=e)
        raise
    
    # Store research results in session
    session_memory.set(session_id, 'research_results', research_results)
    
    # Step 3: Fact Checking
    print("\n" + "-"*80)
    print("STEP 3: Fact Checking")
    print("-"*80)
    
    start_time = obs_logger.start_timer("FactCheckerAgent")
    try:
        f_agent = FactCheckerAgent()
        verified_results = f_agent.run(research_results)
        obs_logger.end_timer("FactCheckerAgent", start_time, success=True)
    except Exception as e:
        obs_logger.end_timer("FactCheckerAgent", start_time, success=False, error=e)
        raise
    
    # Step 4: Synthesis
    print("\n" + "-"*80)
    print("STEP 4: Synthesizing Summary")
    print("-"*80)
    
    start_time = obs_logger.start_timer("SynthesizerAgent")
    try:
        s_agent = SynthesizerAgent()
        saved_preferences = session_memory.get(session_id, 'preferences', preferences)
        summary = s_agent.run(verified_results, saved_preferences)
        obs_logger.end_timer("SynthesizerAgent", start_time, success=True)
    except Exception as e:
        obs_logger.end_timer("SynthesizerAgent", start_time, success=False, error=e)
        raise
    
    # Store summary in session
    session_memory.set(session_id, 'summary', summary)
    
    # Step 5: Action Plan
    print("\n" + "-"*80)
    print("STEP 5: Creating Action Plan")
    print("-"*80)
    
    start_time = obs_logger.start_timer("ActionPlanAgent")
    try:
        a_agent = ActionPlanAgent()
        action_plan = a_agent.run(summary, query)
        obs_logger.end_timer("ActionPlanAgent", start_time, success=True)
    except Exception as e:
        obs_logger.end_timer("ActionPlanAgent", start_time, success=False, error=e)
        raise
    
    # Store action plan in session
    session_memory.set(session_id, 'action_plan', action_plan)
    
    # Final Output
    print("\n" + "="*80)
    print("📊 FINAL RESULTS")
    print("="*80)
    
    print("\n📝 SUMMARY:")
    print("-"*80)
    print(summary)
    
    print("\n\n✅ ACTION CHECKLIST:")
    print("-"*80)
    for i, item in enumerate(action_plan['checklist'], 1):
        print(f"{i}. {item}")
    
    print("\n\n🚀 QUICK START (3 Steps):")
    print("-"*80)
    for step in action_plan['quick_start']:
        print(f"  • {step}")
    
    print("\n" + "="*80)
    print("✨ Research Complete!")
    print("="*80)
    
    # Show memory stats
    print("\n" + "="*80)
    print("💾 MEMORY STATUS")
    print("="*80)
    print(f"Session data stored: {len(session_memory.get_all(session_id))} items")
    print(f"Query history: {len(long_term_memory.get_query_history())} recent queries")
    print(f"Saved preferences: {long_term_memory.get_all_preferences()}")
    
    # Save metrics and show summary
    obs_logger.save_metrics()
    obs_logger.print_summary()
    
    logging.info("Pipeline completed successfully")

if __name__ == "__main__":
    main()