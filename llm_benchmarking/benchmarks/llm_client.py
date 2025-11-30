#!/usr/bin/env python3
"""
Unified LLM Client
Handles API calls to different LLM providers (Groq, etc.)
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Represents an LLM response."""
    model_id: str
    prompt_type: str
    question_id: str
    response: str
    latency_ms: float
    tokens_used: int
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class LLMClient:
    """Unified client for LLM API calls."""
    
    def __init__(self, config_path: Optional[Path] = None):
        # Load config
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "models_config.json"
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Load API keys from environment
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Initialize clients
        self.groq_client = None
        self._init_groq()
        
        # Load prompt templates
        self.prompts = self._load_prompts()
    
    def _init_groq(self):
        """Initialize Groq client."""
        if not self.groq_api_key:
            print("Warning: GROQ_API_KEY not found")
            return
        
        try:
            from groq import Groq
            self.groq_client = Groq(api_key=self.groq_api_key)
            print("Groq client initialized")
        except ImportError:
            print("Warning: groq package not installed")
        except Exception as e:
            print(f"Warning: Could not initialize Groq client: {e}")
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates."""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompts = {}
        
        prompt_files = {
            'methodology': 'methodology_prompt.txt',
            'sql': 'sql_generation_prompt.txt',
            'table_selection': 'table_selection_prompt.txt'
        }
        
        for key, filename in prompt_files.items():
            filepath = prompts_dir / filename
            if filepath.exists():
                prompts[key] = filepath.read_text()
            else:
                prompts[key] = "{question}"  # Fallback
        
        return prompts
    
    def get_enabled_models(self) -> List[Dict]:
        """Get list of enabled models from config."""
        return [m for m in self.config.get('models', []) if m.get('enabled', True)]
    
    def _call_groq(self, model_id: str, prompt: str, 
                   max_tokens: int = 1024) -> Dict:
        """Make API call to Groq."""
        if self.groq_client is None:
            raise RuntimeError("Groq client not initialized")
        
        start_time = time.time()
        
        try:
            response = self.groq_client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.1  # Low temperature for consistency
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                'response': response.choices[0].message.content,
                'latency_ms': latency_ms,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'error': None,
                'raw_response': {
                    'id': response.id,
                    'model': response.model,
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                        'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                        'total_tokens': response.usage.total_tokens if response.usage else 0
                    }
                }
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                'response': '',
                'latency_ms': latency_ms,
                'tokens_used': 0,
                'error': str(e),
                'raw_response': None
            }
    
    def query(self, model_id: str, question: str, 
              prompt_type: str = 'methodology',
              question_id: str = '') -> LLMResponse:
        """
        Query an LLM with a question.
        
        Args:
            model_id: Model identifier (e.g., 'llama-3.1-8b-instant')
            question: The question to ask
            prompt_type: Type of prompt ('methodology', 'sql', 'table_selection')
            question_id: Optional question ID for tracking
        
        Returns:
            LLMResponse object
        """
        # Build prompt
        prompt_template = self.prompts.get(prompt_type, "{question}")
        prompt = prompt_template.format(question=question)
        
        # Determine provider and make call
        model_config = next(
            (m for m in self.config.get('models', []) if m['id'] == model_id),
            None
        )
        provider = model_config.get('provider', 'groq') if model_config else 'groq'
        
        if provider == 'groq':
            result = self._call_groq(model_id, prompt)
        else:
            result = {
                'response': '',
                'latency_ms': 0,
                'tokens_used': 0,
                'error': f'Unknown provider: {provider}',
                'raw_response': None
            }
        
        return LLMResponse(
            model_id=model_id,
            prompt_type=prompt_type,
            question_id=question_id,
            response=result['response'],
            latency_ms=result['latency_ms'],
            tokens_used=result['tokens_used'],
            error=result['error'],
            raw_response=result['raw_response']
        )
    
    def query_all_prompts(self, model_id: str, question: str,
                          question_id: str = '') -> Dict[str, LLMResponse]:
        """
        Query a model with all prompt types.
        
        Returns:
            Dict mapping prompt_type to LLMResponse
        """
        results = {}
        rate_limit_delay = self.config.get('providers', {}).get('groq', {}).get('rate_limit_delay', 1.0)
        
        for prompt_type in ['methodology', 'sql', 'table_selection']:
            results[prompt_type] = self.query(
                model_id=model_id,
                question=question,
                prompt_type=prompt_type,
                question_id=question_id
            )
            time.sleep(rate_limit_delay)
        
        return results
    
    def batch_query(self, model_id: str, questions: List[Dict],
                    prompt_type: str = 'methodology') -> List[LLMResponse]:
        """
        Query a model with multiple questions.
        
        Args:
            model_id: Model identifier
            questions: List of dicts with 'id' and 'question' keys
            prompt_type: Type of prompt to use
        
        Returns:
            List of LLMResponse objects
        """
        results = []
        rate_limit_delay = self.config.get('providers', {}).get('groq', {}).get('rate_limit_delay', 1.0)
        
        for q in questions:
            response = self.query(
                model_id=model_id,
                question=q['question'],
                prompt_type=prompt_type,
                question_id=q.get('id', '')
            )
            results.append(response)
            time.sleep(rate_limit_delay)
        
        return results
