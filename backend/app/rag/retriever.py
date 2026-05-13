import os
from typing import Optional


class Retriever:
    def __init__(self):
        self.mode_patterns = {
            "detailed": [
                "Add specific context about your domain or industry",
                "Specify the format you want the output in (bullets, paragraph, code)",
                "Include examples of the desired output",
                "Define the target audience for the response",
                "Specify any constraints or limitations",
            ],
            "concise": [
                "Get to the point immediately, avoid preamble",
                "Remove unnecessary background information",
                "State constraints and requirements upfront",
                "Focus on the core action or information needed",
            ],
            "structured": [
                "Use bullet points to list requirements",
                "Ask for step-by-step or numbered responses",
                "Request specific output format or structure",
                "Organize information in clear sections",
            ],
            "multi_step": [
                "Break the task into clear phases or steps",
                "Ask for intermediate checkpoints or confirmations",
                "Request explanation between each step",
                "Define success criteria for each phase",
            ],
        }

    def search(self, query: str, mode: str = "detailed", top_k: int = 5) -> list:
        """Return patterns based on mode (no embeddings needed)."""
        patterns = self.mode_patterns.get(mode, self.mode_patterns["detailed"])
        return patterns[:top_k]


# Singleton instance
_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """Get or create the Retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever