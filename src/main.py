from agents.query_understanding import QueryUnderstandingAgent
from agents.research_agent import ResearchAgent
from agents.fact_checker import FactCheckerAgent
from agents.synthesizer import SynthesizerAgent
from agents.action_plan import ActionPlanAgent
from memory.session_memory import SessionMemory
from memory.long_term import LongTermMemory
import json

def main():
    """Complete pipeline demonstration with memory"""
    
    # Initialize memory systems
    session_memory = SessionMemory()
    long_term_memory = LongTermMemory()
    
    # Create new session
    session_id = session_memory.new_session()
    
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
    q_agent = QueryUnderstandingAgent()
    understanding = q_agent.run(query)
    subtopics = understanding['subtopics']
    preferences = understanding['preferences']
    
    # Store preferences in session memory
    session_memory.set(session_id, 'preferences', preferences)
    
    # Also save to long-term memory if user wants
    for key, value in preferences.items():
        long_term_memory.set_preference(f'default_{key}', value)
    
    print(f"\nSubtopics identified:")
    for i, subtopic in enumerate(subtopics, 1):
        print(f"  {i}. {subtopic}")
    
    # Step 2: Research
    print("\n" + "-"*80)
    print("STEP 2: Conducting Research")
    print("-"*80)
    USE_SCRAPER = False
    r_agent = ResearchAgent(parallel=True, use_scraper=USE_SCRAPER)
    research_results = r_agent.run(subtopics)
    
    # Store research results in session
    session_memory.set(session_id, 'research_results', research_results)
    
    # Step 3: Fact Checking
    print("\n" + "-"*80)
    print("STEP 3: Fact Checking")
    print("-"*80)
    f_agent = FactCheckerAgent()
    verified_results = f_agent.run(research_results)
    
    # Step 4: Synthesis
    print("\n" + "-"*80)
    print("STEP 4: Synthesizing Summary")
    print("-"*80)
    s_agent = SynthesizerAgent()
    
    # Retrieve preferences from session memory
    saved_preferences = session_memory.get(session_id, 'preferences', preferences)
    summary = s_agent.run(verified_results, saved_preferences)
    
    # Store summary in session
    session_memory.set(session_id, 'summary', summary)
    
    # Step 5: Action Plan
    print("\n" + "-"*80)
    print("STEP 5: Creating Action Plan")
    print("-"*80)
    a_agent = ActionPlanAgent()
    action_plan = a_agent.run(summary, query)
    
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

if __name__ == "__main__":
    main()