#!/usr/bin/env python3
"""
Complete LLM Benchmark Runner
Runs full benchmark with progress tracking, time estimates, and results display.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

def print_section(text):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}▶ {text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'-'*70}{Colors.ENDC}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def format_time(seconds):
    """Format seconds into readable time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds//60)}m {int(seconds%60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def check_requirements():
    """Check if all requirements are met."""
    print_section("Checking Requirements")
    
    # Check .env file
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print_error(".env file not found!")
        print_info("Please create .env file with your API keys:")
        print("  GROQ_API_KEY=your_groq_api_key")
        print("  GEMINI_API_KEY=your_gemini_api_key")
        return False
    print_success(".env file found")
    
    # Check API keys
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key or groq_key.startswith("your_"):
        print_error("GROQ_API_KEY not set or invalid in .env")
        return False
    print_success("GROQ_API_KEY found")
    
    # Check Python packages
    required_packages = ['groq', 'pandas', 'tqdm', 'google.generativeai']
    missing = []
    for package in required_packages:
        try:
            if package == 'google.generativeai':
                __import__('google.generativeai')
            else:
                __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print_error(f"Missing packages: {', '.join(missing)}")
        print_info("Install with: pip install -r requirements.txt")
        return False
    print_success("All required packages installed")
    
    # Check question file
    questions_file = Path(__file__).parent.parent / "question_generator" / "generated_questions.json"
    if not questions_file.exists():
        print_error(f"Questions file not found: {questions_file}")
        return False
    print_success(f"Questions file found: {questions_file}")
    
    return True

def run_benchmark():
    """Run the benchmark with progress tracking."""
    print_section("Running Benchmark")
    
    try:
        from benchmarks.benchmark_runner import BenchmarkRunner
        from benchmarks.question_loader import QuestionLoader
        import json
        
        # Load config
        config_file = Path(__file__).parent / "config" / "models_config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Get enabled models
        enabled_models = [m for m in config['models'] if m.get('enabled', True)]
        model_ids = [m['id'] for m in enabled_models]
        
        print_info(f"Testing {len(enabled_models)} models:")
        for model in enabled_models:
            print(f"  • {model['name']} ({model['id']})")
        
        # Initialize runner
        runner = BenchmarkRunner(use_gemini_eval=True)
        
        # Get sample size from config
        eval_config = config.get('evaluation', {})
        sample_size = eval_config.get('sample_size')
        # Ensure sample_size is not None - default to 30
        if sample_size is None or sample_size == 0:
            sample_size = 30
        runner.sample_size = sample_size
        
        # Load questions to estimate total
        loader = QuestionLoader()
        all_questions = loader.get_all()
        
        # Sample questions if needed
        if len(all_questions) > sample_size:
            import random
            random.seed(42)
            sampled_questions = random.sample(all_questions, sample_size)
        else:
            sampled_questions = all_questions
        
        print_info(f"Testing {len(sampled_questions)} questions")
        
        # Calculate total
        total_questions = len(sampled_questions) * len(model_ids)
        print_info(f"Total evaluations: {total_questions}")
        
        # Track progress
        start_time = time.time()
        completed = [0]
        current_model = [""]
        current_model_idx = [0]
        current_question_num = [0]
        total_questions_per_model = [len(sampled_questions)]
        
        # Override _log to show detailed progress
        original_log = runner._log
        
        def progress_log(msg, also_print=True):
            """Enhanced logging with detailed progress tracking."""
            # Always log to file
            original_log(msg, also_print=False)
            
            # Show detailed progress on terminal
            if also_print:
                # Detect model start
                if "--- Benchmarking:" in msg:
                    current_model_idx[0] += 1
                    current_model[0] = msg.split("--- Benchmarking:")[1].strip()
                    current_question_num[0] = 0
                    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
                    print(f"{Colors.BOLD}Model {current_model_idx[0]}/{len(model_ids)}: {current_model[0]}{Colors.ENDC}")
                    print(f"{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
                
                # Detect question start - format: "  [1/30] Easy_4: What is the total..."
                elif "[" in msg and "/" in msg and "]" in msg and ":" in msg and not "Score:" in msg:
                    # Extract question number
                    try:
                        q_match = msg.split("[")[1].split("]")[0]
                        if "/" in q_match:
                            q_num, q_total = q_match.split("/")
                            current_question_num[0] = int(q_num)
                            total_questions_per_model[0] = int(q_total)
                    except:
                        pass
                    
                    # Extract question ID and text
                    q_id = ""
                    q_text = ""
                    if ":" in msg:
                        parts = msg.split(":", 1)
                        if len(parts) > 1:
                            q_id = parts[0].split("]")[-1].strip() if "]" in parts[0] else parts[0].strip()
                            q_text = parts[1].split("...")[0].strip() if "..." in parts[1] else parts[1].strip()[:45]
                    
                    elapsed = time.time() - start_time
                    
                    if completed[0] > 0:
                        avg_time = elapsed / completed[0]
                        remaining = total_questions - completed[0]
                        eta = avg_time * remaining
                        eta_str = format_time(eta)
                        progress_pct = (completed[0] / total_questions) * 100
                    else:
                        eta_str = "calculating..."
                        progress_pct = 0
                    
                    # Show question details
                    print(f"\n{Colors.OKCYAN}[{current_question_num[0]}/{total_questions_per_model[0]}] {q_id[:20]:<20}{Colors.ENDC}")
                    print(f"  Question: {q_text[:60]}")
                    print(f"  Progress: {Colors.BOLD}{progress_pct:.1f}%{Colors.ENDC} ({completed[0]}/{total_questions}) | "
                          f"ETA: {Colors.WARNING}{eta_str}{Colors.ENDC}", end='', flush=True)
                
                # Detect score - format: "    Score: 56.8 (SQL: 77.0, Tables: 80.0, Method: 0.0)"
                elif "Score:" in msg and "SQL:" in msg:
                    completed[0] += 1
                    try:
                        # Extract scores using regex-like parsing
                        import re
                        overall_match = re.search(r'Score:\s*([\d.]+)', msg)
                        sql_match = re.search(r'SQL:\s*([\d.]+)', msg)
                        table_match = re.search(r'Tables:\s*([\d.]+)', msg)
                        method_match = re.search(r'Method:\s*([\d.]+)', msg)
                        
                        overall_score = float(overall_match.group(1)) if overall_match else 0
                        sql_score = float(sql_match.group(1)) if sql_match else 0
                        table_score = float(table_match.group(1)) if table_match else 0
                        method_score = float(method_match.group(1)) if method_match else 0
                        
                        # Color code overall score
                        if overall_score >= 60:
                            score_color = Colors.OKGREEN
                        elif overall_score >= 40:
                            score_color = Colors.WARNING
                        else:
                            score_color = Colors.FAIL
                        
                        # Calculate updated ETA
                        elapsed = time.time() - start_time
                        if completed[0] > 0:
                            avg_time = elapsed / completed[0]
                            remaining = total_questions - completed[0]
                            eta = avg_time * remaining
                            eta_str = format_time(eta)
                            progress_pct = (completed[0] / total_questions) * 100
                        else:
                            eta_str = "calculating..."
                            progress_pct = 0
                        
                        # Show score details
                        print(f"\r  {Colors.BOLD}✓ Score: {score_color}{overall_score:.1f}%{Colors.ENDC} | "
                              f"SQL: {sql_score:.1f}% | "
                              f"Tables: {table_score:.1f}% | "
                              f"Method: {method_score:.1f}% | "
                              f"Progress: {Colors.BOLD}{progress_pct:.1f}%{Colors.ENDC} | "
                              f"ETA: {Colors.WARNING}{eta_str}{Colors.ENDC}")
                        
                    except Exception as e:
                        # If parsing fails, just show the message
                        print(f"\n  {msg}")
                
                # Show errors
                elif "ERROR" in msg:
                    print(f"\n{Colors.FAIL}  ✗ ERROR: {msg}{Colors.ENDC}")
                
                # Show completion messages
                elif "completed" in msg.lower() and ("seconds" in msg.lower() or "Benchmark completed" in msg):
                    print(f"\n{Colors.OKGREEN}  ✓ {msg}{Colors.ENDC}")
        
        runner._log = progress_log
        
        # Run benchmark
        print(f"\n{Colors.OKBLUE}Starting benchmark...{Colors.ENDC}\n")
        result_dict = runner.run(models=model_ids, categories=None)
        
        # Restore original log
        runner._log = original_log
        
        results = result_dict.get('results', [])
        total_time = time.time() - start_time
        
        print(f"\n\n{Colors.OKGREEN}✓ Benchmark completed in {format_time(total_time)}{Colors.ENDC}")
        print_info(f"Total results: {len(results)}")
        
        return results
        
    except Exception as e:
        print_error(f"Benchmark failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def generate_visualizations():
    """Generate visualizations and reports."""
    print_section("Generating Visualizations")
    
    try:
        from analysis.visualizations import BenchmarkVisualizer
        from analysis.metrics_aggregator import MetricsAggregator
        
        viz = BenchmarkVisualizer()
        if not viz.load_results():
            print_error("No results found to visualize")
            return False
        
        print_info("Generating visualizations...")
        paths = viz.generate_all_visualizations()
        
        print_success(f"Generated {len(paths)} visualizations:")
        for name, path in paths.items():
            print(f"  • {name}: {path}")
        
        # Generate report
        print_info("Generating analysis report...")
        agg = MetricsAggregator()
        if agg.load_results():
            report_path = viz.results_dir / 'logs' / 'analysis_report.txt'
            report = agg.generate_report(report_path)
            print_success(f"Analysis report saved: {report_path}")
        
        return True
        
    except Exception as e:
        print_error(f"Visualization generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_summary():
    """Show benchmark summary."""
    print_section("Benchmark Summary")
    
    try:
        import pandas as pd
        from pathlib import Path
        
        results_dir = Path(__file__).parent / "results"
        comparison_file = results_dir / "model_comparison.csv"
        
        if not comparison_file.exists():
            print_warning("Summary file not found")
            return
        
        df = pd.read_csv(comparison_file)
        
        # Sort by overall score
        if 'avg_overall' in df.columns:
            df = df.sort_values('avg_overall', ascending=False)
            
            print(f"\n{Colors.BOLD}{'Rank':<6} {'Model':<35} {'Overall':<10} {'SQL':<10} {'Tables':<10} {'Latency':<12}{Colors.ENDC}")
            print(f"{Colors.OKBLUE}{'-'*90}{Colors.ENDC}")
            
            for idx, row in df.iterrows():
                rank = df.index.get_loc(idx) + 1
                model_name = row.get('Unnamed: 0', 'Unknown')
                if len(model_name) > 33:
                    model_name = model_name[:30] + "..."
                
                overall = row.get('avg_overall', 0)
                sql = row.get('avg_sql', 0)
                tables = row.get('avg_table_column', 0)
                latency = row.get('avg_latency_ms', 0)
                
                # Color code by score
                if overall >= 60:
                    color = Colors.OKGREEN
                elif overall >= 40:
                    color = Colors.WARNING
                else:
                    color = Colors.FAIL
                
                print(f"{rank:<6} {model_name:<35} {color}{overall:>6.1f}%{Colors.ENDC}  "
                      f"{sql:>6.1f}%  {tables:>6.1f}%  {latency:>8.0f}ms")
            
            # Show top model
            top_model = df.iloc[0]
            print(f"\n{Colors.BOLD}{Colors.OKGREEN}🏆 Top Model: {top_model.get('Unnamed: 0', 'Unknown')}{Colors.ENDC}")
            print(f"   Overall Score: {top_model.get('avg_overall', 0):.1f}%")
            print(f"   SQL Score: {top_model.get('avg_sql', 0):.1f}%")
            print(f"   Table/Column Score: {top_model.get('avg_table_column', 0):.1f}%")
        
        # Show file locations
        print(f"\n{Colors.BOLD}Results Location:{Colors.ENDC}")
        print(f"  • Metrics: {results_dir / 'metrics'}")
        print(f"  • Visualizations: {results_dir / 'visualizations'}")
        print(f"  • Logs: {results_dir / 'logs'}")
        
    except Exception as e:
        print_error(f"Failed to show summary: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main execution function."""
    print_header("LLM Benchmark - Complete Runner")
    
    start_time = time.time()
    
    # Check requirements
    if not check_requirements():
        print_error("Requirements check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Run benchmark
    results = run_benchmark()
    if results is None:
        print_error("Benchmark failed. Check errors above.")
        sys.exit(1)
    
    # Generate visualizations
    if not generate_visualizations():
        print_warning("Visualization generation had issues, but continuing...")
    
    # Show summary
    show_summary()
    
    # Final summary
    total_time = time.time() - start_time
    print_header("Benchmark Complete!")
    print_success(f"Total execution time: {format_time(total_time)}")
    print_info("Check the results/ directory for detailed outputs")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Benchmark interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

