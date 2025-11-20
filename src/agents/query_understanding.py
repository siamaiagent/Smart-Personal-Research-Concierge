import json
import re

class QueryUnderstandingAgent:
    def __init__(self, llm_client, prompts_path="prompt/query_understanding.txt"):
        self.llm = llm_client
        self.prompts_path = prompts_path
        self.session_memory = {}

    def _load_prompt(self):
        with open(self.prompts_path, "r", encoding="utf-8") as f:
            return f.read()

    def _extract_json_array(self, text: str):
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return ["general context", "implementation", "examples"]

    def run(self, query: str):
        prompt_template = self._load_prompt()
        prompt = prompt_template.format(query=query)

        raw = self.llm.call(prompt)

        topics = self._extract_json_array(raw)

        # Detect short/tweet preference
        q_lower = query.lower()
        if "short" in q_lower or "tweet" in q_lower:
            self.session_memory["output_preference"] = "short"

        self.session_memory["last_query"] = query
        self.session_memory["last_subtopics"] = topics

        return topics
