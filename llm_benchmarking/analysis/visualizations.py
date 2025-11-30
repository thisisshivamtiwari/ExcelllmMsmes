#!/usr/bin/env python3
"""
Benchmark Visualizations
Creates charts and graphs for benchmark results
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    sns = None


class BenchmarkVisualizer:
    """Creates visualizations for benchmark results."""
    
    def __init__(self, results_dir: Optional[Path] = None, style: str = 'seaborn-v0_8-whitegrid'):
        self.results_dir = results_dir or Path(__file__).parent.parent / "results"
        self.viz_dir = self.results_dir / "visualizations"
        self.log_dir = self.results_dir / "logs"
        
        self.viz_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
        self.summary = {}
        
        # Set style if matplotlib available
        if HAS_MATPLOTLIB:
            try:
                plt.style.use(style)
            except:
                plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn' in plt.style.available else 'default')
        
        # Color palette
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'tertiary': '#F18F01',
            'success': '#C73E1D',
            'info': '#3B1F2B',
            'models': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B', '#6B4423']
        }
        
        # Log file for this session
        self.log_file = self.log_dir / f"visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    def _log(self, message: str):
        """Log message to file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
        
        print(message)
    
    def load_results(self, results_file: Optional[Path] = None) -> bool:
        """Load results from JSON file."""
        if results_file is None:
            results_file = self.results_dir / "metrics" / "all_results.json"
        
        if not results_file.exists():
            self._log(f"ERROR: Results file not found: {results_file}")
            return False
        
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.results = data.get('results', [])
        self.summary = data.get('summary', {})
        
        self._log(f"Loaded {len(self.results)} results from {results_file.name}")
        return True
    
    def _check_dependencies(self) -> bool:
        """Check if visualization dependencies are available."""
        if not HAS_MATPLOTLIB:
            self._log("WARNING: matplotlib not installed. Install with: pip install matplotlib")
            return False
        if not HAS_NUMPY:
            self._log("WARNING: numpy not installed. Install with: pip install numpy")
            return False
        return True
    
    def plot_model_comparison_bar(self, save: bool = True) -> Optional[str]:
        """Create bar chart comparing models across metrics."""
        if not self._check_dependencies():
            return None
        
        self._log("Generating model comparison bar chart...")
        
        model_data = self.summary.get('by_model', {})
        if not model_data:
            self._log("No model data available")
            return None
        
        models = list(model_data.keys())
        metrics = ['avg_overall', 'avg_sql', 'avg_table_column', 'avg_methodology']
        metric_labels = ['Overall', 'SQL', 'Table/Column', 'Methodology']
        
        x = np.arange(len(models))
        width = 0.2
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
            values = [model_data[m].get(metric, 0) for m in models]
            bars = ax.bar(x + i * width, values, width, label=label, color=self.colors['models'][i])
            # Add value labels
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{val:.1f}', ha='center', va='bottom', fontsize=8)
        
        ax.set_xlabel('Model')
        ax.set_ylabel('Score')
        ax.set_title('Model Performance Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels([m.split('/')[-1] for m in models], rotation=45, ha='right')
        ax.legend(loc='upper right')
        ax.set_ylim(0, 110)
        ax.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='Good threshold')
        ax.axhline(y=40, color='orange', linestyle='--', alpha=0.5, label='Fair threshold')
        
        plt.tight_layout()
        
        if save:
            filepath = self.viz_dir / "model_comparison_bar.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            self._log(f"Saved: {filepath}")
            plt.close()
            return str(filepath)
        
        plt.show()
        return None
    
    def plot_radar_chart(self, save: bool = True) -> Optional[str]:
        """Create radar chart for model comparison."""
        if not self._check_dependencies():
            return None
        
        self._log("Generating radar chart...")
        
        model_data = self.summary.get('by_model', {})
        if not model_data:
            self._log("No model data available")
            return None
        
        categories = ['SQL', 'Table/Column', 'Methodology', 'Quality', 'Speed']
        N = len(categories)
        
        # Create angles for radar chart
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Complete the circle
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        for i, (model_id, data) in enumerate(model_data.items()):
            # Normalize speed score (inverse of latency)
            max_latency = max(d['avg_latency_ms'] for d in model_data.values())
            speed_score = 100 * (1 - data['avg_latency_ms'] / max_latency) if max_latency > 0 else 50
            
            values = [
                data.get('avg_sql', 0),
                data.get('avg_table_column', 0),
                data.get('avg_methodology', 0),
                100 - data.get('error_rate', 0) * 100,  # Quality = 100 - error_rate
                speed_score
            ]
            values += values[:1]  # Complete the circle
            
            ax.plot(angles, values, 'o-', linewidth=2, 
                   label=model_id.split('/')[-1], color=self.colors['models'][i % len(self.colors['models'])])
            ax.fill(angles, values, alpha=0.1, color=self.colors['models'][i % len(self.colors['models'])])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.set_title('Model Performance Radar', fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        if save:
            filepath = self.viz_dir / "radar_chart.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            self._log(f"Saved: {filepath}")
            plt.close()
            return str(filepath)
        
        plt.show()
        return None
    
    def plot_category_heatmap(self, save: bool = True) -> Optional[str]:
        """Create heatmap of model performance by category."""
        if not self._check_dependencies():
            return None
        
        self._log("Generating category heatmap...")
        
        model_data = self.summary.get('by_model', {})
        if not model_data:
            self._log("No model data available")
            return None
        
        # Build data matrix
        models = list(model_data.keys())
        categories = ['Easy', 'Medium', 'Complex']
        
        # Get category scores for each model
        data_matrix = []
        for model_id in models:
            # Get from results since summary might not have category breakdown
            model_results = [r for r in self.results if r.get('model_id') == model_id]
            row = []
            for cat in categories:
                cat_results = [r['overall_score'] for r in model_results if r.get('category') == cat]
                avg = sum(cat_results) / len(cat_results) if cat_results else 0
                row.append(avg)
            data_matrix.append(row)
        
        data_matrix = np.array(data_matrix)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if HAS_SEABORN:
            sns.heatmap(data_matrix, annot=True, fmt='.1f', cmap='RdYlGn',
                       xticklabels=categories,
                       yticklabels=[m.split('/')[-1] for m in models],
                       vmin=0, vmax=100, ax=ax)
        else:
            im = ax.imshow(data_matrix, cmap='RdYlGn', vmin=0, vmax=100)
            ax.set_xticks(np.arange(len(categories)))
            ax.set_yticks(np.arange(len(models)))
            ax.set_xticklabels(categories)
            ax.set_yticklabels([m.split('/')[-1] for m in models])
            
            # Add annotations
            for i in range(len(models)):
                for j in range(len(categories)):
                    ax.text(j, i, f'{data_matrix[i, j]:.1f}',
                           ha='center', va='center', color='black')
            
            plt.colorbar(im)
        
        ax.set_title('Model Performance by Category', fontsize=14, fontweight='bold')
        ax.set_xlabel('Question Category')
        ax.set_ylabel('Model')
        
        plt.tight_layout()
        
        if save:
            filepath = self.viz_dir / "category_heatmap.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            self._log(f"Saved: {filepath}")
            plt.close()
            return str(filepath)
        
        plt.show()
        return None
    
    def plot_score_distribution(self, save: bool = True) -> Optional[str]:
        """Create box plots showing score distributions."""
        if not self._check_dependencies():
            return None
        
        self._log("Generating score distribution box plots...")
        
        if not self.results:
            self._log("No results available")
            return None
        
        # Group by model
        models = list(set(r['model_id'] for r in self.results))
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        metrics = [
            ('overall_score', 'Overall Score'),
            ('sql_score', 'SQL Score'),
            ('table_column_score', 'Table/Column Score'),
            ('methodology_score', 'Methodology Score')
        ]
        
        for ax, (metric, title) in zip(axes.flat, metrics):
            data = []
            labels = []
            for model in models:
                model_scores = [r[metric] for r in self.results if r['model_id'] == model]
                data.append(model_scores)
                labels.append(model.split('/')[-1])
            
            bp = ax.boxplot(data, labels=labels, patch_artist=True)
            
            # Color boxes
            for patch, color in zip(bp['boxes'], self.colors['models']):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_ylabel('Score')
            ax.set_ylim(0, 105)
            ax.axhline(y=70, color='green', linestyle='--', alpha=0.5)
            ax.axhline(y=40, color='orange', linestyle='--', alpha=0.5)
            ax.tick_params(axis='x', rotation=45)
        
        plt.suptitle('Score Distributions by Model', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save:
            filepath = self.viz_dir / "score_distribution.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            self._log(f"Saved: {filepath}")
            plt.close()
            return str(filepath)
        
        plt.show()
        return None
    
    def plot_latency_comparison(self, save: bool = True) -> Optional[str]:
        """Create latency comparison chart."""
        if not self._check_dependencies():
            return None
        
        self._log("Generating latency comparison chart...")
        
        model_data = self.summary.get('by_model', {})
        if not model_data:
            self._log("No model data available")
            return None
        
        models = list(model_data.keys())
        latencies = [model_data[m]['avg_latency_ms'] for m in models]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bars = ax.bar([m.split('/')[-1] for m in models], latencies, color=self.colors['models'][:len(models)])
        
        # Add value labels
        for bar, val in zip(bars, latencies):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                   f'{val:.0f}ms', ha='center', va='bottom', fontsize=10)
        
        ax.set_xlabel('Model')
        ax.set_ylabel('Average Latency (ms)')
        ax.set_title('Response Latency by Model', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        if save:
            filepath = self.viz_dir / "latency_comparison.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            self._log(f"Saved: {filepath}")
            plt.close()
            return str(filepath)
        
        plt.show()
        return None
    
    def generate_all_visualizations(self) -> Dict[str, str]:
        """Generate all visualizations and return paths."""
        self._log("=" * 50)
        self._log("GENERATING ALL VISUALIZATIONS")
        self._log("=" * 50)
        
        if not self.results:
            if not self.load_results():
                self._log("Could not load results")
                return {}
        
        paths = {}
        
        # Generate each visualization
        viz_methods = [
            ('model_comparison_bar', self.plot_model_comparison_bar),
            ('radar_chart', self.plot_radar_chart),
            ('category_heatmap', self.plot_category_heatmap),
            ('score_distribution', self.plot_score_distribution),
            ('latency_comparison', self.plot_latency_comparison),
        ]
        
        for name, method in viz_methods:
            try:
                path = method(save=True)
                if path:
                    paths[name] = path
            except Exception as e:
                self._log(f"ERROR generating {name}: {e}")
        
        # Log summary
        self._log("\n" + "=" * 50)
        self._log("VISUALIZATION SUMMARY")
        self._log("=" * 50)
        self._log(f"Generated {len(paths)} visualizations:")
        for name, path in paths.items():
            self._log(f"  - {name}: {Path(path).name}")
        self._log(f"\nVisualization log: {self.log_file}")
        
        return paths


def main():
    """Generate visualizations from existing results."""
    visualizer = BenchmarkVisualizer()
    
    if visualizer.load_results():
        visualizer.generate_all_visualizations()
    else:
        print("No results to visualize. Run benchmark first.")


if __name__ == "__main__":
    main()

