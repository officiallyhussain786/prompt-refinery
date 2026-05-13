import os
import requests
from typing import Optional


class Retriever:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("HF_TOKEN environment variable is not set")
        self.endpoint = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
        self.patterns = []
        self.mode_patterns = {}
        self.embeddings = []
        self._initialize()

    def _get_embedding(self, text: str) -> list:
        """Get embedding from HuggingFace Inference API."""
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.hf_token}"},
            json={"inputs": text}
        )
        response.raise_for_status()
        return response.json()

    def _initialize(self):
        """Initialize patterns with HuggingFace embeddings."""
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

        # Flatten patterns for indexing
        all_patterns = []
        for mode, pattern_list in self.mode_patterns.items():
            for pattern in pattern_list:
                all_patterns.append({
                    "text": pattern,
                    "mode": mode,
                    "category": self._categorize(pattern)
                })

        self.patterns = all_patterns

        # Get embeddings for all patterns
        texts = [p["text"] for p in self.patterns]
        for text in texts:
            embedding = self._get_embedding(text)
            self.embeddings.append(embedding)

    def _categorize(self, text: str) -> str:
        """Categorize pattern by its focus area."""
        text_lower = text.lower()
        if "context" in text_lower or "domain" in text_lower:
            return "context"
        elif "format" in text_lower or "structure" in text_lower:
            return "format"
        elif "example" in text_lower:
            return "example"
        elif "audience" in text_lower:
            return "audience"
        elif "step" in text_lower or "phase" in text_lower:
            return "process"
        elif "constraint" in text_lower or "limit" in text_lower:
            return "constraint"
        return "general"

    def _cosine_similarity(self, a: list, b: list) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0

    def search(self, query: str, mode: str = "detailed", top_k: int = 5) -> list:
        """Search for relevant patterns based on query and mode.

        Args:
            query: The user's original prompt
            mode: Refinement mode (detailed, concise, structured, multi_step)
            top_k: Number of patterns to retrieve

        Returns:
            List of relevant pattern strings
        """
        if not self.embeddings:
            return self.mode_patterns.get(mode, self.mode_patterns["detailed"])

        # Get query embedding
        try:
            query_embedding = self._get_embedding(query)
        except Exception:
            return self.mode_patterns.get(mode, self.mode_patterns["detailed"])

        # Calculate similarities
        similarities = []
        for idx, embedding in enumerate(self.embeddings):
            sim = self._cosine_similarity(query_embedding, embedding)
            pattern = self.patterns[idx]
            similarities.append((idx, sim, pattern))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get matching patterns, filtering by mode
        results = []
        for idx, sim, pattern in similarities:
            if pattern["mode"] == mode:
                results.append(pattern["text"])

        # If no mode-matched results, return top matches
        if len(results) < 3:
            for idx, sim, pattern in similarities[:3]:
                text = pattern["text"]
                if text not in results:
                    results.append(text)

        return results[:top_k]


# Singleton instance
_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """Get or create the Retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever