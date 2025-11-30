#!/usr/bin/env python3
"""
Gemini-based Semantic Similarity Evaluator
Uses Gemini API to evaluate methodology/reasoning similarity
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class GeminiSimilarityEvaluator:
    """Evaluates semantic similarity between expected and generated calculation steps."""
    
    def __init__(self, api_key: Optional[str] = None):
        if genai is None:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=self.api_key)
        
        # Try different model names
        model_names = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
        self.model = None
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                print(f"  Gemini Evaluator using model: {model_name}")
                break
            except Exception:
                continue
        
        if self.model is None:
            raise ValueError("Could not initialize any Gemini model")
        
        # Load evaluation prompt template
        prompt_file = Path(__file__).parent.parent / "prompts" / "gemini_evaluation_prompt.txt"
        if prompt_file.exists():
            self.prompt_template = prompt_file.read_text()
        else:
            self.prompt_template = self._default_prompt_template()
    
    def _default_prompt_template(self) -> str:
        return """Evaluate how well the LLM's calculation steps match the expected steps.

Question: {question}

Expected Steps: {expected_steps}

LLM Generated Steps: {llm_steps}

Return JSON only:
{{"similarity_score": <0-100>, "matching_concepts": [], "missing_concepts": [], "reasoning": "brief explanation"}}"""
    
    def evaluate(self, question: str, expected_steps: List[str], 
                 llm_steps: str, max_retries: int = 3) -> Dict:
        """
        Evaluate similarity between expected and LLM-generated steps.
        
        Returns:
            Dict with similarity_score (0-100), matching_concepts, missing_concepts, reasoning
        """
        expected_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(expected_steps))
        
        prompt = self.prompt_template.format(
            question=question,
            expected_steps=expected_str,
            llm_steps=llm_steps
        )
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Parse JSON from response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                # Find JSON object in response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    response_text = response_text[json_start:json_end]
                
                result = json.loads(response_text)
                
                # Validate and normalize result
                return {
                    "similarity_score": min(100, max(0, float(result.get("similarity_score", 0)))),
                    "matching_concepts": result.get("matching_concepts", []),
                    "missing_concepts": result.get("missing_concepts", []),
                    "extra_concepts": result.get("extra_concepts", []),
                    "reasoning": result.get("reasoning", "")
                }
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return {
                    "similarity_score": 0,
                    "matching_concepts": [],
                    "missing_concepts": [],
                    "extra_concepts": [],
                    "reasoning": f"JSON parse error: {str(e)}",
                    "error": True
                }
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    "similarity_score": 0,
                    "matching_concepts": [],
                    "missing_concepts": [],
                    "extra_concepts": [],
                    "reasoning": f"API error: {error_msg}",
                    "error": True,
                    "is_quota_error": "quota" in error_msg.lower() or "429" in error_msg
                }
        
        return {
            "similarity_score": 0,
            "matching_concepts": [],
            "missing_concepts": [],
            "extra_concepts": [],
            "reasoning": "Max retries exceeded"
        }
    
    def batch_evaluate(self, evaluations: List[Tuple[str, List[str], str]], 
                       delay: float = 1.0) -> List[Dict]:
        """
        Evaluate multiple question-step pairs with rate limiting.
        
        Args:
            evaluations: List of (question, expected_steps, llm_steps) tuples
            delay: Seconds to wait between API calls
        
        Returns:
            List of evaluation results
        """
        results = []
        for i, (question, expected, generated) in enumerate(evaluations):
            result = self.evaluate(question, expected, generated)
            results.append(result)
            if i < len(evaluations) - 1:
                time.sleep(delay)
        return results

