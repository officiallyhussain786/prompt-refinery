import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


class Retriever:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None
        self.patterns = []
        self.mode_patterns = {}
        self._initialize()

    def _initialize(self):
        """Initialize FAISS index with prompt engineering patterns."""
        # Patterns organized by refinement mode
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

        # Create embeddings and build FAISS index
        texts = [p["text"] for p in self.patterns]
        embeddings = self.model.encode(texts, show_progress_bar=False)

        # Build FAISS index (dimension = embedding size)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))

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

    def search(self, query: str, mode: str = "detailed", top_k: int = 5) -> list:
        """Search for relevant patterns based on query and mode.

        Args:
            query: The user's original prompt
            mode: Refinement mode (detailed, concise, structured, multi_step)
            top_k: Number of patterns to retrieve

        Returns:
            List of relevant pattern strings
        """
        if self.index is None:
            return self.mode_patterns.get(mode, self.mode_patterns["detailed"])

        # Encode the query
        query_embedding = self.model.encode([query])

        # Search FAISS index
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'),
            min(top_k, len(self.patterns))
        )

        # Get matching patterns, filtering by mode
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.patterns):
                pattern = self.patterns[idx]
                # Boost relevance for matching mode
                if pattern["mode"] == mode:
                    results.append(pattern["text"])

        # If no mode-matched results, return top matches
        if len(results) < 3:
            for idx in indices[0][:3]:
                if idx < len(self.patterns):
                    text = self.patterns[idx]["text"]
                    if text not in results:
                        results.append(text)

        return results[:top_k]


# Singleton instance
_retriever = None

def get_retriever() -> Retriever:
    """Get or create the Retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever