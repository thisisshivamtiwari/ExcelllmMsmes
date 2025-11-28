#!/usr/bin/env python3
"""
MSME Shopfloor Question Generator
Analyzes all data files and generates categorized questions with answers and formulas.
"""

import os
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import time

# Try to detect and use Anaconda Python if available
def find_python_with_packages():
    """Find Python interpreter that has required packages installed."""
    python_paths = [
        "/opt/anaconda3/bin/python3",
        os.path.expanduser("~/anaconda3/bin/python3"),
        os.path.expanduser("~/miniconda3/bin/python3"),
    ]
    
    for python_path in python_paths:
        if os.path.exists(python_path):
            try:
                result = subprocess.run(
                    [python_path, "-c", "import google.generativeai; import pandas; import dotenv"],
                    capture_output=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    return python_path
            except (subprocess.TimeoutExpired, Exception):
                if "anaconda" in python_path.lower() or "miniconda" in python_path.lower():
                    return python_path
                continue
    
    return None

# Check for required packages
try:
    import pandas as pd
except ImportError:
    correct_python = find_python_with_packages()
    if correct_python:
        print("=" * 60)
        print("ERROR: Required packages not found in current Python!")
        print("=" * 60)
        print(f"\nFound Python with packages at: {correct_python}")
        print(f"\nPlease run the script using:")
        print(f"  {correct_python} {sys.argv[0]}")
        sys.exit(1)
    else:
        print("Error: pandas not installed. Run: pip install pandas")
        sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    correct_python = find_python_with_packages()
    if correct_python:
        print("=" * 60)
        print("ERROR: Required packages not found in current Python!")
        print("=" * 60)
        print(f"\nFound Python with packages at: {correct_python}")
        print(f"\nPlease run the script using:")
        print(f"  {correct_python} {sys.argv[0]}")
        sys.exit(1)
    else:
        print("Error: google-generativeai not installed.")
        print("Run: pip install google-generativeai")
        sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    correct_python = find_python_with_packages()
    if correct_python:
        print("=" * 60)
        print("ERROR: Required packages not found in current Python!")
        print("=" * 60)
        print(f"\nFound Python with packages at: {correct_python}")
        print(f"\nPlease run the script using:")
        print(f"  {correct_python} {sys.argv[0]}")
        sys.exit(1)
    else:
        print("Error: python-dotenv not installed. Run: pip install python-dotenv")
        sys.exit(1)

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    env_file = Path(__file__).parent.parent / "datagenerator" / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    if not GEMINI_API_KEY:
        print("=" * 60)
        print("ERROR: GEMINI_API_KEY not found!")
        print("=" * 60)
        print("\nPlease set GEMINI_API_KEY in .env file")
        print("Get your API key from: https://makersuite.google.com/app/apikey")
        print("=" * 60)
        sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Configuration
DATA_DIR = Path(__file__).parent.parent / "datagenerator" / "generated_data"
QUESTIONS_FILE = Path(__file__).parent / "generated_questions.json"
QUESTIONS_CSV_FILE = Path(__file__).parent / "generated_questions.csv"
QUESTIONS_PER_CATEGORY = 35
CATEGORIES = ["Easy", "Medium", "Complex"]


class DataAnalyzer:
    """Analyzes data files and extracts relationships."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.dataframes = {}
        self.relationships = {}
        self.schema = {}
        
    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """Load all CSV files from data directory."""
        print("Loading data files...")
        for csv_file in self.data_dir.glob("*.csv"):
            try:
                df_name = csv_file.stem
                df = pd.read_csv(csv_file)
                # Convert date columns
                date_cols = [col for col in df.columns if 'date' in col.lower() or col == 'Date']
                for col in date_cols:
                    df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
                self.dataframes[df_name] = df
                print(f"  ✓ Loaded {df_name}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                print(f"  ✗ Error loading {csv_file.name}: {e}")
        
        return self.dataframes
    
    def analyze_schema(self) -> Dict[str, Dict]:
        """Analyze schema of all dataframes."""
        print("\nAnalyzing data schema...")
        for name, df in self.dataframes.items():
            self.schema[name] = {
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "row_count": len(df),
                "date_columns": [col for col in df.columns if 'date' in col.lower() or col == 'Date'],
                "numeric_columns": list(df.select_dtypes(include=['int64', 'float64']).columns),
                "categorical_columns": list(df.select_dtypes(include=['object']).columns),
                "sample_values": {}
            }
            
            # Get sample values for key columns
            for col in df.columns[:10]:  # Sample first 10 columns
                unique_vals = df[col].dropna().unique()[:5]
                self.schema[name]["sample_values"][col] = [str(v) for v in unique_vals]
        
        return self.schema
    
    def detect_relationships(self) -> Dict:
        """Detect relationships between data files."""
        print("\nDetecting relationships across files...")
        relationships = {
            "date_links": [],
            "product_links": [],
            "machine_links": [],
            "material_links": [],
            "common_columns": {},
            "foreign_keys": []
        }
        
        # Find common date columns
        date_cols_by_file = {}
        for name, df in self.dataframes.items():
            date_cols = [col for col in df.columns if 'date' in col.lower() or col == 'Date']
            if date_cols:
                date_cols_by_file[name] = date_cols
        
        # Find date relationships
        for file1, dates1 in date_cols_by_file.items():
            for file2, dates2 in date_cols_by_file.items():
                if file1 != file2:
                    for d1 in dates1:
                        for d2 in dates2:
                            relationships["date_links"].append({
                                "file1": file1,
                                "column1": d1,
                                "file2": file2,
                                "column2": d2,
                                "type": "date_link"
                            })
        
        # Find product relationships
        product_cols = {}
        for name, df in self.dataframes.items():
            product_cols_found = [col for col in df.columns if 'product' in col.lower()]
            if product_cols_found:
                product_cols[name] = product_cols_found
        
        for file1, cols1 in product_cols.items():
            for file2, cols2 in product_cols.items():
                if file1 != file2:
                    relationships["product_links"].append({
                        "file1": file1,
                        "column1": cols1[0],
                        "file2": file2,
                        "column2": cols2[0],
                        "type": "product_link"
                    })
        
        # Find machine relationships
        machine_cols = {}
        for name, df in self.dataframes.items():
            machine_cols_found = [col for col in df.columns if 'machine' in col.lower()]
            if machine_cols_found:
                machine_cols[name] = machine_cols_found
        
        for file1, cols1 in machine_cols.items():
            for file2, cols2 in machine_cols.items():
                if file1 != file2:
                    relationships["machine_links"].append({
                        "file1": file1,
                        "column1": cols1[0],
                        "file2": file2,
                        "column2": cols2[0],
                        "type": "machine_link"
                    })
        
        # Find common columns across files
        all_columns = {}
        for name, df in self.dataframes.items():
            for col in df.columns:
                if col not in all_columns:
                    all_columns[col] = []
                all_columns[col].append(name)
        
        for col, files in all_columns.items():
            if len(files) > 1:
                relationships["common_columns"][col] = files
        
        self.relationships = relationships
        return relationships
    
    def get_data_summary(self) -> str:
        """Get a comprehensive summary of all data for question generation."""
        summary_parts = []
        
        summary_parts.append("DATA FILES SUMMARY:")
        summary_parts.append("=" * 60)
        
        for name, df in self.dataframes.items():
            summary_parts.append(f"\n{name.upper()}:")
            summary_parts.append(f"  Rows: {len(df)}")
            summary_parts.append(f"  Columns: {', '.join(df.columns)}")
            
            # Date range
            date_cols = [col for col in df.columns if 'date' in col.lower() or col == 'Date']
            if date_cols:
                for date_col in date_cols:
                    dates = df[date_col].dropna()
                    if not dates.empty:
                        summary_parts.append(f"  {date_col} range: {dates.min()} to {dates.max()}")
            
            # Numeric columns summary
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                summary_parts.append(f"  Numeric columns: {', '.join(numeric_cols)}")
                for col in numeric_cols[:5]:  # First 5 numeric columns
                    summary_parts.append(f"    {col}: min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.2f}")
            
            # Categorical columns
            cat_cols = df.select_dtypes(include=['object']).columns
            if len(cat_cols) > 0:
                summary_parts.append(f"  Categorical columns: {', '.join(cat_cols)}")
                for col in cat_cols[:3]:  # First 3 categorical columns
                    unique_vals = df[col].dropna().unique()[:5]
                    summary_parts.append(f"    {col}: {', '.join([str(v) for v in unique_vals])}")
        
        summary_parts.append("\n" + "=" * 60)
        summary_parts.append("\nRELATIONSHIPS:")
        summary_parts.append("=" * 60)
        
        if self.relationships.get("date_links"):
            summary_parts.append(f"\nDate Links: {len(self.relationships['date_links'])} connections")
        if self.relationships.get("product_links"):
            summary_parts.append(f"Product Links: {len(self.relationships['product_links'])} connections")
        if self.relationships.get("machine_links"):
            summary_parts.append(f"Machine Links: {len(self.relationships['machine_links'])} connections")
        if self.relationships.get("common_columns"):
            summary_parts.append(f"Common Columns: {len(self.relationships['common_columns'])} shared columns")
        
        return "\n".join(summary_parts)


class QuestionGenerator:
    """Generates questions using Gemini API."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        try:
            self.model = genai.GenerativeModel(model_name)
            print(f"Using model: {model_name}")
        except Exception as e:
            print(f"Warning: {model_name} not available, trying gemini-2.5-flash...")
            try:
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                print("Using model: gemini-2.5-flash")
            except Exception as e2:
                self.model = genai.GenerativeModel('gemini-2.5-pro')
                print("Using model: gemini-2.5-pro")
    
    def generate_questions(self, data_summary: str, relationships: Dict, 
                          category: str, count: int) -> List[Dict]:
        """Generate questions for a specific category."""
        print(f"\nGenerating {count} {category} questions...")
        
        difficulty_guidelines = {
            "Easy": "Simple queries requiring basic aggregations (SUM, COUNT, AVG) on single tables, filtering by date ranges or categories, finding min/max values.",
            "Medium": "Queries requiring JOINs between 2-3 tables, GROUP BY with aggregations, date calculations, percentage calculations, conditional aggregations.",
            "Complex": "Multi-table JOINs (3+ tables), complex aggregations with subqueries, time-series analysis, correlation analysis, trend calculations, predictive queries."
        }
        
        prompt = f"""You are analyzing MSME shopfloor manufacturing data. Based on the following data summary and relationships, generate {count} realistic questions.

DATA SUMMARY:
{data_summary}

RELATIONSHIPS:
{json.dumps(relationships, indent=2)}

CATEGORY: {category}
DIFFICULTY GUIDELINES: {difficulty_guidelines[category]}

For each question, provide:
1. A clear, natural language question that a shopfloor manager would ask
2. The exact SQL formula/query to answer it (or Excel formula if applicable)
3. The step-by-step calculation method
4. The expected answer format (number, percentage, date range, etc.)

Return as JSON array with this exact structure:
[
  {{
    "question": "What is the total production quantity for Widget-A in the last 30 days?",
    "category": "{category}",
    "sql_formula": "SELECT SUM(Actual_Qty) FROM production_logs WHERE Product = 'Widget-A' AND Date >= DATE('now', '-30 days')",
    "excel_formula": "=SUMIFS(production_logs[Actual_Qty], production_logs[Product], \"Widget-A\", production_logs[Date], \">=\"&TODAY()-30)",
    "calculation_steps": [
      "Filter production_logs for Product = 'Widget-A'",
      "Filter for dates in last 30 days",
      "Sum the Actual_Qty column"
    ],
    "answer_format": "integer (total quantity)",
    "related_tables": ["production_logs"],
    "related_columns": ["Product", "Actual_Qty", "Date"]
  }}
]

Generate {count} unique questions. Make them realistic and relevant to manufacturing operations.
Return ONLY valid JSON array, no markdown, no explanations."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Parse JSON from response
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            questions = json.loads(response_text)
            if isinstance(questions, list):
                return questions
            elif isinstance(questions, dict) and "questions" in questions:
                return questions["questions"]
            else:
                return [questions]
        except Exception as e:
            print(f"Error generating questions: {e}")
            print(f"Response text: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            return []


class QuestionManager:
    """Manages question storage and duplicate detection."""
    
    def __init__(self, questions_file: Path):
        self.questions_file = questions_file
        self.questions_csv_file = questions_file.with_suffix('.csv')
        self.questions = self.load_questions()
    
    def load_questions(self) -> Dict[str, List[Dict]]:
        """Load existing questions from file."""
        if self.questions_file.exists():
            try:
                with open(self.questions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("questions", {"Easy": [], "Medium": [], "Complex": []})
            except Exception as e:
                print(f"Warning: Could not load existing questions: {e}")
        
        return {"Easy": [], "Medium": [], "Complex": []}
    
    def save_questions(self):
        """Save questions to both JSON and CSV files."""
        total_questions = sum(len(q) for q in self.questions.values())
        output = {
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "total_questions": total_questions,
                "questions_by_category": {cat: len(q) for cat, q in self.questions.items()}
            },
            "questions": self.questions
        }
        
        # Save JSON
        with open(self.questions_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {total_questions} questions to {self.questions_file}")
        
        # Save CSV
        self.save_questions_csv()
    
    def save_questions_csv(self):
        """Save questions to CSV format."""
        # Flatten all questions into a list
        all_questions = []
        for category, questions in self.questions.items():
            for q in questions:
                row = {
                    "id": q.get("id", ""),
                    "category": q.get("category", category),
                    "question": q.get("question", ""),
                    "sql_formula": q.get("sql_formula", ""),
                    "excel_formula": q.get("excel_formula", ""),
                    "calculation_steps": " | ".join(q.get("calculation_steps", [])),
                    "answer_format": q.get("answer_format", ""),
                    "related_tables": ", ".join(q.get("related_tables", [])),
                    "related_columns": ", ".join(q.get("related_columns", [])),
                    "created_at": q.get("created_at", "")
                }
                all_questions.append(row)
        
        if all_questions:
            df = pd.DataFrame(all_questions)
            # Reorder columns for better readability
            column_order = [
                "id", "category", "question", "sql_formula", "excel_formula",
                "calculation_steps", "answer_format", "related_tables",
                "related_columns", "created_at"
            ]
            df = df[[col for col in column_order if col in df.columns]]
            df.to_csv(self.questions_csv_file, index=False, encoding='utf-8')
            print(f"✓ Saved {len(all_questions)} questions to {self.questions_csv_file}")
        else:
            print("  No questions to save to CSV")
    
    def get_existing_question_texts(self) -> Set[str]:
        """Get set of existing question texts for duplicate detection."""
        existing = set()
        for category_questions in self.questions.values():
            for q in category_questions:
                existing.add(q.get("question", "").lower().strip())
        return existing
    
    def add_questions(self, new_questions: List[Dict], category: str):
        """Add new questions, filtering duplicates."""
        existing_texts = self.get_existing_question_texts()
        added_count = 0
        
        for q in new_questions:
            q_text = q.get("question", "").lower().strip()
            if q_text and q_text not in existing_texts:
                q["category"] = category
                q["id"] = f"{category}_{len(self.questions[category]) + 1}"
                q["created_at"] = datetime.now().isoformat()
                self.questions[category].append(q)
                existing_texts.add(q_text)
                added_count += 1
        
        print(f"  Added {added_count} new {category} questions (filtered {len(new_questions) - added_count} duplicates)")
        return added_count
    
    def get_question_counts(self) -> Dict[str, int]:
        """Get current question counts by category."""
        return {cat: len(q) for cat, q in self.questions.items()}


def main():
    """Main function to generate questions."""
    print("=" * 60)
    print("MSME Shopfloor Question Generator")
    print("=" * 60)
    
    # Initialize components
    analyzer = DataAnalyzer(DATA_DIR)
    question_gen = QuestionGenerator()
    question_mgr = QuestionManager(QUESTIONS_FILE)
    
    # Load and analyze data
    dataframes = analyzer.load_all_data()
    if not dataframes:
        print("\nError: No data files found in", DATA_DIR)
        return 1
    
    schema = analyzer.analyze_schema()
    relationships = analyzer.detect_relationships()
    data_summary = analyzer.get_data_summary()
    
    print("\n" + "=" * 60)
    print("Current Question Status:")
    print("=" * 60)
    counts = question_mgr.get_question_counts()
    for cat in CATEGORIES:
        print(f"  {cat}: {counts.get(cat, 0)} questions")
    
    # Generate questions for each category
    total_added = 0
    for category in CATEGORIES:
        current_count = len(question_mgr.questions.get(category, []))
        needed = max(0, QUESTIONS_PER_CATEGORY - current_count)
        
        if needed > 0:
            print(f"\n{'=' * 60}")
            print(f"Generating {needed} {category} questions...")
            print("=" * 60)
            
            # Generate in batches to avoid API limits
            batch_size = 10
            for batch_start in range(0, needed, batch_size):
                batch_count = min(batch_size, needed - batch_start)
                new_questions = question_gen.generate_questions(
                    data_summary, relationships, category, batch_count
                )
                
                if new_questions:
                    added = question_mgr.add_questions(new_questions, category)
                    total_added += added
                    question_mgr.save_questions()  # Save after each batch
                    time.sleep(2)  # Rate limiting
                else:
                    print(f"  Warning: No questions generated for batch")
        else:
            print(f"\n{category}: Already has {current_count} questions (target: {QUESTIONS_PER_CATEGORY})")
    
    # Final save
    question_mgr.save_questions()
    
    print("\n" + "=" * 60)
    print("Question Generation Complete!")
    print("=" * 60)
    final_counts = question_mgr.get_question_counts()
    for cat in CATEGORIES:
        print(f"  {cat}: {final_counts.get(cat, 0)} questions")
    print(f"\nTotal questions: {sum(final_counts.values())}")
    print(f"New questions added: {total_added}")
    print(f"\nQuestions saved to:")
    print(f"  - JSON: {QUESTIONS_FILE}")
    print(f"  - CSV: {QUESTIONS_CSV_FILE}")
    
    return 0


if __name__ == "__main__":
    exit(main())

