from agents.query_understanding import QueryUnderstandingAgent
from agents.research_agent import ResearchAgent
from agents.fact_checker import FactCheckerAgent
from agents.synthesizer import SynthesizerAgent
from agents.action_plan import ActionPlanAgent

def main():
    query = "What's the impact of AI automation on small agencies?"

    # create agent instances
    q_agent = QueryUnderstandingAgent()
    r_agent = ResearchAgent()
    f_agent = FactCheckerAgent()
    s_agent = SynthesizerAgent()
    a_agent = ActionPlanAgent()

    # pipeline
    subtopics = q_agent.run(query)
    research_results = r_agent.run(subtopics)
    checked = f_agent.run(research_results)
    summary = s_agent.run(checked)
    actions = a_agent.run(summary)

    print("SUMMARY:\n", summary)
    print("ACTIONS:\n", actions)

if __name__ == "__main__":
    main()
