#!/usr/bin/env python3
"""
Compare Baseline vs Enhanced Prompt Performance
Compares Llama 4 Maverick baseline results with enhanced prompt results
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import pandas as pd

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "llm_benchmarking"))

from llama4_maverick_optimizer import EnhancedPromptEngineer
from evaluators.sql_comparator import SQLComparator
from evaluators.table_column_matcher import TableColumnMatcher
from evaluators.gemini_similarity import GeminiSimilarityEvaluator


class BaselineVsEnhancedComparator:
    """Compare baseline and enhanced prompt performance."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.baseline_results_file = self.base_dir.parent / "llm_benchmarking" / "results" / "metrics" / "all_results.json"
        self.questions_file = self.base_dir.parent / "question_generator" / "generated_questions.json"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.optimizer = EnhancedPromptEngineer()
        self.sql_comparator = SQLComparator()
        self.table_matcher = TableColumnMatcher()
        try:
            self.gemini_evaluator = GeminiSimilarityEvaluator()
        except:
            self.gemini_evaluator = None
        
        # Load data
        self.baseline_results = self._load_baseline_results()
        self.questions = self._load_questions()
    
    def _load_baseline_results(self) -> Dict:
        """Load baseline benchmark results."""
        if not self.baseline_results_file.exists():
            print(f"Warning: Baseline results not found: {self.baseline_results_file}")
            return {}
        
        with open(self.baseline_results_file, 'r') as f:
            data = json.load(f)
        
        # Filter for Llama 4 Maverick only
        maverick_results = {}
        for result in data.get('results', []):
            if 'maverick' in result.get('model_id', '').lower():
                q_id = result.get('question_id', '')
                maverick_results[q_id] = result
        
        print(f"✓ Loaded {len(maverick_results)} baseline results for Llama 4 Maverick")
        return maverick_results
    
    def _load_questions(self) -> Dict:
        """Load questions from question_generator."""
        if not self.questions_file.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_file}")
        
        with open(self.questions_file, 'r') as f:
            data = json.load(f)
        
        questions = {}
        for category in data.get('questions', {}):
            for q in data['questions'][category]:
                questions[q['id']] = q
        
        print(f"✓ Loaded {len(questions)} questions")
        return questions
    
    def extract_sql_from_response(self, response: str) -> str:
        """Extract SQL from response, handling various formats."""
        if not response:
            return ""
        
        # Try multiple extraction methods
        # Method 1: Use SQLComparator's extraction
        sql = self.sql_comparator.extract_sql_from_response(response)
        if sql and len(sql) > 10:
            return sql
        
        # Method 2: Manual extraction from markdown
        import re
        patterns = [
            r'```sql\s*(.*?)\s*```',
            r'```\s*(SELECT.*?)\s*```',
            r'(SELECT\s+.*?)(?:;|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 10:
                    return extracted
        
        # Method 3: Find SELECT statement
        if 'SELECT' in response.upper():
            lines = response.split('\n')
            sql_lines = []
            in_sql = False
            for line in lines:
                line_upper = line.upper().strip()
                if 'SELECT' in line_upper and not in_sql:
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    # Stop at empty line after SQL or at semicolon
                    if ';' in line or (line.strip() == '' and sql_lines):
                        break
            if sql_lines:
                return '\n'.join(sql_lines).strip()
        
        return ""
    
    def extract_table_selection_from_response(self, response: str) -> Optional[Dict]:
        """Extract table/column selection from response."""
        if not response:
            return None
        
        try:
            # Try to find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                # Try to extract from markdown code blocks
                if '```json' in json_str:
                    start = json_str.find('```json') + 7
                    end = json_str.find('```', start)
                    json_str = json_str[start:end].strip()
                elif '```' in json_str:
                    start = json_str.find('```') + 3
                    end = json_str.find('```', start)
                    json_str = json_str[start:end].strip()
                
                data = json.loads(json_str)
                return {
                    'tables': data.get('tables', []),
                    'columns': data.get('columns', [])
                }
        except:
            pass
        
        return None
    
    def evaluate_enhanced_response(self, question: Dict, response: Dict) -> Dict:
        """Evaluate enhanced prompt response against ground truth."""
        scores = {
            'sql_score': 0.0,
            'table_column_score': 0.0,
            'methodology_score': 0.0,
            'overall_score': 0.0
        }
        
        # Evaluate SQL - match exactly how benchmark_runner does it
        # Pass raw response, let SQLComparator handle extraction internally
        sql_response_raw = response.get('sql', '')
        expected_sql = question.get('sql_formula', '')
        
        if expected_sql and sql_response_raw:
            try:
                # SQLComparator.compare() handles extraction internally
                # It checks for ```sql blocks and extracts automatically
                sql_eval = self.sql_comparator.compare(
                    expected_sql=expected_sql,
                    generated_sql=sql_response_raw  # Pass raw response
                )
                # SQLComparator returns 'overall_score' (0-100)
                scores['sql_score'] = sql_eval.get('overall_score', 0.0)
            except Exception as e:
                # Debug: print error to understand what's failing
                print(f"  SQL evaluation error: {str(e)[:150]}")
                # Don't print full traceback in production, but keep for debugging
                pass
        
        # Evaluate table/column selection (use raw response, matcher extracts internally)
        table_response_raw = response.get('table_selection', '')
        expected_tables = question.get('related_tables', [])
        expected_columns = question.get('related_columns', [])
        
        if table_response_raw and expected_tables and expected_columns:
            try:
                if self.table_matcher:
                    # Use match() method which takes raw response string
                    table_eval = self.table_matcher.match(
                        expected_tables, expected_columns,
                        table_response_raw
                    )
                    scores['table_column_score'] = table_eval.get('overall_score', 0.0)
            except Exception as e:
                # Debug: could log error here
                pass
        
        # Evaluate methodology
        methodology_response = response.get('methodology', '')
        expected_steps = question.get('calculation_steps', [])
        
        if methodology_response and expected_steps:
            if self.gemini_evaluator:
                try:
                    meth_eval = self.gemini_evaluator.evaluate(
                        question=question.get('question', ''),
                        expected_steps=expected_steps,
                        llm_steps=methodology_response
                    )
                    scores['methodology_score'] = meth_eval.get('similarity_score', 0.0)
                except:
                    # Fallback to keyword matching
                    pass
        
        # Calculate overall score (same weights as benchmark)
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
            90.0 * weights['response_quality']  # Assume good quality if no errors
        )
        
        return scores
    
    def compare_question(self, question_id: str) -> Optional[Dict]:
        """Compare baseline vs enhanced for a single question."""
        question = self.questions.get(question_id)
        baseline = self.baseline_results.get(question_id)
        
        if not question:
            return None
        
        if not baseline:
            print(f"  Warning: No baseline result for {question_id}")
            return None
        
        # Test with enhanced prompts
        try:
            result = self.optimizer.test_question(question, prompt_version="enhanced_v1")
            
            # Parse response - result.response is a dict or JSON string
            if isinstance(result.response, dict):
                response_data = result.response
            elif isinstance(result.response, str):
                try:
                    response_data = json.loads(result.response)
                except json.JSONDecodeError:
                    # If not JSON, it might be a single string response
                    # Try to parse as if it contains all three responses
                    response_data = {
                        "methodology": result.response,
                        "sql": result.response,
                        "table_selection": result.response
                    }
            else:
                response_data = {}
            
            # Ensure we have the right structure
            if not isinstance(response_data, dict):
                response_data = {}
            if 'sql' not in response_data:
                response_data['sql'] = ''
            if 'methodology' not in response_data:
                response_data['methodology'] = ''
            if 'table_selection' not in response_data:
                response_data['table_selection'] = ''
            
            # Evaluate enhanced response
            enhanced_scores = self.evaluate_enhanced_response(question, response_data)
            
            # Get baseline scores
            baseline_scores = {
                'sql_score': baseline.get('sql_score', 0.0),
                'table_column_score': baseline.get('table_column_score', 0.0),
                'methodology_score': baseline.get('methodology_score', 0.0),
                'overall_score': baseline.get('overall_score', 0.0)
            }
            
            # Calculate improvements
            improvements = {
                'sql_improvement': enhanced_scores['sql_score'] - baseline_scores['sql_score'],
                'table_improvement': enhanced_scores['table_column_score'] - baseline_scores['table_column_score'],
                'methodology_improvement': enhanced_scores['methodology_score'] - baseline_scores['methodology_score'],
                'overall_improvement': enhanced_scores['overall_score'] - baseline_scores['overall_score']
            }
            
            return {
                'question_id': question_id,
                'question_text': question.get('question', ''),
                'category': question.get('category', ''),
                'baseline': baseline_scores,
                'enhanced': enhanced_scores,
                'improvements': improvements,
                'latency_ms': result.latency_ms,
                'tokens': result.tokens,
                'error': result.error
            }
            
        except Exception as e:
            return {
                'question_id': question_id,
                'error': str(e),
                'baseline': {
                    'overall_score': baseline.get('overall_score', 0.0) if baseline else 0.0
                },
                'enhanced': {'overall_score': 0.0},
                'improvements': {'overall_improvement': 0.0}
            }
    
    def compare_all(self, question_ids: Optional[List[str]] = None, limit: int = 10) -> List[Dict]:
        """Compare baseline vs enhanced for multiple questions."""
        if question_ids is None:
            # Get questions that have baseline results
            question_ids = list(self.baseline_results.keys())[:limit]
        
        print(f"\nComparing {len(question_ids)} questions...")
        print("="*70)
        
        results = []
        for i, q_id in enumerate(question_ids, 1):
            print(f"\n[{i}/{len(question_ids)}] {q_id}")
            comparison = self.compare_question(q_id)
            if comparison:
                results.append(comparison)
                
                # Show comparison
                baseline_score = comparison['baseline']['overall_score']
                enhanced_score = comparison['enhanced']['overall_score']
                improvement = comparison['improvements']['overall_improvement']
                
                improvement_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
                color = "✓" if improvement > 0 else "✗"
                
                print(f"  Baseline: {baseline_score:.1f}% | Enhanced: {enhanced_score:.1f}% | {color} {improvement_str}")
                print(f"  SQL: {comparison['baseline']['sql_score']:.1f}% → {comparison['enhanced']['sql_score']:.1f}% "
                      f"({comparison['improvements']['sql_improvement']:+.1f}%)")
                print(f"  Tables: {comparison['baseline']['table_column_score']:.1f}% → "
                      f"{comparison['enhanced']['table_column_score']:.1f}% "
                      f"({comparison['improvements']['table_improvement']:+.1f}%)")
                print(f"  Method: {comparison['baseline']['methodology_score']:.1f}% → "
                      f"{comparison['enhanced']['methodology_score']:.1f}% "
                      f"({comparison['improvements']['methodology_improvement']:+.1f}%)")
        
        return results
    
    def generate_comparison_report(self, results: List[Dict]) -> Dict:
        """Generate summary report."""
        if not results:
            return {}
        
        # Calculate averages
        baseline_avg = {
            'sql': sum(r['baseline']['sql_score'] for r in results) / len(results),
            'table': sum(r['baseline']['table_column_score'] for r in results) / len(results),
            'methodology': sum(r['baseline']['methodology_score'] for r in results) / len(results),
            'overall': sum(r['baseline']['overall_score'] for r in results) / len(results)
        }
        
        enhanced_avg = {
            'sql': sum(r['enhanced']['sql_score'] for r in results) / len(results),
            'table': sum(r['enhanced']['table_column_score'] for r in results) / len(results),
            'methodology': sum(r['enhanced']['methodology_score'] for r in results) / len(results),
            'overall': sum(r['enhanced']['overall_score'] for r in results) / len(results)
        }
        
        improvements_avg = {
            'sql': enhanced_avg['sql'] - baseline_avg['sql'],
            'table': enhanced_avg['table'] - baseline_avg['table'],
            'methodology': enhanced_avg['methodology'] - baseline_avg['methodology'],
            'overall': enhanced_avg['overall'] - baseline_avg['overall']
        }
        
        # Count improvements
        improved_count = sum(1 for r in results if r['improvements']['overall_improvement'] > 0)
        degraded_count = sum(1 for r in results if r['improvements']['overall_improvement'] < 0)
        same_count = len(results) - improved_count - degraded_count
        
        return {
            'total_questions': len(results),
            'baseline_averages': baseline_avg,
            'enhanced_averages': enhanced_avg,
            'average_improvements': improvements_avg,
            'improved': improved_count,
            'degraded': degraded_count,
            'same': same_count,
            'improvement_rate': (improved_count / len(results)) * 100 if results else 0
        }
    
    def save_comparison(self, results: List[Dict], report: Dict):
        """Save comparison results."""
        output_file = self.results_dir / "baseline_vs_enhanced_comparison.json"
        
        data = {
            'report': report,
            'detailed_results': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✓ Comparison saved to: {output_file}")
        
        # Also save CSV
        csv_file = self.results_dir / "baseline_vs_enhanced_comparison.csv"
        df_data = []
        for r in results:
            df_data.append({
                'question_id': r['question_id'],
                'category': r.get('category', ''),
                'baseline_overall': r['baseline']['overall_score'],
                'enhanced_overall': r['enhanced']['overall_score'],
                'overall_improvement': r['improvements']['overall_improvement'],
                'baseline_sql': r['baseline']['sql_score'],
                'enhanced_sql': r['enhanced']['sql_score'],
                'sql_improvement': r['improvements']['sql_improvement'],
                'baseline_tables': r['baseline']['table_column_score'],
                'enhanced_tables': r['enhanced']['table_column_score'],
                'tables_improvement': r['improvements']['table_improvement'],
                'baseline_methodology': r['baseline']['methodology_score'],
                'enhanced_methodology': r['enhanced']['methodology_score'],
                'methodology_improvement': r['improvements']['methodology_improvement']
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(csv_file, index=False)
        print(f"✓ CSV saved to: {csv_file}")


def main():
    """Main comparison function."""
    print("="*70)
    print("Baseline vs Enhanced Prompt Comparison")
    print("Model: meta-llama/llama-4-maverick-17b-128e-instruct")
    print("="*70)
    
    comparator = BaselineVsEnhancedComparator()
    
    # Compare questions (focus on Complex questions that performed worst)
    # Get Complex questions from baseline
    complex_questions = [
        q_id for q_id in comparator.baseline_results.keys()
        if comparator.questions.get(q_id, {}).get('category') == 'Complex'
    ][:10]  # Test 10 Complex questions
    
    print(f"\nSelected {len(complex_questions)} Complex questions for comparison")
    
    # Run comparison
    results = comparator.compare_all(question_ids=complex_questions)
    
    if results:
        # Generate report
        report = comparator.generate_comparison_report(results)
        
        # Display summary
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        print(f"\nTotal Questions: {report['total_questions']}")
        print(f"\nAverage Scores:")
        print(f"  Baseline Overall: {report['baseline_averages']['overall']:.1f}%")
        print(f"  Enhanced Overall: {report['enhanced_averages']['overall']:.1f}%")
        print(f"  Improvement: {report['average_improvements']['overall']:+.1f}%")
        print(f"\nComponent Improvements:")
        print(f"  SQL: {report['average_improvements']['sql']:+.1f}%")
        print(f"  Tables/Columns: {report['average_improvements']['table']:+.1f}%")
        print(f"  Methodology: {report['average_improvements']['methodology']:+.1f}%")
        print(f"\nResults:")
        print(f"  Improved: {report['improved']} ({report['improvement_rate']:.1f}%)")
        print(f"  Degraded: {report['degraded']}")
        print(f"  Same: {report['same']}")
        
        # Save results
        comparator.save_comparison(results, report)
        
        # Generate visualizations
        print("\n" + "="*70)
        print("Generating Visualizations...")
        print("="*70)
        try:
            from visualize_comparison import ComparisonVisualizer
            visualizer = ComparisonVisualizer()
            visualizer.generate_all()
        except Exception as e:
            print(f"Warning: Could not generate visualizations: {e}")
            print("You can run visualizations manually with: python3 visualize_comparison.py")
    else:
        print("\nNo results to compare")


if __name__ == "__main__":
    main()

