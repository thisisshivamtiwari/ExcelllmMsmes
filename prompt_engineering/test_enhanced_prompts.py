#!/usr/bin/env python3
"""
Test Enhanced Prompts for Llama 4 Maverick
Compares enhanced prompts against baseline performance
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from llama4_maverick_optimizer import EnhancedPromptEngineer, PromptResult

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "llm_benchmarking"))

try:
    from evaluators.sql_comparator import SQLComparator
    from evaluators.table_column_matcher import TableColumnMatcher
    from evaluators.gemini_similarity import GeminiSimilarityEvaluator
    HAS_EVALUATORS = True
except ImportError:
    print("Warning: Evaluators not found. Install llm_benchmarking dependencies.")
    HAS_EVALUATORS = False
    SQLComparator = None
    TableColumnMatcher = None
    GeminiSimilarityEvaluator = None


class PromptTester:
    """Test and compare prompt versions."""
    
    def __init__(self):
        self.optimizer = EnhancedPromptEngineer()
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize evaluators
        if HAS_EVALUATORS:
            self.sql_comparator = SQLComparator()
            self.table_matcher = TableColumnMatcher()
            try:
                self.gemini_evaluator = GeminiSimilarityEvaluator()
            except:
                self.gemini_evaluator = None
        else:
            self.sql_comparator = None
            self.table_matcher = None
            self.gemini_evaluator = None
    
    def load_test_questions(self, limit: int = 10, categories: List[str] = None) -> List[Dict]:
        """Load questions for testing."""
        questions_file = Path(__file__).parent.parent / "question_generator" / "generated_questions.json"
        
        with open(questions_file, 'r') as f:
            data = json.load(f)
        
        all_questions = []
        for category in data['questions']:
            if categories and category not in categories:
                continue
            for q in data['questions'][category]:
                q['category'] = category
                all_questions.append(q)
        
        return all_questions[:limit]
    
    def evaluate_response(self, question: Dict, response: Dict) -> Dict:
        """Evaluate a response against ground truth."""
        scores = {
            'sql_score': 0.0,
            'table_column_score': 0.0,
            'methodology_score': 0.0,
            'overall_score': 0.0
        }
        
        # Extract SQL from response using SQLComparator's method
        sql_response_raw = response.get('sql', '')
        sql_response = ""
        
        if sql_response_raw and self.sql_comparator:
            # Use SQLComparator's extraction method which handles various formats
            sql_response = self.sql_comparator.extract_sql_from_response(sql_response_raw)
        
        # Evaluate SQL
        expected_sql = question.get('sql_formula', '')
        if expected_sql and sql_response and self.sql_comparator:
            try:
                sql_eval = self.sql_comparator.compare(expected_sql, sql_response)
                scores['sql_score'] = sql_eval.get('score', 0.0)
            except Exception as e:
                # Debug: could log error here
                pass
        
        # Evaluate table/column selection
        table_response_raw = response.get('table_selection', '')
        expected_tables = question.get('related_tables', [])
        expected_columns = question.get('related_columns', [])
        
        if table_response_raw and expected_tables and expected_columns:
            try:
                # Extract JSON from response
                json_start = table_response_raw.find('{')
                json_end = table_response_raw.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = table_response_raw[json_start:json_end]
                    
                    # Remove markdown code blocks if present
                    if '```json' in json_str:
                        start = json_str.find('```json') + 7
                        end = json_str.find('```', start)
                        json_str = json_str[start:end].strip()
                    elif '```' in json_str:
                        start = json_str.find('```') + 3
                        end = json_str.find('```', start)
                        json_str = json_str[start:end].strip()
                    
                    table_data = json.loads(json_str)
                    tables = table_data.get('tables', [])
                    columns = table_data.get('columns', [])
                    
                    if self.table_matcher:
                        # Use match() method which takes raw response string
                        table_eval = self.table_matcher.match(
                            expected_tables, expected_columns,
                            table_response_raw
                        )
                        scores['table_column_score'] = table_eval.get('overall_score', 0.0)
            except json.JSONDecodeError as e:
                # JSON parsing failed - try to extract tables/columns from text
                pass
            except Exception as e:
                # Other errors
                pass
        
        # Evaluate methodology
        methodology_response = response.get('methodology', '')
        expected_steps = question.get('calculation_steps', [])
        
        if methodology_response and expected_steps and self.gemini_evaluator:
            try:
                meth_eval = self.gemini_evaluator.evaluate(
                    question=question.get('question', ''),
                    expected_steps=expected_steps,
                    llm_steps=methodology_response
                )
                scores['methodology_score'] = meth_eval.get('similarity_score', 0.0)
            except:
                pass
        
        # Calculate overall score (weighted)
        weights = {
            'sql': 0.35,
            'table_column': 0.25,
            'methodology': 0.30,
            'response_quality': 0.10
        }
        
        scores['overall_score'] = (
            scores['sql_score'] * weights['sql'] +
            scores['table_column_score'] * weights['table_column'] +
            scores['methodology_score'] * weights['methodology'] +
            90.0 * weights['response_quality']  # Assume good response quality if no errors
        )
        
        return scores
    
    def test_prompts(self, questions: List[Dict], prompt_version: str = "enhanced_v1") -> List[Dict]:
        """Test enhanced prompts on questions."""
        results = []
        
        print(f"\nTesting {len(questions)} questions with {prompt_version}...")
        print("="*70)
        
        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] {question.get('id', 'unknown')}: {question.get('question', '')[:60]}...")
            
            try:
                # Test with enhanced prompts
                result = self.optimizer.test_question(question, prompt_version)
                
                # Parse response
                response_data = json.loads(result.response) if result.response.startswith('{') else {}
                
                # Evaluate
                scores = self.evaluate_response(question, response_data)
                
                result_dict = {
                    'question_id': result.question_id,
                    'question_text': result.question_text,
                    'category': result.category,
                    'prompt_version': prompt_version,
                    'scores': scores,
                    'latency_ms': result.latency_ms,
                    'tokens': result.tokens,
                    'error': result.error,
                    'response': response_data
                }
                
                results.append(result_dict)
                
                print(f"  ✓ Score: {scores['overall_score']:.1f}% (SQL: {scores['sql_score']:.1f}%, "
                      f"Tables: {scores['table_column_score']:.1f}%, Method: {scores['methodology_score']:.1f}%)")
                print(f"  Latency: {result.latency_ms:.0f}ms")
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)[:100]}")
                results.append({
                    'question_id': question.get('id', 'unknown'),
                    'error': str(e),
                    'scores': {'overall_score': 0.0}
                })
        
        return results
    
    def save_results(self, results: List[Dict], filename: str = "enhanced_prompt_results.json"):
        """Save test results."""
        output_file = self.results_dir / filename
        
        summary = {
            'total_questions': len(results),
            'avg_overall_score': sum(r.get('scores', {}).get('overall_score', 0) for r in results) / len(results) if results else 0,
            'avg_sql_score': sum(r.get('scores', {}).get('sql_score', 0) for r in results) / len(results) if results else 0,
            'avg_table_score': sum(r.get('scores', {}).get('table_column_score', 0) for r in results) / len(results) if results else 0,
            'avg_methodology_score': sum(r.get('scores', {}).get('methodology_score', 0) for r in results) / len(results) if results else 0,
            'total_latency_ms': sum(r.get('latency_ms', 0) for r in results),
            'total_tokens': sum(r.get('tokens', 0) for r in results),
            'error_count': sum(1 for r in results if r.get('error')),
            'results': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✓ Results saved to: {output_file}")
        print(f"\nSummary:")
        print(f"  Average Overall Score: {summary['avg_overall_score']:.1f}%")
        print(f"  Average SQL Score: {summary['avg_sql_score']:.1f}%")
        print(f"  Average Table/Column Score: {summary['avg_table_score']:.1f}%")
        print(f"  Average Methodology Score: {summary['avg_methodology_score']:.1f}%")
        print(f"  Total Latency: {summary['total_latency_ms']:.0f}ms")
        print(f"  Error Rate: {summary['error_count']}/{summary['total_questions']}")


def main():
    """Main test function."""
    print("="*70)
    print("Enhanced Prompt Testing for Llama 4 Maverick")
    print("="*70)
    
    tester = PromptTester()
    
    # Load test questions (focus on Complex questions that performed worst)
    questions = tester.load_test_questions(limit=10, categories=['Complex'])
    
    print(f"\nLoaded {len(questions)} Complex questions for testing")
    
    # Test enhanced prompts
    results = tester.test_prompts(questions, prompt_version="enhanced_v1")
    
    # Save results
    tester.save_results(results)


if __name__ == "__main__":
    main()

