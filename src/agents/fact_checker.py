class FactCheckerAgent:
    def __init__(self):
        pass

    def run(self, research_results):
        print("[FactChecker] received:", research_results)
        return {"checked": research_results}
