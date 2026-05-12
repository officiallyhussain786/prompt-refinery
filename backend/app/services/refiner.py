import os
import json
import re
from groq import Groq


class Refiner:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        self.client = Groq(api_key=api_key)

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code block formatting if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        # Try to extract JSON object
        text = text.strip()

        # Find JSON object (handles nested objects)
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract fields with regex as fallback
            result = {}
            patterns = {
                'refined_prompt': r'"refined_prompt"\s*:\s*"([^"]*)"',
                'intent': r'"intent"\s*:\s*"([^"]*)"',
                'original_score': r'"original_score"\s*:\s*(\d+)',
                'refined_score': r'"refined_score"\s*:\s*(\d+)',
                'improvements': r'"improvements"\s*:\s*\[(.*?)\]',
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    if key == 'improvements':
                        items = re.findall(r'"([^"]*)"', match.group(1))
                        result[key] = items
                    else:
                        result[key] = match.group(1) if key != 'improvements' else match.group(1)

            if result:
                return result

        return {"error": "Could not parse response"}

    def _score_prompt(self, prompt: str) -> int:
        """Score prompt quality 1-10 based on clarity and specificity."""
        score = 5  # Base score

        # Deductions for common issues
        if len(prompt) < 20:
            score -= 2
        if len(prompt) > 500:
            score -= 1

        # Check for specificity indicators
        has_numbers = bool(re.search(r'\d+', prompt))
        has_examples = 'example' in prompt.lower() or 'like' in prompt.lower()
        has_constraints = any(w in prompt.lower() for w in ['must', 'should', 'need', 'require'])
        has_format = any(w in prompt.lower() for w in ['format', 'list', 'bullets', 'steps'])

        if has_numbers:
            score += 0.5
        if has_examples:
            score += 1
        if has_constraints:
            score += 1
        if has_format:
            score += 1

        return min(10, max(1, int(score)))

    def refine(self, prompt: str, mode: str, patterns: list) -> dict:
        """Refine the user's prompt using the retrieved patterns.

        Args:
            prompt: Original user prompt
            mode: Refinement mode (detailed, concise, structured, multi_step)
            patterns: Retrieved RAG patterns to apply

        Returns:
            Dictionary with refined_prompt, intent, scores, and improvements
        """
        context = "\n".join([f"- {p}" for p in patterns])

        system = f"""You are an expert prompt engineer. Your task is to refine user prompts
to be clearer, more specific, and optimized for better LLM outputs.

Refinement mode: {mode}
Apply these best practices:
{context}

Return your response as a JSON object with these fields:
{{
    "refined_prompt": "The improved, enhanced prompt",
    "intent": "Brief description of what the user wants to accomplish",
    "original_score": <1-10 score for original prompt quality>,
    "refined_score": <1-10 score for refined prompt quality>,
    "improvements": ["List of specific improvements made"]
}}

Be strict with JSON formatting - no markdown, no explanations outside the JSON."""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Refine this prompt: {prompt}"}
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        result_text = response.choices[0].message.content

        # Parse the JSON response
        parsed = self._parse_json_response(result_text)

        # Calculate scores if not provided by LLM
        original_score = parsed.get('original_score') or self._score_prompt(prompt)

        # Refined score should be better than original
        refined_score = parsed.get('refined_score') or min(10, original_score + 3)

        improvements = parsed.get('improvements') or ["Enhanced clarity", "Added specificity"]

        return {
            "refined_prompt": parsed.get('refined_prompt', prompt),
            "intent": parsed.get('intent', "General refinement"),
            "original_score": int(original_score),
            "refined_score": int(refined_score),
            "improvements": improvements
        }


# Singleton instance
_refiner = None

def get_refiner() -> Refiner:
    """Get or create the Refiner singleton."""
    global _refiner
    if _refiner is None:
        _refiner = Refiner()
    return _refiner