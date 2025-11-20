from src.llm_client import LLMClient
from src.agents.query_understanding import QueryUnderstandingAgent

def main():
    llm = LLMClient()
    agent = QueryUnderstandingAgent(llm)

    queries = [
        "How can I automate LinkedIn lead capture using n8n?",
        "Write a short tweet thread about AI agents.",
        "Market size of automation tools in 2025."
    ]

    for q in queries:
        print("\n=== Query ===")
        print(q)
        out = agent.run(q)
        print("Subtopics:", out)
        print("Session memory:", agent.session_memory)

if __name__ == "__main__":
    main()
