#!/usr/bin/env python3
"""
Enhanced vs Baseline vs Ground Truth Comparison
Compares three approaches:
1. Enhanced Prompts (methodology + table selection enhanced, SQL baseline)
2. Baseline Prompts (original benchmark prompts)
3. Ground Truth (from generated_questions.json)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "llm_benchmarking"))
sys.path.insert(0, str(Path(__file__).parent.parent / "prompt_engineering"))

from prompt_engineering.llama4_maverick_optimizer import EnhancedPromptEngineer
from llm_benchmarking.benchmarks.question_loader import QuestionLoader
from llm_benchmarking.evaluators.sql_comparator import SQLComparator
from llm_benchmarking.evaluators.table_column_matcher import TableColumnMatcher
from llm_benchmarking.evaluators.gemini_similarity import GeminiSimilarityEvaluator


class ThreeWayComparison:
    """Compare Enhanced, Baseline, and Ground Truth."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.results_dir = self.base_dir / "results"
        self.visualizations_dir = self.results_dir / "visualizations"
        self.results_dir.mkdir(exist_ok=True)
        self.visualizations_dir.mkdir(exist_ok=True)
        
        # Load data sources
        self.baseline_results_file = Path(__file__).parent.parent / "llm_benchmarking" / "results" / "metrics" / "all_results.json"
        self.questions_file = Path(__file__).parent.parent / "question_generator" / "generated_questions.json"
        self.enhanced_results_file = Path(__file__).parent.parent / "prompt_engineering" / "results" / "baseline_vs_enhanced_comparison.json"
        
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
        self.enhanced_results = self._load_enhanced_results()
    
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
        
        print(f"✓ Loaded {len(maverick_results)} baseline results")
        return maverick_results
    
    def _load_questions(self) -> Dict:
        """Load questions with ground truth."""
        if not self.questions_file.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_file}")
        
        with open(self.questions_file, 'r') as f:
            data = json.load(f)
        
        questions = {}
        for category in data.get('questions', {}):
            for q in data['questions'][category]:
                questions[q['id']] = q
        
        print(f"✓ Loaded {len(questions)} questions with ground truth")
        return questions
    
    def _load_enhanced_results(self) -> Dict:
        """Load enhanced prompt results."""
        if not self.enhanced_results_file.exists():
            print(f"Warning: Enhanced results not found: {self.enhanced_results_file}")
            return {}
        
        with open(self.enhanced_results_file, 'r') as f:
            data = json.load(f)
        
        enhanced_results = {}
        for result in data.get('detailed_results', []):
            q_id = result.get('question_id', '')
            enhanced_results[q_id] = result.get('enhanced', {})
        
        print(f"✓ Loaded {len(enhanced_results)} enhanced results")
        return enhanced_results
    
    def evaluate_against_ground_truth(self, question: Dict) -> Dict:
        """Evaluate ground truth scores (perfect scores)."""
        return {
            'sql_score': 100.0,  # Ground truth SQL is perfect
            'table_column_score': 100.0,  # Ground truth tables/columns are perfect
            'methodology_score': 100.0,  # Ground truth methodology is perfect
            'overall_score': 100.0
        }
    
    def compare_question(self, question_id: str) -> Optional[Dict]:
        """Compare all three approaches for a single question."""
        question = self.questions.get(question_id)
        baseline = self.baseline_results.get(question_id)
        enhanced = self.enhanced_results.get(question_id)
        
        if not question:
            return None
        
        # Ground truth (perfect scores)
        ground_truth = self.evaluate_against_ground_truth(question)
        
        # Baseline scores
        baseline_scores = {
            'sql_score': baseline.get('sql_score', 0.0) if baseline else 0.0,
            'table_column_score': baseline.get('table_column_score', 0.0) if baseline else 0.0,
            'methodology_score': baseline.get('methodology_score', 0.0) if baseline else 0.0,
            'overall_score': baseline.get('overall_score', 0.0) if baseline else 0.0
        }
        
        # Enhanced scores
        enhanced_scores = {
            'sql_score': enhanced.get('sql_score', 0.0) if enhanced else 0.0,
            'table_column_score': enhanced.get('table_column_score', 0.0) if enhanced else 0.0,
            'methodology_score': enhanced.get('methodology_score', 0.0) if enhanced else 0.0,
            'overall_score': enhanced.get('overall_score', 0.0) if enhanced else 0.0
        }
        
        return {
            'question_id': question_id,
            'question_text': question.get('question', ''),
            'category': question.get('category', ''),
            'ground_truth': ground_truth,
            'baseline': baseline_scores,
            'enhanced': enhanced_scores,
            'baseline_gap': {
                'sql': ground_truth['sql_score'] - baseline_scores['sql_score'],
                'table': ground_truth['table_column_score'] - baseline_scores['table_column_score'],
                'methodology': ground_truth['methodology_score'] - baseline_scores['methodology_score'],
                'overall': ground_truth['overall_score'] - baseline_scores['overall_score']
            },
            'enhanced_gap': {
                'sql': ground_truth['sql_score'] - enhanced_scores['sql_score'],
                'table': ground_truth['table_column_score'] - enhanced_scores['table_column_score'],
                'methodology': ground_truth['methodology_score'] - enhanced_scores['methodology_score'],
                'overall': ground_truth['overall_score'] - enhanced_scores['overall_score']
            },
            'enhanced_improvement': {
                'sql': enhanced_scores['sql_score'] - baseline_scores['sql_score'],
                'table': enhanced_scores['table_column_score'] - baseline_scores['table_column_score'],
                'methodology': enhanced_scores['methodology_score'] - baseline_scores['methodology_score'],
                'overall': enhanced_scores['overall_score'] - baseline_scores['overall_score']
            }
        }
    
    def compare_all(self, question_ids: Optional[List[str]] = None, limit: int = 30) -> List[Dict]:
        """Compare all three approaches for multiple questions."""
        if question_ids is None:
            # Only compare questions that have BOTH baseline and enhanced results
            baseline_ids = set(self.baseline_results.keys())
            enhanced_ids = set(self.enhanced_results.keys())
            common_ids = list(baseline_ids & enhanced_ids)
            
            if not common_ids:
                print("Warning: No questions found with both baseline and enhanced results.")
                print(f"Baseline questions: {len(baseline_ids)}")
                print(f"Enhanced questions: {len(enhanced_ids)}")
                return []
            
            question_ids = common_ids[:limit] if limit else common_ids
            print(f"\nFound {len(common_ids)} questions with both baseline and enhanced results")
            print(f"Comparing {len(question_ids)} questions...")
        else:
            # Filter to only questions with both results
            baseline_ids = set(self.baseline_results.keys())
            enhanced_ids = set(self.enhanced_results.keys())
            question_ids = [qid for qid in question_ids if qid in baseline_ids and qid in enhanced_ids]
            print(f"\nComparing {len(question_ids)} questions (filtered to those with both results)...")
        
        print("="*70)
        
        results = []
        for i, q_id in enumerate(question_ids, 1):
            comparison = self.compare_question(q_id)
            if comparison:
                results.append(comparison)
                
                # Show progress
                if i % 5 == 0 or i == len(question_ids):
                    baseline_score = comparison['baseline']['overall_score']
                    enhanced_score = comparison['enhanced']['overall_score']
                    improvement = comparison['enhanced_improvement']['overall']
                    
                    improvement_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
                    color = "✓" if improvement > 0 else "✗"
                    
                    print(f"[{i}/{len(question_ids)}] {q_id}: "
                          f"Baseline {baseline_score:.1f}% | "
                          f"Enhanced {enhanced_score:.1f}% | "
                          f"{color} {improvement_str}")
        
        return results
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """Generate comprehensive comparison report."""
        if not results:
            return {}
        
        # Calculate averages
        ground_truth_avg = {
            'sql': 100.0,
            'table': 100.0,
            'methodology': 100.0,
            'overall': 100.0
        }
        
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
        
        # Calculate gaps from ground truth
        baseline_gap_avg = {
            'sql': ground_truth_avg['sql'] - baseline_avg['sql'],
            'table': ground_truth_avg['table'] - baseline_avg['table'],
            'methodology': ground_truth_avg['methodology'] - baseline_avg['methodology'],
            'overall': ground_truth_avg['overall'] - baseline_avg['overall']
        }
        
        enhanced_gap_avg = {
            'sql': ground_truth_avg['sql'] - enhanced_avg['sql'],
            'table': ground_truth_avg['table'] - enhanced_avg['table'],
            'methodology': ground_truth_avg['methodology'] - enhanced_avg['methodology'],
            'overall': ground_truth_avg['overall'] - enhanced_avg['overall']
        }
        
        # Calculate improvements
        improvements_avg = {
            'sql': enhanced_avg['sql'] - baseline_avg['sql'],
            'table': enhanced_avg['table'] - baseline_avg['table'],
            'methodology': enhanced_avg['methodology'] - baseline_avg['methodology'],
            'overall': enhanced_avg['overall'] - baseline_avg['overall']
        }
        
        # Count improvements
        improved_count = sum(1 for r in results if r['enhanced_improvement']['overall'] > 0)
        degraded_count = sum(1 for r in results if r['enhanced_improvement']['overall'] < 0)
        same_count = len(results) - improved_count - degraded_count
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_questions': len(results),
            'ground_truth_averages': ground_truth_avg,
            'baseline_averages': baseline_avg,
            'enhanced_averages': enhanced_avg,
            'baseline_gap_from_ground_truth': baseline_gap_avg,
            'enhanced_gap_from_ground_truth': enhanced_gap_avg,
            'enhanced_improvements': improvements_avg,
            'improved': improved_count,
            'degraded': degraded_count,
            'same': same_count,
            'improvement_rate': (improved_count / len(results)) * 100 if results else 0
        }
    
    def save_results(self, results: List[Dict], report: Dict):
        """Save comparison results."""
        # Save JSON
        output_file = self.results_dir / "three_way_comparison.json"
        data = {
            'report': report,
            'detailed_results': results
        }
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Results saved to: {output_file}")
        
        # Save CSV
        csv_file = self.results_dir / "three_way_comparison.csv"
        df_data = []
        for r in results:
            df_data.append({
                'question_id': r['question_id'],
                'category': r.get('category', ''),
                'ground_truth_overall': r['ground_truth']['overall_score'],
                'baseline_overall': r['baseline']['overall_score'],
                'enhanced_overall': r['enhanced']['overall_score'],
                'baseline_gap': r['baseline_gap']['overall'],
                'enhanced_gap': r['enhanced_gap']['overall'],
                'enhanced_improvement': r['enhanced_improvement']['overall'],
                'ground_truth_sql': r['ground_truth']['sql_score'],
                'baseline_sql': r['baseline']['sql_score'],
                'enhanced_sql': r['enhanced']['sql_score'],
                'ground_truth_tables': r['ground_truth']['table_column_score'],
                'baseline_tables': r['baseline']['table_column_score'],
                'enhanced_tables': r['enhanced']['table_column_score'],
                'ground_truth_methodology': r['ground_truth']['methodology_score'],
                'baseline_methodology': r['baseline']['methodology_score'],
                'enhanced_methodology': r['enhanced']['methodology_score']
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(csv_file, index=False)
        print(f"✓ CSV saved to: {csv_file}")
    
    def generate_visualizations(self, results: List[Dict], report: Dict):
        """Generate comprehensive visualizations."""
        print("\n" + "="*70)
        print("Generating Visualizations...")
        print("="*70)
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (14, 8)
        plt.rcParams['font.size'] = 10
        
        # 1. Three-way comparison bar chart
        self._plot_three_way_comparison(report)
        
        # 2. Component-wise comparison
        self._plot_component_comparison(report)
        
        # 3. Gap analysis (distance from ground truth)
        self._plot_gap_analysis(report)
        
        # 4. Improvement distribution
        self._plot_improvement_distribution(results)
        
        # 5. Radar chart
        self._plot_radar_chart(report)
        
        # 6. Category-wise comparison
        self._plot_category_comparison(results)
        
        print(f"\n✓ All visualizations saved to: {self.visualizations_dir}")
    
    def _plot_three_way_comparison(self, report: Dict):
        """Bar chart comparing all three approaches."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        components = ['SQL', 'Tables/Columns', 'Methodology', 'Overall']
        ground_truth_values = [100.0, 100.0, 100.0, 100.0]
        baseline_values = [
            report['baseline_averages']['sql'],
            report['baseline_averages']['table'],
            report['baseline_averages']['methodology'],
            report['baseline_averages']['overall']
        ]
        enhanced_values = [
            report['enhanced_averages']['sql'],
            report['enhanced_averages']['table'],
            report['enhanced_averages']['methodology'],
            report['enhanced_averages']['overall']
        ]
        
        x = np.arange(len(components))
        width = 0.25
        
        bars1 = ax.bar(x - width, ground_truth_values, width, label='Ground Truth', 
                      color='#27ae60', alpha=0.9)
        bars2 = ax.bar(x, baseline_values, width, label='Baseline', 
                      color='#3498db', alpha=0.8)
        bars3 = ax.bar(x + width, enhanced_values, width, label='Enhanced', 
                      color='#e74c3c', alpha=0.8)
        
        # Add value labels
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Components', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score (%)', fontsize=12, fontweight='bold')
        ax.set_title('Three-Way Comparison: Ground Truth vs Baseline vs Enhanced\n(Perfect Score = 100%)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(components)
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 105])
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'three_way_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ Saved: three_way_comparison.png")
    
    def _plot_component_comparison(self, report: Dict):
        """Component-wise detailed comparison."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()
        
        components = [
            ('SQL', 'sql'),
            ('Tables/Columns', 'table'),
            ('Methodology', 'methodology'),
            ('Overall', 'overall')
        ]
        
        for idx, (comp_name, comp_key) in enumerate(components):
            ax = axes[idx]
            
            ground_truth = 100.0
            baseline = report['baseline_averages'][comp_key]
            enhanced = report['enhanced_averages'][comp_key]
            
            categories = ['Ground Truth', 'Baseline', 'Enhanced']
            values = [ground_truth, baseline, enhanced]
            colors = ['#27ae60', '#3498db', '#e74c3c']
            
            bars = ax.bar(categories, values, color=colors, alpha=0.8)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            # Add gap annotations
            baseline_gap = ground_truth - baseline
            enhanced_gap = ground_truth - enhanced
            improvement = enhanced - baseline
            
            ax.text(1, baseline + 2, f'Gap: -{baseline_gap:.1f}%', 
                   ha='center', fontsize=9, color='#3498db', fontweight='bold')
            ax.text(2, enhanced + 2, f'Gap: -{enhanced_gap:.1f}%', 
                   ha='center', fontsize=9, color='#e74c3c', fontweight='bold')
            
            if improvement != 0:
                color = '#27ae60' if improvement > 0 else '#e74c3c'
                ax.text(1.5, max(baseline, enhanced) + 5, 
                       f'{improvement:+.1f}%', 
                       ha='center', fontsize=10, color=color, fontweight='bold')
            
            ax.set_ylabel('Score (%)', fontsize=10, fontweight='bold')
            ax.set_title(f'{comp_name} Comparison', fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            ax.set_ylim([0, 105])
        
        plt.suptitle('Component-wise Comparison: Ground Truth vs Baseline vs Enhanced', 
                    fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'component_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ Saved: component_comparison.png")
    
    def _plot_gap_analysis(self, report: Dict):
        """Gap analysis - distance from ground truth."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        components = ['SQL', 'Tables/Columns', 'Methodology', 'Overall']
        baseline_gaps = [
            report['baseline_gap_from_ground_truth']['sql'],
            report['baseline_gap_from_ground_truth']['table'],
            report['baseline_gap_from_ground_truth']['methodology'],
            report['baseline_gap_from_ground_truth']['overall']
        ]
        enhanced_gaps = [
            report['enhanced_gap_from_ground_truth']['sql'],
            report['enhanced_gap_from_ground_truth']['table'],
            report['enhanced_gap_from_ground_truth']['methodology'],
            report['enhanced_gap_from_ground_truth']['overall']
        ]
        
        x = np.arange(len(components))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, baseline_gaps, width, label='Baseline Gap', 
                      color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, enhanced_gaps, width, label='Enhanced Gap', 
                      color='#e74c3c', alpha=0.8)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Components', fontsize=12, fontweight='bold')
        ax.set_ylabel('Gap from Ground Truth (%)', fontsize=12, fontweight='bold')
        ax.set_title('Gap Analysis: Distance from Perfect Score (100%)\n(Lower is Better)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(components)
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'gap_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ Saved: gap_analysis.png")
    
    def _plot_improvement_distribution(self, results: List[Dict]):
        """Distribution of improvements."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        components = [
            ('SQL', 'sql'),
            ('Tables/Columns', 'table'),
            ('Methodology', 'methodology'),
            ('Overall', 'overall')
        ]
        
        for idx, (comp_name, comp_key) in enumerate(components):
            ax = axes[idx]
            
            improvements = [r['enhanced_improvement'][comp_key] for r in results]
            
            # Create histogram
            ax.hist(improvements, bins=20, color='#3498db', alpha=0.7, edgecolor='black')
            ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No Change')
            ax.axvline(x=np.mean(improvements), color='green', linestyle='--', linewidth=2, 
                      label=f'Mean: {np.mean(improvements):.1f}%')
            
            ax.set_xlabel('Improvement (%)', fontsize=10, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=10, fontweight='bold')
            ax.set_title(f'{comp_name} Improvement Distribution', fontsize=11, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(axis='y', alpha=0.3)
        
        plt.suptitle('Improvement Distribution: Enhanced vs Baseline', 
                    fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'improvement_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ Saved: improvement_distribution.png")
    
    def _plot_radar_chart(self, report: Dict):
        """Radar chart comparing all three approaches."""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        categories = ['SQL', 'Tables', 'Methodology', 'Overall']
        
        ground_truth_values = [100.0, 100.0, 100.0, 100.0]
        baseline_values = [
            report['baseline_averages']['sql'],
            report['baseline_averages']['table'],
            report['baseline_averages']['methodology'],
            report['baseline_averages']['overall']
        ]
        enhanced_values = [
            report['enhanced_averages']['sql'],
            report['enhanced_averages']['table'],
            report['enhanced_averages']['methodology'],
            report['enhanced_averages']['overall']
        ]
        
        # Compute angles
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        ground_truth_values += ground_truth_values[:1]
        baseline_values += baseline_values[:1]
        enhanced_values += enhanced_values[:1]
        angles += angles[:1]
        
        # Plot
        ax.plot(angles, ground_truth_values, 'o-', linewidth=3, label='Ground Truth', 
               color='#27ae60', alpha=0.9)
        ax.fill(angles, ground_truth_values, alpha=0.25, color='#27ae60')
        
        ax.plot(angles, baseline_values, 'o-', linewidth=2, label='Baseline', 
               color='#3498db', alpha=0.8)
        ax.fill(angles, baseline_values, alpha=0.25, color='#3498db')
        
        ax.plot(angles, enhanced_values, 'o-', linewidth=2, label='Enhanced', 
               color='#e74c3c', alpha=0.8)
        ax.fill(angles, enhanced_values, alpha=0.25, color='#e74c3c')
        
        # Customize
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
        ax.grid(True, alpha=0.3)
        
        ax.set_title('Performance Radar Chart\nGround Truth vs Baseline vs Enhanced', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'radar_chart.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ Saved: radar_chart.png")
    
    def _plot_category_comparison(self, results: List[Dict]):
        """Compare performance by category."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Group by category
        category_data = defaultdict(lambda: {'baseline': [], 'enhanced': []})
        for r in results:
            cat = r.get('category', 'Unknown')
            category_data[cat]['baseline'].append(r['baseline']['overall_score'])
            category_data[cat]['enhanced'].append(r['enhanced']['overall_score'])
        
        categories = sorted(category_data.keys())
        baseline_avg = [np.mean(category_data[cat]['baseline']) for cat in categories]
        enhanced_avg = [np.mean(category_data[cat]['enhanced']) for cat in categories]
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, baseline_avg, width, label='Baseline', 
                      color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, enhanced_avg, width, label='Enhanced', 
                      color='#e74c3c', alpha=0.8)
        
        # Add ground truth line
        ax.axhline(y=100, color='#27ae60', linestyle='--', linewidth=2, 
                  label='Ground Truth (100%)', alpha=0.7)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Category', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Score (%)', fontsize=12, fontweight='bold')
        ax.set_title('Performance by Category\nBaseline vs Enhanced (Ground Truth = 100%)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 105])
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'category_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ Saved: category_comparison.png")
    
    def generate_text_report(self, report: Dict, results: List[Dict]) -> str:
        """Generate text report."""
        report_text = f"""
{'='*70}
THREE-WAY COMPARISON REPORT
Enhanced vs Baseline vs Ground Truth
{'='*70}

Generated: {report['timestamp']}
Total Questions Analyzed: {report['total_questions']}

{'='*70}
OVERALL PERFORMANCE SUMMARY
{'='*70}

Ground Truth (Perfect Score):
  SQL:            {report['ground_truth_averages']['sql']:.1f}%
  Tables/Columns: {report['ground_truth_averages']['table']:.1f}%
  Methodology:    {report['ground_truth_averages']['methodology']:.1f}%
  Overall:        {report['ground_truth_averages']['overall']:.1f}%

Baseline Performance:
  SQL:            {report['baseline_averages']['sql']:.1f}%
  Tables/Columns: {report['baseline_averages']['table']:.1f}%
  Methodology:    {report['baseline_averages']['methodology']:.1f}%
  Overall:        {report['baseline_averages']['overall']:.1f}%

Enhanced Performance:
  SQL:            {report['enhanced_averages']['sql']:.1f}%
  Tables/Columns: {report['enhanced_averages']['table']:.1f}%
  Methodology:    {report['enhanced_averages']['methodology']:.1f}%
  Overall:        {report['enhanced_averages']['overall']:.1f}%

{'='*70}
GAP ANALYSIS (Distance from Ground Truth)
{'='*70}

Baseline Gap from Ground Truth:
  SQL:            {report['baseline_gap_from_ground_truth']['sql']:.1f}%
  Tables/Columns: {report['baseline_gap_from_ground_truth']['table']:.1f}%
  Methodology:    {report['baseline_gap_from_ground_truth']['methodology']:.1f}%
  Overall:        {report['baseline_gap_from_ground_truth']['overall']:.1f}%

Enhanced Gap from Ground Truth:
  SQL:            {report['enhanced_gap_from_ground_truth']['sql']:.1f}%
  Tables/Columns: {report['enhanced_gap_from_ground_truth']['table']:.1f}%
  Methodology:    {report['enhanced_gap_from_ground_truth']['methodology']:.1f}%
  Overall:        {report['enhanced_gap_from_ground_truth']['overall']:.1f}%

{'='*70}
ENHANCED IMPROVEMENTS (vs Baseline)
{'='*70}

  SQL:            {report['enhanced_improvements']['sql']:+.1f}%
  Tables/Columns: {report['enhanced_improvements']['table']:+.1f}%
  Methodology:    {report['enhanced_improvements']['methodology']:+.1f}%
  Overall:        {report['enhanced_improvements']['overall']:+.1f}%

Improvement Rate: {report['improvement_rate']:.1f}% ({report['improved']} questions improved)
Degraded: {report['degraded']} questions
Same: {report['same']} questions

{'='*70}
KEY INSIGHTS
{'='*70}

1. Enhanced prompts show {'improvement' if report['enhanced_improvements']['overall'] > 0 else 'degradation'} in overall performance
   compared to baseline ({report['enhanced_improvements']['overall']:+.1f}%).

2. The largest improvement is in {'Methodology' if report['enhanced_improvements']['methodology'] == max(report['enhanced_improvements'].values()) else 'Tables/Columns'} 
   ({report['enhanced_improvements']['methodology'] if report['enhanced_improvements']['methodology'] == max(report['enhanced_improvements'].values()) else report['enhanced_improvements']['table']:+.1f}%).

3. Enhanced prompts reduce the gap from ground truth by 
   {report['baseline_gap_from_ground_truth']['overall'] - report['enhanced_gap_from_ground_truth']['overall']:.1f}% 
   compared to baseline.

4. {'Enhanced prompts' if report['enhanced_gap_from_ground_truth']['overall'] < report['baseline_gap_from_ground_truth']['overall'] else 'Baseline prompts'} 
   are closer to ground truth performance.

{'='*70}
"""
        return report_text
    
    def save_report(self, report_text: str):
        """Save text report."""
        report_file = self.results_dir / "comparison_report.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)
        print(f"✓ Report saved to: {report_file}")


def main():
    """Main comparison function."""
    print("="*70)
    print("Three-Way Comparison: Enhanced vs Baseline vs Ground Truth")
    print("="*70)
    
    comparator = ThreeWayComparison()
    
    # Compare questions (use all available baseline results)
    question_ids = list(comparator.baseline_results.keys())
    
    print(f"\nSelected {len(question_ids)} questions for comparison")
    
    # Run comparison
    results = comparator.compare_all(question_ids=question_ids)
    
    if results:
        # Generate report
        report = comparator.generate_report(results)
        
        # Display summary
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        print(f"\nGround Truth: 100.0% (Perfect Score)")
        print(f"\nBaseline Average: {report['baseline_averages']['overall']:.1f}%")
        print(f"Enhanced Average: {report['enhanced_averages']['overall']:.1f}%")
        print(f"Improvement: {report['enhanced_improvements']['overall']:+.1f}%")
        print(f"\nGap from Ground Truth:")
        print(f"  Baseline: {report['baseline_gap_from_ground_truth']['overall']:.1f}%")
        print(f"  Enhanced: {report['enhanced_gap_from_ground_truth']['overall']:.1f}%")
        print(f"\nComponent Improvements:")
        print(f"  SQL: {report['enhanced_improvements']['sql']:+.1f}%")
        print(f"  Tables/Columns: {report['enhanced_improvements']['table']:+.1f}%")
        print(f"  Methodology: {report['enhanced_improvements']['methodology']:+.1f}%")
        print(f"\nResults:")
        print(f"  Improved: {report['improved']} ({report['improvement_rate']:.1f}%)")
        print(f"  Degraded: {report['degraded']}")
        print(f"  Same: {report['same']}")
        
        # Save results
        comparator.save_results(results, report)
        
        # Generate visualizations
        comparator.generate_visualizations(results, report)
        
        # Generate and save text report
        report_text = comparator.generate_text_report(report, results)
        comparator.save_report(report_text)
        
        print("\n" + "="*70)
        print("✓ Comparison Complete!")
        print("="*70)
    else:
        print("\nNo results to compare")


if __name__ == "__main__":
    main()

