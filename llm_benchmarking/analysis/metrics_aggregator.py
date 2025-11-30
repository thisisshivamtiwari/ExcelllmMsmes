#!/usr/bin/env python3
"""
Metrics Aggregator
Aggregates and analyzes benchmark results with statistical analysis
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@dataclass
class ModelStats:
    """Statistics for a single model."""
    model_id: str
    total_questions: int
    avg_overall: float
    std_overall: float
    avg_sql: float
    avg_table_column: float
    avg_methodology: float
    avg_latency_ms: float
    error_rate: float
    by_category: Dict[str, Dict]


class MetricsAggregator:
    """Aggregates and analyzes benchmark metrics."""
    
    def __init__(self, results_dir: Optional[Path] = None):
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"
        self.results = []
        self.summary = {}
    
    def load_results(self, results_file: Optional[Path] = None) -> bool:
        """Load results from JSON file."""
        if results_file is None:
            results_file = self.results_dir / "metrics" / "all_results.json"
        
        if not results_file.exists():
            print(f"Results file not found: {results_file}")
            return False
        
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.results = data.get('results', [])
        self.summary = data.get('summary', {})
        
        print(f"Loaded {len(self.results)} results")
        return True
    
    def get_model_comparison(self) -> Dict[str, ModelStats]:
        """Get detailed comparison between models."""
        if not self.results:
            return {}
        
        # Group by model
        by_model: Dict[str, List] = {}
        for r in self.results:
            model = r.get('model_id', 'unknown')
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(r)
        
        stats = {}
        for model_id, model_results in by_model.items():
            overall_scores = [r['overall_score'] for r in model_results]
            sql_scores = [r['sql_score'] for r in model_results]
            table_scores = [r['table_column_score'] for r in model_results]
            method_scores = [r['methodology_score'] for r in model_results]
            latencies = [r['total_latency_ms'] for r in model_results]
            
            # Category breakdown
            by_cat = {}
            for r in model_results:
                cat = r.get('category', 'unknown')
                if cat not in by_cat:
                    by_cat[cat] = []
                by_cat[cat].append(r['overall_score'])
            
            category_stats = {
                cat: {
                    'avg': sum(scores) / len(scores) if scores else 0,
                    'count': len(scores)
                }
                for cat, scores in by_cat.items()
            }
            
            # Calculate statistics
            if HAS_NUMPY:
                std_overall = float(np.std(overall_scores))
            else:
                mean = sum(overall_scores) / len(overall_scores)
                std_overall = (sum((x - mean) ** 2 for x in overall_scores) / len(overall_scores)) ** 0.5
            
            stats[model_id] = ModelStats(
                model_id=model_id,
                total_questions=len(model_results),
                avg_overall=sum(overall_scores) / len(overall_scores),
                std_overall=std_overall,
                avg_sql=sum(sql_scores) / len(sql_scores),
                avg_table_column=sum(table_scores) / len(table_scores),
                avg_methodology=sum(method_scores) / len(method_scores),
                avg_latency_ms=sum(latencies) / len(latencies),
                error_rate=sum(1 for r in model_results if r.get('errors')) / len(model_results),
                by_category=category_stats
            )
        
        return stats
    
    def get_category_analysis(self) -> Dict[str, Dict]:
        """Analyze performance by question category."""
        if not self.results:
            return {}
        
        by_category: Dict[str, List] = {}
        for r in self.results:
            cat = r.get('category', 'unknown')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(r)
        
        analysis = {}
        for cat, cat_results in by_category.items():
            overall = [r['overall_score'] for r in cat_results]
            sql = [r['sql_score'] for r in cat_results]
            table = [r['table_column_score'] for r in cat_results]
            method = [r['methodology_score'] for r in cat_results]
            
            analysis[cat] = {
                'count': len(cat_results),
                'avg_overall': sum(overall) / len(overall),
                'avg_sql': sum(sql) / len(sql),
                'avg_table_column': sum(table) / len(table),
                'avg_methodology': sum(method) / len(method),
                'min_overall': min(overall),
                'max_overall': max(overall)
            }
        
        return analysis
    
    def get_best_worst_questions(self, n: int = 5) -> Dict[str, List]:
        """Get best and worst performing questions."""
        if not self.results:
            return {'best': [], 'worst': []}
        
        # Group by question
        by_question: Dict[str, List] = {}
        for r in self.results:
            qid = r.get('question_id', 'unknown')
            if qid not in by_question:
                by_question[qid] = {
                    'question_text': r.get('question_text', ''),
                    'category': r.get('category', ''),
                    'scores': []
                }
            by_question[qid]['scores'].append(r['overall_score'])
        
        # Calculate average score per question
        question_avgs = []
        for qid, data in by_question.items():
            avg = sum(data['scores']) / len(data['scores'])
            question_avgs.append({
                'question_id': qid,
                'question_text': data['question_text'][:100],
                'category': data['category'],
                'avg_score': avg,
                'num_evaluations': len(data['scores'])
            })
        
        # Sort by score
        sorted_questions = sorted(question_avgs, key=lambda x: x['avg_score'], reverse=True)
        
        return {
            'best': sorted_questions[:n],
            'worst': sorted_questions[-n:][::-1]
        }
    
    def get_metric_correlations(self) -> Dict[str, float]:
        """Calculate correlations between different metrics."""
        if not self.results or not HAS_NUMPY:
            return {}
        
        sql = np.array([r['sql_score'] for r in self.results])
        table = np.array([r['table_column_score'] for r in self.results])
        method = np.array([r['methodology_score'] for r in self.results])
        overall = np.array([r['overall_score'] for r in self.results])
        
        correlations = {
            'sql_vs_table': float(np.corrcoef(sql, table)[0, 1]),
            'sql_vs_methodology': float(np.corrcoef(sql, method)[0, 1]),
            'table_vs_methodology': float(np.corrcoef(table, method)[0, 1]),
            'sql_vs_overall': float(np.corrcoef(sql, overall)[0, 1]),
            'table_vs_overall': float(np.corrcoef(table, overall)[0, 1]),
            'methodology_vs_overall': float(np.corrcoef(method, overall)[0, 1])
        }
        
        return correlations
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate a text report of the analysis."""
        lines = []
        lines.append("=" * 60)
        lines.append("LLM BENCHMARK ANALYSIS REPORT")
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("=" * 60)
        
        # Model comparison
        lines.append("\n## MODEL COMPARISON")
        lines.append("-" * 40)
        
        model_stats = self.get_model_comparison()
        for model_id, stats in sorted(model_stats.items(), key=lambda x: x[1].avg_overall, reverse=True):
            lines.append(f"\n{model_id}:")
            lines.append(f"  Overall Score: {stats.avg_overall:.1f} (±{stats.std_overall:.1f})")
            lines.append(f"  SQL Score: {stats.avg_sql:.1f}")
            lines.append(f"  Table/Column Score: {stats.avg_table_column:.1f}")
            lines.append(f"  Methodology Score: {stats.avg_methodology:.1f}")
            lines.append(f"  Avg Latency: {stats.avg_latency_ms:.0f}ms")
            lines.append(f"  Error Rate: {stats.error_rate*100:.1f}%")
        
        # Category analysis
        lines.append("\n\n## CATEGORY ANALYSIS")
        lines.append("-" * 40)
        
        cat_analysis = self.get_category_analysis()
        for cat, stats in cat_analysis.items():
            lines.append(f"\n{cat} (n={stats['count']}):")
            lines.append(f"  Avg Overall: {stats['avg_overall']:.1f} [{stats['min_overall']:.1f} - {stats['max_overall']:.1f}]")
            lines.append(f"  Avg SQL: {stats['avg_sql']:.1f}")
            lines.append(f"  Avg Table/Column: {stats['avg_table_column']:.1f}")
            lines.append(f"  Avg Methodology: {stats['avg_methodology']:.1f}")
        
        # Best/Worst questions
        lines.append("\n\n## QUESTION ANALYSIS")
        lines.append("-" * 40)
        
        bw = self.get_best_worst_questions(5)
        
        lines.append("\nTop 5 Best Performing Questions:")
        for i, q in enumerate(bw['best'], 1):
            lines.append(f"  {i}. [{q['category']}] {q['question_text'][:60]}... (Score: {q['avg_score']:.1f})")
        
        lines.append("\nTop 5 Worst Performing Questions:")
        for i, q in enumerate(bw['worst'], 1):
            lines.append(f"  {i}. [{q['category']}] {q['question_text'][:60]}... (Score: {q['avg_score']:.1f})")
        
        # Correlations
        if HAS_NUMPY:
            lines.append("\n\n## METRIC CORRELATIONS")
            lines.append("-" * 40)
            
            correlations = self.get_metric_correlations()
            for metric_pair, corr in correlations.items():
                lines.append(f"  {metric_pair}: {corr:.3f}")
        
        # Recommendations
        lines.append("\n\n## RECOMMENDATIONS")
        lines.append("-" * 40)
        
        overall_avg = sum(r['overall_score'] for r in self.results) / len(self.results) if self.results else 0
        
        if overall_avg >= 70:
            lines.append("✓ Models show good domain understanding")
            lines.append("✓ Prompt engineering may be sufficient for improvement")
        elif overall_avg >= 40:
            lines.append("⚠ Models show moderate understanding")
            lines.append("⚠ Consider domain-specific examples in prompts")
            lines.append("⚠ Fine-tuning may improve results")
        else:
            lines.append("✗ Models struggle with domain tasks")
            lines.append("✗ Fine-tuning is recommended")
            lines.append("✗ Consider smaller, focused models")
        
        lines.append("\n" + "=" * 60)
        
        report = "\n".join(lines)
        
        # Save if output file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def to_dataframe(self):
        """Convert results to pandas DataFrame."""
        if not HAS_PANDAS:
            raise ImportError("pandas not installed")
        
        return pd.DataFrame(self.results)

