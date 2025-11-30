#!/usr/bin/env python3
"""
Visualization for Baseline vs Enhanced Prompt Comparison
Generates charts comparing baseline and enhanced prompt performance
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

class ComparisonVisualizer:
    """Generate visualizations for baseline vs enhanced comparison."""
    
    def __init__(self, results_file: Path = None):
        self.base_dir = Path(__file__).parent
        self.results_dir = self.base_dir / "results"
        self.visualizations_dir = self.results_dir / "visualizations"
        self.visualizations_dir.mkdir(exist_ok=True)
        
        if results_file is None:
            results_file = self.results_dir / "baseline_vs_enhanced_comparison.json"
        
        self.results_file = results_file
        self.data = self._load_data()
        self.df = self._create_dataframe()
    
    def _load_data(self) -> Dict:
        """Load comparison results."""
        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_file}")
        
        with open(self.results_file, 'r') as f:
            return json.load(f)
    
    def _create_dataframe(self) -> pd.DataFrame:
        """Create pandas DataFrame from results."""
        results = self.data.get('detailed_results', [])
        
        df_data = []
        for r in results:
            df_data.append({
                'question_id': r['question_id'],
                'category': r.get('category', 'Unknown'),
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
        
        return pd.DataFrame(df_data)
    
    def plot_overall_comparison(self):
        """Bar chart comparing overall baseline vs enhanced scores."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Prepare data
        questions = self.df['question_id'].values
        baseline_scores = self.df['baseline_overall'].values
        enhanced_scores = self.df['enhanced_overall'].values
        
        x = np.arange(len(questions))
        width = 0.35
        
        # Create bars
        bars1 = ax.bar(x - width/2, baseline_scores, width, label='Baseline', 
                       color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, enhanced_scores, width, label='Enhanced', 
                       color='#e74c3c', alpha=0.8)
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=8)
        
        # Customize
        ax.set_xlabel('Questions', fontsize=12, fontweight='bold')
        ax.set_ylabel('Overall Score (%)', fontsize=12, fontweight='bold')
        ax.set_title('Baseline vs Enhanced Prompt Performance\nOverall Score Comparison', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(questions, rotation=45, ha='right')
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 105])
        
        # Add average lines
        baseline_avg = self.df['baseline_overall'].mean()
        enhanced_avg = self.df['enhanced_overall'].mean()
        ax.axhline(y=baseline_avg, color='#3498db', linestyle='--', alpha=0.5, linewidth=2)
        ax.axhline(y=enhanced_avg, color='#e74c3c', linestyle='--', alpha=0.5, linewidth=2)
        ax.text(len(questions)-1, baseline_avg+2, f'Baseline Avg: {baseline_avg:.1f}%', 
               color='#3498db', fontsize=9, fontweight='bold')
        ax.text(len(questions)-1, enhanced_avg+2, f'Enhanced Avg: {enhanced_avg:.1f}%', 
               color='#e74c3c', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'overall_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: overall_comparison.png")
    
    def plot_component_comparison(self):
        """Compare SQL, Tables, and Methodology scores."""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        components = [
            ('SQL', 'baseline_sql', 'enhanced_sql', 'sql_improvement'),
            ('Tables/Columns', 'baseline_tables', 'enhanced_tables', 'tables_improvement'),
            ('Methodology', 'baseline_methodology', 'enhanced_methodology', 'methodology_improvement')
        ]
        
        for idx, (comp_name, baseline_col, enhanced_col, improvement_col) in enumerate(components):
            ax = axes[idx]
            
            baseline_scores = self.df[baseline_col].values
            enhanced_scores = self.df[enhanced_col].values
            improvements = self.df[improvement_col].values
            
            x = np.arange(len(self.df))
            width = 0.35
            
            bars1 = ax.bar(x - width/2, baseline_scores, width, label='Baseline', 
                          color='#3498db', alpha=0.8)
            bars2 = ax.bar(x + width/2, enhanced_scores, width, label='Enhanced', 
                          color='#e74c3c', alpha=0.8)
            
            # Color bars based on improvement
            for i, (bar1, bar2, imp) in enumerate(zip(bars1, bars2, improvements)):
                if imp > 0:
                    bar2.set_color('#27ae60')  # Green for improvement
                elif imp < 0:
                    bar2.set_color('#e74c3c')  # Red for degradation
            
            ax.set_xlabel('Questions', fontsize=10, fontweight='bold')
            ax.set_ylabel('Score (%)', fontsize=10, fontweight='bold')
            ax.set_title(f'{comp_name} Comparison', fontsize=12, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(self.df['question_id'], rotation=45, ha='right', fontsize=8)
            ax.legend(loc='upper right', fontsize=9)
            ax.grid(axis='y', alpha=0.3)
            ax.set_ylim([0, 105])
            
            # Add average
            baseline_avg = self.df[baseline_col].mean()
            enhanced_avg = self.df[enhanced_col].mean()
            ax.axhline(y=baseline_avg, color='#3498db', linestyle='--', alpha=0.5)
            ax.axhline(y=enhanced_avg, color='#e74c3c', linestyle='--', alpha=0.5)
            ax.text(len(self.df)-1, baseline_avg+3, f'B: {baseline_avg:.1f}%', 
                   color='#3498db', fontsize=8)
            ax.text(len(self.df)-1, enhanced_avg+3, f'E: {enhanced_avg:.1f}%', 
                   color='#e74c3c', fontsize=8)
        
        plt.suptitle('Component-wise Comparison: Baseline vs Enhanced', 
                    fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'component_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: component_comparison.png")
    
    def plot_improvement_heatmap(self):
        """Heatmap showing improvements/degradations."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Prepare data for heatmap
        heatmap_data = self.df[['sql_improvement', 'tables_improvement', 
                                'methodology_improvement', 'overall_improvement']].T
        heatmap_data.columns = self.df['question_id'].values
        heatmap_data.index = ['SQL', 'Tables/Columns', 'Methodology', 'Overall']
        
        # Create heatmap
        sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', 
                   center=0, vmin=-100, vmax=100, cbar_kws={'label': 'Improvement (%)'},
                   linewidths=0.5, linecolor='gray', ax=ax)
        
        ax.set_title('Improvement Heatmap: Enhanced vs Baseline\n(Green = Improvement, Red = Degradation)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Questions', fontsize=12, fontweight='bold')
        ax.set_ylabel('Components', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'improvement_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: improvement_heatmap.png")
    
    def plot_average_comparison(self):
        """Bar chart comparing average scores."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        report = self.data.get('report', {})
        baseline_avg = report.get('baseline_averages', {})
        enhanced_avg = report.get('enhanced_averages', {})
        
        components = ['sql', 'table', 'methodology', 'overall']
        component_labels = ['SQL', 'Tables/Columns', 'Methodology', 'Overall']
        
        baseline_values = [baseline_avg.get(c, 0) for c in components]
        enhanced_values = [enhanced_avg.get(c, 0) for c in components]
        
        x = np.arange(len(component_labels))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, baseline_values, width, label='Baseline', 
                      color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, enhanced_values, width, label='Enhanced', 
                      color='#e74c3c', alpha=0.8)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add improvement annotations
        improvements = report.get('average_improvements', {})
        for i, (comp, label) in enumerate(zip(components, component_labels)):
            imp = improvements.get(comp, 0)
            color = '#27ae60' if imp > 0 else '#e74c3c'
            ax.text(i, max(baseline_values[i], enhanced_values[i]) + 3,
                   f'{imp:+.1f}%', ha='center', fontsize=9, fontweight='bold', color=color)
        
        ax.set_xlabel('Components', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Score (%)', fontsize=12, fontweight='bold')
        ax.set_title('Average Performance Comparison\nBaseline vs Enhanced Prompts', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(component_labels)
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, max(max(baseline_values), max(enhanced_values)) * 1.2])
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'average_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: average_comparison.png")
    
    def plot_category_comparison(self):
        """Compare performance by category."""
        if 'category' not in self.df.columns:
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        category_data = self.df.groupby('category').agg({
            'baseline_overall': 'mean',
            'enhanced_overall': 'mean',
            'overall_improvement': 'mean'
        }).reset_index()
        
        categories = category_data['category'].values
        baseline_avg = category_data['baseline_overall'].values
        enhanced_avg = category_data['enhanced_overall'].values
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, baseline_avg, width, label='Baseline', 
                      color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, enhanced_avg, width, label='Enhanced', 
                      color='#e74c3c', alpha=0.8)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add improvement annotations
        for i, imp in enumerate(category_data['overall_improvement'].values):
            color = '#27ae60' if imp > 0 else '#e74c3c'
            ax.text(i, max(baseline_avg[i], enhanced_avg[i]) + 2,
                   f'{imp:+.1f}%', ha='center', fontsize=9, fontweight='bold', color=color)
        
        ax.set_xlabel('Category', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Score (%)', fontsize=12, fontweight='bold')
        ax.set_title('Performance by Category\nBaseline vs Enhanced', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend(loc='upper right', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, max(max(baseline_avg), max(enhanced_avg)) * 1.2])
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'category_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: category_comparison.png")
    
    def plot_improvement_distribution(self):
        """Box plot showing distribution of improvements."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        components = [
            ('SQL', 'sql_improvement'),
            ('Tables/Columns', 'tables_improvement'),
            ('Methodology', 'methodology_improvement'),
            ('Overall', 'overall_improvement')
        ]
        
        for idx, (comp_name, col) in enumerate(components):
            ax = axes[idx]
            
            improvements = self.df[col].values
            
            # Create box plot
            bp = ax.boxplot([improvements], patch_artist=True, widths=0.6)
            bp['boxes'][0].set_facecolor('#3498db')
            bp['boxes'][0].set_alpha(0.7)
            
            # Add mean line
            mean_val = improvements.mean()
            ax.axhline(y=mean_val, color='red', linestyle='--', linewidth=2, 
                      label=f'Mean: {mean_val:.1f}%')
            
            # Add scatter points
            ax.scatter([1] * len(improvements), improvements, alpha=0.5, 
                      color='black', s=30, zorder=3)
            
            ax.set_ylabel('Improvement (%)', fontsize=10, fontweight='bold')
            ax.set_title(f'{comp_name} Improvement Distribution', 
                        fontsize=11, fontweight='bold')
            ax.set_xticklabels([comp_name])
            ax.axhline(y=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
            ax.grid(axis='y', alpha=0.3)
            ax.legend(fontsize=8)
            
            # Add statistics
            median_val = np.median(improvements)
            q1 = np.percentile(improvements, 25)
            q3 = np.percentile(improvements, 75)
            stats_text = f'Median: {median_val:.1f}%\nQ1: {q1:.1f}%\nQ3: {q3:.1f}%'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=8, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle('Improvement Distribution Analysis', 
                    fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'improvement_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: improvement_distribution.png")
    
    def plot_radar_chart(self):
        """Radar chart comparing baseline vs enhanced."""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        report = self.data.get('report', {})
        baseline_avg = report.get('baseline_averages', {})
        enhanced_avg = report.get('enhanced_averages', {})
        
        categories = ['SQL', 'Tables', 'Methodology', 'Overall']
        baseline_values = [
            baseline_avg.get('sql', 0),
            baseline_avg.get('table', 0),
            baseline_avg.get('methodology', 0),
            baseline_avg.get('overall', 0)
        ]
        enhanced_values = [
            enhanced_avg.get('sql', 0),
            enhanced_avg.get('table', 0),
            enhanced_avg.get('methodology', 0),
            enhanced_avg.get('overall', 0)
        ]
        
        # Compute angles
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        baseline_values += baseline_values[:1]  # Complete the circle
        enhanced_values += enhanced_values[:1]
        angles += angles[:1]
        
        # Plot
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
        
        ax.set_title('Performance Radar Chart\nBaseline vs Enhanced', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
        
        plt.tight_layout()
        plt.savefig(self.visualizations_dir / 'radar_chart.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: radar_chart.png")
    
    def generate_all(self):
        """Generate all visualizations."""
        print("="*70)
        print("Generating Comparison Visualizations")
        print("="*70)
        print()
        
        try:
            self.plot_overall_comparison()
            self.plot_component_comparison()
            self.plot_improvement_heatmap()
            self.plot_average_comparison()
            self.plot_category_comparison()
            self.plot_improvement_distribution()
            self.plot_radar_chart()
            
            print()
            print("="*70)
            print(f"✓ All visualizations saved to: {self.visualizations_dir}")
            print("="*70)
            
        except Exception as e:
            print(f"Error generating visualizations: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main function."""
    visualizer = ComparisonVisualizer()
    visualizer.generate_all()


if __name__ == "__main__":
    main()

