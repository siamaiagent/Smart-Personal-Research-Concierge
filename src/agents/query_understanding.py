class QueryUnderstandingAgent:
    def __init__(self):
        pass

    def run(self, query: str):
        print("[QueryAgent] received:", query)
        return ["market impact", "tools", "case studies"]
