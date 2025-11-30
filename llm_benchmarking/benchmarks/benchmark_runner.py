#!/usr/bin/env python3
"""
Benchmark Runner
Main orchestrator for running LLM benchmarks with hybrid evaluation
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.question_loader import QuestionLoader, Question
from benchmarks.llm_client import LLMClient, LLMResponse
from evaluators.sql_comparator import SQLComparator
from evaluators.table_column_matcher import TableColumnMatcher
from evaluators.gemini_similarity import GeminiSimilarityEvaluator


@dataclass
class QuestionResult:
    """Result for a single question evaluation."""
    question_id: str
    question_text: str
    category: str
    model_id: str
    
    # Responses
    methodology_response: str
    sql_response: str
    table_selection_response: str
    
    # Scores
    methodology_score: float
    sql_score: float
    table_column_score: float
    response_quality_score: float
    overall_score: float
    
    # Details
    methodology_details: Dict
    sql_details: Dict
    table_column_details: Dict
    
    # Metadata
    total_latency_ms: float
    total_tokens: int
    errors: List[str]
    timestamp: str


class BenchmarkRunner:
    """Orchestrates the complete benchmark process."""
    
    def __init__(self, results_dir: Optional[Path] = None,
                 use_gemini_eval: bool = True,
                 sample_size: Optional[int] = None):
        """
        Initialize benchmark runner.
        
        Args:
            results_dir: Directory to save results
            use_gemini_eval: Whether to use Gemini for methodology evaluation
            sample_size: Number of questions to sample (None = all)
        """
        self.base_dir = Path(__file__).parent.parent
        self.results_dir = results_dir or self.base_dir / "results"
        self.use_gemini_eval = use_gemini_eval
        self.sample_size = sample_size
        
        # Create results directories
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / "raw_responses").mkdir(exist_ok=True)
        (self.results_dir / "metrics").mkdir(exist_ok=True)
        (self.results_dir / "visualizations").mkdir(exist_ok=True)
        (self.results_dir / "logs").mkdir(exist_ok=True)
        
        # Initialize components
        self.question_loader = QuestionLoader()
        self.llm_client = LLMClient()
        self.sql_comparator = SQLComparator()
        self.table_matcher = TableColumnMatcher()
        
        # Initialize Gemini evaluator if enabled
        self.gemini_evaluator = None
        if use_gemini_eval:
            try:
                self.gemini_evaluator = GeminiSimilarityEvaluator()
            except Exception as e:
                print(f"Warning: Could not initialize Gemini evaluator: {e}")
                print("Methodology evaluation will use fallback scoring")
        
        # Load evaluation weights from config
        config_path = self.base_dir / "config" / "models_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.weights = config.get('evaluation', {}).get('weights', {
            'table_column_selection': 0.25,
            'sql_structure_matching': 0.35,
            'methodology_similarity': 0.30,
            'response_quality': 0.10
        })
        
        # Initialize logger
        self.log_file = self.results_dir / "logs" / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self._log(f"Benchmark initialized at {datetime.now().isoformat()}")
        self._log(f"Evaluation weights: {self.weights}")
    
    def _log(self, message: str, also_print: bool = True):
        """Log message to file and optionally print."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
        
        if also_print:
            print(message)
    
    def _evaluate_methodology(self, question: Question, 
                             response: str) -> Dict:
        """Evaluate methodology/reasoning response."""
        if self.gemini_evaluator and self.use_gemini_eval:
            try:
                result = self.gemini_evaluator.evaluate(
                    question=question.question,
                    expected_steps=question.calculation_steps,
                    llm_steps=response
                )
                # Check if Gemini evaluation actually succeeded (not quota/API error)
                reasoning = result.get('reasoning', '').lower()
                has_error = result.get('error', False) or result.get('is_quota_error', False)
                has_quota_in_reasoning = 'quota' in reasoning or '429' in reasoning or 'exceeded' in reasoning
                
                if not has_error and not has_quota_in_reasoning:
                    if result.get('similarity_score', 0) > 0:
                        return {
                            'score': result['similarity_score'],
                            'details': result
                        }
                    # Score is 0 but no error - might be legitimate 0, but use fallback for safety
                    self._log(f"Gemini returned 0 score, using fallback", also_print=False)
                else:
                    # Gemini failed (quota/error), use fallback
                    self._log(f"Gemini evaluation failed (quota/error detected), using fallback", also_print=False)
            except Exception as e:
                self._log(f"Gemini evaluation exception: {e}", also_print=False)
        
        # Fallback: improved keyword matching with better scoring
        expected_keywords = set()
        for step in question.calculation_steps:
            # Extract meaningful keywords (remove common words)
            words = step.lower().split()
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
            meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
            expected_keywords.update(meaningful_words)
        
        response_keywords = set()
        response_words = response.lower().split()
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
        meaningful_words = [w for w in response_words if w not in stop_words and len(w) > 2]
        response_keywords.update(meaningful_words)
        
        if not expected_keywords:
            return {
                'score': 0,
                'details': {
                    'method': 'keyword_fallback',
                    'reason': 'No expected keywords found'
                }
            }
        
        overlap = len(expected_keywords & response_keywords)
        score = (overlap / len(expected_keywords)) * 100
        
        return {
            'score': min(100, score),
            'details': {
                'method': 'keyword_fallback',
                'overlap_count': overlap,
                'expected_keyword_count': len(expected_keywords),
                'response_keyword_count': len(response_keywords)
            }
        }
    
    def _evaluate_sql(self, question: Question, response: str) -> Dict:
        """Evaluate SQL generation response."""
        result = self.sql_comparator.compare(
            expected_sql=question.sql_formula,
            generated_sql=response
        )
        return {
            'score': result['overall_score'],
            'details': result
        }
    
    def _evaluate_table_column(self, question: Question, response: str) -> Dict:
        """Evaluate table/column selection response."""
        result = self.table_matcher.match(
            expected_tables=question.related_tables,
            expected_columns=question.related_columns,
            response=response
        )
        return {
            'score': result['overall_score'],
            'details': result
        }
    
    def _evaluate_response_quality(self, responses: Dict[str, LLMResponse]) -> Dict:
        """Evaluate response quality metrics."""
        errors = []
        total_latency = 0
        total_tokens = 0
        has_content = 0
        
        for prompt_type, response in responses.items():
            total_latency += response.latency_ms
            total_tokens += response.tokens_used
            if response.error:
                errors.append(f"{prompt_type}: {response.error}")
            if response.response and len(response.response.strip()) > 10:
                has_content += 1
        
        # Quality score based on: no errors, has content, reasonable latency
        error_penalty = len(errors) * 20
        content_score = (has_content / 3) * 50
        latency_score = max(0, 50 - (total_latency / 1000))  # Penalty for slow responses
        
        score = max(0, min(100, content_score + latency_score - error_penalty))
        
        return {
            'score': score,
            'details': {
                'total_latency_ms': total_latency,
                'total_tokens': total_tokens,
                'errors': errors,
                'has_content_ratio': has_content / 3
            }
        }
    
    def evaluate_question(self, question: Question, model_id: str) -> QuestionResult:
        """Evaluate a single question with a model."""
        # Get responses for all prompt types
        responses = self.llm_client.query_all_prompts(
            model_id=model_id,
            question=question.question,
            question_id=question.id
        )
        
        # Check for API errors
        errors = []
        for prompt_type, resp in responses.items():
            if resp.error:
                errors.append(f"{prompt_type}: {resp.error}")
        
        # Evaluate each dimension
        try:
            methodology_eval = self._evaluate_methodology(
                question, responses['methodology'].response
            )
        except Exception as e:
            methodology_eval = {'score': 0, 'details': {'error': str(e)}}
        
        try:
            sql_eval = self._evaluate_sql(
                question, responses['sql'].response
            )
        except Exception as e:
            sql_eval = {'score': 0, 'details': {'error': str(e)}}
        
        try:
            table_column_eval = self._evaluate_table_column(
                question, responses['table_selection'].response
            )
        except Exception as e:
            table_column_eval = {'score': 0, 'details': {'error': str(e)}}
        
        quality_eval = self._evaluate_response_quality(responses)
        
        # Calculate weighted overall score
        overall_score = (
            table_column_eval['score'] * self.weights['table_column_selection'] +
            sql_eval['score'] * self.weights['sql_structure_matching'] +
            methodology_eval['score'] * self.weights['methodology_similarity'] +
            quality_eval['score'] * self.weights['response_quality']
        )
        
        return QuestionResult(
            question_id=question.id,
            question_text=question.question,
            category=question.category,
            model_id=model_id,
            methodology_response=responses['methodology'].response,
            sql_response=responses['sql'].response,
            table_selection_response=responses['table_selection'].response,
            methodology_score=methodology_eval['score'],
            sql_score=sql_eval['score'],
            table_column_score=table_column_eval['score'],
            response_quality_score=quality_eval['score'],
            overall_score=overall_score,
            methodology_details=methodology_eval['details'],
            sql_details=sql_eval['details'],
            table_column_details=table_column_eval['details'],
            total_latency_ms=quality_eval['details']['total_latency_ms'],
            total_tokens=quality_eval['details']['total_tokens'],
            errors=quality_eval['details']['errors'],
            timestamp=datetime.now().isoformat()
        )
    
    def run(self, models: Optional[List[str]] = None,
            categories: Optional[List[str]] = None) -> Dict:
        """
        Run the full benchmark.
        
        Args:
            models: List of model IDs to benchmark (None = all enabled)
            categories: List of categories to include (None = all)
        
        Returns:
            Dict with all results and summary
        """
        start_time = datetime.now()
        self._log("=" * 60)
        self._log("Starting LLM Benchmark")
        self._log("=" * 60)
        
        # Get models to benchmark
        if models is None:
            models = [m['id'] for m in self.llm_client.get_enabled_models()]
        self._log(f"Models to benchmark: {models}")
        
        # Get questions
        if self.sample_size:
            questions = self.question_loader.sample(self.sample_size, seed=42)
            self._log(f"Sampled {len(questions)} questions")
        else:
            questions = self.question_loader.get_all()
            self._log(f"Using all {len(questions)} questions")
        
        # Filter by category if specified
        if categories:
            questions = [q for q in questions if q.category in categories]
            self._log(f"Filtered to {len(questions)} questions in categories: {categories}")
        
        # Run benchmark
        all_results: List[QuestionResult] = []
        
        for model_id in models:
            self._log(f"\n--- Benchmarking: {model_id} ---")
            model_results = []
            
            for i, question in enumerate(questions):
                try:
                    self._log(f"  [{i+1}/{len(questions)}] {question.id}: {question.question[:50]}...")
                    result = self.evaluate_question(question, model_id)
                    model_results.append(result)
                    
                    self._log(f"    Score: {result.overall_score:.1f} (SQL: {result.sql_score:.1f}, "
                             f"Tables: {result.table_column_score:.1f}, Method: {result.methodology_score:.1f})")
                    
                except Exception as e:
                    self._log(f"    ERROR: {e}")
                    continue
            
            all_results.extend(model_results)
            
            # Save intermediate results for this model
            self._save_model_results(model_id, model_results)
        
        # Generate summary
        summary = self._generate_summary(all_results)
        
        # Save final results
        self._save_final_results(all_results, summary)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self._log(f"\n{'=' * 60}")
        self._log(f"Benchmark completed in {duration:.1f} seconds")
        self._log(f"Results saved to: {self.results_dir}")
        self._log("=" * 60)
        
        return {
            'results': all_results,
            'summary': summary,
            'duration_seconds': duration
        }
    
    def _save_model_results(self, model_id: str, results: List[QuestionResult]):
        """Save results for a single model."""
        model_dir = self.results_dir / "raw_responses" / model_id.replace('/', '_')
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        results_data = [asdict(r) for r in results]
        with open(model_dir / "results.json", 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    def _generate_summary(self, results: List[QuestionResult]) -> Dict:
        """Generate summary statistics from results."""
        if not results:
            return {}
        
        # Group by model
        by_model = {}
        for r in results:
            if r.model_id not in by_model:
                by_model[r.model_id] = []
            by_model[r.model_id].append(r)
        
        # Group by category
        by_category = {}
        for r in results:
            if r.category not in by_category:
                by_category[r.category] = []
            by_category[r.category].append(r)
        
        summary = {
            'total_evaluations': len(results),
            'models_evaluated': list(by_model.keys()),
            'categories_evaluated': list(by_category.keys()),
            'by_model': {},
            'by_category': {},
            'overall': {}
        }
        
        # Model summaries
        for model_id, model_results in by_model.items():
            summary['by_model'][model_id] = {
                'count': len(model_results),
                'avg_overall': sum(r.overall_score for r in model_results) / len(model_results),
                'avg_sql': sum(r.sql_score for r in model_results) / len(model_results),
                'avg_table_column': sum(r.table_column_score for r in model_results) / len(model_results),
                'avg_methodology': sum(r.methodology_score for r in model_results) / len(model_results),
                'avg_latency_ms': sum(r.total_latency_ms for r in model_results) / len(model_results),
                'error_count': sum(1 for r in model_results if r.errors)
            }
        
        # Category summaries
        for category, cat_results in by_category.items():
            summary['by_category'][category] = {
                'count': len(cat_results),
                'avg_overall': sum(r.overall_score for r in cat_results) / len(cat_results),
                'avg_sql': sum(r.sql_score for r in cat_results) / len(cat_results),
                'avg_table_column': sum(r.table_column_score for r in cat_results) / len(cat_results),
                'avg_methodology': sum(r.methodology_score for r in cat_results) / len(cat_results)
            }
        
        # Overall stats
        summary['overall'] = {
            'avg_overall': sum(r.overall_score for r in results) / len(results),
            'avg_sql': sum(r.sql_score for r in results) / len(results),
            'avg_table_column': sum(r.table_column_score for r in results) / len(results),
            'avg_methodology': sum(r.methodology_score for r in results) / len(results),
            'avg_latency_ms': sum(r.total_latency_ms for r in results) / len(results)
        }
        
        return summary
    
    def _save_final_results(self, results: List[QuestionResult], summary: Dict):
        """Save final aggregated results."""
        # Save all results as JSON
        metrics_dir = self.results_dir / "metrics"
        
        results_data = [asdict(r) for r in results]
        with open(metrics_dir / "all_results.json", 'w', encoding='utf-8') as f:
            json.dump({
                'results': results_data,
                'summary': summary
            }, f, indent=2, ensure_ascii=False)
        
        # Save summary
        with open(metrics_dir / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Save as CSV for easy analysis
        try:
            import pandas as pd
            if results_data:
                df = pd.DataFrame(results_data)
                df.to_csv(metrics_dir / "all_results.csv", index=False)
            
            # Model comparison CSV
            if summary.get('by_model'):
                model_comparison = pd.DataFrame(summary['by_model']).T
                model_comparison.to_csv(self.results_dir / "model_comparison.csv")
            
            # Category breakdown CSV
            if summary.get('by_category'):
                category_breakdown = pd.DataFrame(summary['by_category']).T
                category_breakdown.to_csv(self.results_dir / "category_breakdown.csv")
        except ImportError:
            self._log("pandas not available, skipping CSV export")
        except Exception as e:
            self._log(f"Error saving CSV: {e}")
        
        # Update log with summary
        self._log("\n" + "=" * 40)
        self._log("BENCHMARK SUMMARY")
        self._log("=" * 40)
        
        for model_id, stats in summary.get('by_model', {}).items():
            self._log(f"\n{model_id}:")
            self._log(f"  Overall Score: {stats['avg_overall']:.1f}")
            self._log(f"  SQL Score: {stats['avg_sql']:.1f}")
            self._log(f"  Table/Column Score: {stats['avg_table_column']:.1f}")
            self._log(f"  Methodology Score: {stats['avg_methodology']:.1f}")
            self._log(f"  Avg Latency: {stats['avg_latency_ms']:.0f}ms")


def main():
    """Main entry point for running benchmark."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LLM Benchmark")
    parser.add_argument("--sample", type=int, default=None, 
                       help="Number of questions to sample (default: all)")
    parser.add_argument("--no-gemini", action="store_true",
                       help="Disable Gemini-based methodology evaluation")
    parser.add_argument("--models", nargs="+", default=None,
                       help="Specific model IDs to benchmark")
    parser.add_argument("--categories", nargs="+", default=None,
                       help="Categories to include (Easy, Medium, Complex)")
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    runner = BenchmarkRunner(
        use_gemini_eval=not args.no_gemini,
        sample_size=args.sample
    )
    
    runner.run(models=args.models, categories=args.categories)


if __name__ == "__main__":
    main()
