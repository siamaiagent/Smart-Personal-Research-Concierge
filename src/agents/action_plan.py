class ActionPlanAgent:
    def __init__(self):
        pass

    def run(self, summary):
        print("[ActionPlan] received:", summary)
        return ["Step 1", "Step 2", "Step 3"]
