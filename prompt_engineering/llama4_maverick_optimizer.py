#!/usr/bin/env python3
"""
Llama 4 Maverick Prompt Engineering Optimizer
Enhanced prompt engineering to improve accuracy for meta-llama/llama-4-maverick-17b-128e-instruct
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables (try multiple locations)
base_path = Path(__file__).parent.parent
load_dotenv()  # Current directory
load_dotenv(base_path / ".env")  # Parent directory
load_dotenv(base_path / "llm_benchmarking" / ".env")  # llm_benchmarking directory

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    print("Warning: groq package not found. Install with: pip install groq")


@dataclass
class PromptResult:
    """Result of a prompt test."""
    question_id: str
    question_text: str
    category: str
    prompt_version: str
    response: str
    score: float
    latency_ms: float
    tokens: int
    error: Optional[str] = None


class EnhancedPromptEngineer:
    """Enhanced prompt engineering for Llama 4 Maverick."""
    
    def __init__(self, model_id: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        """
        Initialize the prompt engineer.
        
        Args:
            model_id: The Groq model ID to use
        """
        self.model_id = model_id
        self.base_dir = Path(__file__).parent
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize Groq client (optional - only needed for query_llm)
        self.client = None
        if HAS_GROQ:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key and api_key.strip() and not api_key.startswith("your_"):
                try:
                    self.client = Groq(api_key=api_key)
                    print(f"✓ Groq client initialized for {model_id}")
                except Exception as e:
                    print(f"Warning: Failed to initialize Groq client: {e}")
            else:
                print("Warning: GROQ_API_KEY not found or invalid. LLM queries will fail.")
        
        # Load schema information
        self.schema_info = self._load_schema_info()
        
        # Load few-shot examples
        self.few_shot_examples = self._load_few_shot_examples()
    
    def _load_schema_info(self) -> Dict:
        """Load database schema information."""
        return {
            "production_logs": {
                "description": "Daily production records with targets, actuals, and downtime",
                "columns": {
                    "Date": "DATE - Production date",
                    "Shift": "VARCHAR - 'Morning', 'Afternoon', 'Night'",
                    "Line_Machine": "VARCHAR - Format: 'Line-X/Machine-MY'",
                    "Product": "VARCHAR - Product names: 'Widget-A', 'Widget-B', 'Widget-C', 'Component-X', 'Component-Y', 'Assembly-Z'",
                    "Target_Qty": "INTEGER - Target production quantity",
                    "Actual_Qty": "INTEGER - Actual production quantity",
                    "Downtime_Minutes": "INTEGER - Machine downtime in minutes",
                    "Operator": "VARCHAR - Operator name"
                },
                "relationships": ["Can join with quality_control on Product and Date", "Can join with maintenance_logs on Machine"]
            },
            "quality_control": {
                "description": "Quality inspection records with defect tracking and rework counts",
                "columns": {
                    "Inspection_Date": "DATE - Date of inspection",
                    "Batch_ID": "VARCHAR - Unique batch identifier",
                    "Product": "VARCHAR - Product name",
                    "Line": "VARCHAR - Production line: 'Line-1', 'Line-2', 'Line-3'",
                    "Inspected_Qty": "INTEGER - Total quantity inspected",
                    "Passed_Qty": "INTEGER - Quantity that passed inspection",
                    "Failed_Qty": "INTEGER - Quantity that failed inspection",
                    "Defect_Type": "VARCHAR - Types: 'Dimensional', 'Surface Finish', 'Assembly Error', 'Material Defect', 'Packaging Issue'",
                    "Rework_Count": "INTEGER - Number of items requiring rework",
                    "Inspector_Name": "VARCHAR - Inspector name"
                },
                "relationships": ["Joins with production_logs on Product and Date", "Line matches Line_Machine prefix"]
            },
            "maintenance_logs": {
                "description": "Machine maintenance records including preventive and breakdown maintenance",
                "columns": {
                    "Maintenance_Date": "DATE - Date maintenance performed",
                    "Machine": "VARCHAR - Machine identifier: 'Machine-M1' to 'Machine-M5'",
                    "Maintenance_Type": "VARCHAR - 'Preventive', 'Breakdown', 'Routine Check', 'Repair'",
                    "Breakdown_Date": "DATE - Date of breakdown (nullable)",
                    "Downtime_Hours": "FLOAT - Hours of downtime",
                    "Issue_Description": "VARCHAR - Description of issue",
                    "Technician": "VARCHAR - Technician name",
                    "Parts_Replaced": "VARCHAR - Comma-separated list of parts",
                    "Cost_Rupees": "INTEGER - Maintenance cost in rupees"
                },
                "relationships": ["Machine matches Line_Machine suffix", "Can correlate with production_logs downtime"]
            },
            "inventory_logs": {
                "description": "Material inventory tracking with consumption, receipts, and wastage",
                "columns": {
                    "Date": "DATE - Inventory date",
                    "Material_Code": "VARCHAR - Material codes: 'Steel-101', 'Plastic-PVC', 'Aluminum-AL', 'Rubber-RB', 'Copper-CU'",
                    "Material_Name": "VARCHAR - Material name",
                    "Opening_Stock_Kg": "INTEGER - Opening stock in kg",
                    "Consumption_Kg": "INTEGER - Material consumed in kg",
                    "Received_Kg": "INTEGER - Material received in kg",
                    "Closing_Stock_Kg": "INTEGER - Closing stock in kg",
                    "Wastage_Kg": "INTEGER - Material wasted in kg",
                    "Supplier": "VARCHAR - Supplier name",
                    "Unit_Cost_Rupees": "FLOAT - Cost per unit in rupees"
                },
                "relationships": ["Can be analyzed independently or correlated with production"]
            }
        }
    
    def _load_few_shot_examples(self) -> Dict:
        """Load few-shot examples for different question types."""
        return {
            "simple_aggregation": {
                "question": "What is the total number of components reworked in Line-2?",
                "methodology": [
                    "Filter quality_control table for Line = 'Line-2'",
                    "Sum the Rework_Count column"
                ],
                "sql": "SELECT SUM(Rework_Count) FROM quality_control WHERE Line = 'Line-2'",
                "tables": ["quality_control"],
                "columns": ["Line", "Rework_Count"]
            },
            "top_n_query": {
                "question": "What are the top 3 defect types that lead to rework for Widget-B, and what is their total rework count?",
                "methodology": [
                    "Filter quality_control for Product = 'Widget-B'",
                    "Group by Defect_Type",
                    "Sum Rework_Count for each defect type",
                    "Order by total rework count descending",
                    "Limit to top 3"
                ],
                "sql": "SELECT Defect_Type, SUM(Rework_Count) AS Total_Rework FROM quality_control WHERE Product = 'Widget-B' GROUP BY Defect_Type ORDER BY Total_Rework DESC LIMIT 3",
                "tables": ["quality_control"],
                "columns": ["Product", "Defect_Type", "Rework_Count"]
            },
            "correlation_analysis": {
                "question": "What is the correlation between downtime minutes and failed quantity per line machine and product?",
                "methodology": [
                    "Join production_logs and quality_control on Date and Product",
                    "Extract Line from Line_Machine in production_logs",
                    "Match Line with quality_control Line",
                    "Group by Line_Machine and Product",
                    "Aggregate Downtime_Minutes from production_logs",
                    "Aggregate Failed_Qty from quality_control",
                    "Calculate correlation coefficient"
                ],
                "sql": "SELECT pl.Line_Machine, pl.Product, AVG(pl.Downtime_Minutes) AS Avg_Downtime, SUM(qc.Failed_Qty) AS Total_Failed FROM production_logs pl JOIN quality_control qc ON pl.Date = qc.Inspection_Date AND pl.Product = qc.Product WHERE SUBSTRING(pl.Line_Machine, 1, 5) = qc.Line GROUP BY pl.Line_Machine, pl.Product",
                "tables": ["production_logs", "quality_control"],
                "columns": ["Line_Machine", "Product", "Downtime_Minutes", "Line", "Failed_Qty"]
            },
            "date_filtering": {
                "question": "How much total waste was recorded in 2025?",
                "methodology": [
                    "Filter inventory_logs for year 2025",
                    "Sum Wastage_Kg column"
                ],
                "sql": "SELECT SUM(Wastage_Kg) AS Total_Waste FROM inventory_logs WHERE EXTRACT(YEAR FROM Date) = 2025",
                "tables": ["inventory_logs"],
                "columns": ["Date", "Wastage_Kg"]
            }
        }
    
    def generate_enhanced_methodology_prompt(self, question: str, question_category: str = "Medium") -> str:
        """
        Generate enhanced methodology prompt with few-shot examples and chain-of-thought.
        
        Args:
            question: The question to answer
            question_category: Category of question (Easy, Medium, Complex)
        
        Returns:
            Enhanced prompt string
        """
        # Select relevant few-shot example based on question type
        example_key = self._identify_question_type(question)
        example = self.few_shot_examples.get(example_key, self.few_shot_examples["simple_aggregation"])
        
        prompt = f"""You are an expert data analyst specializing in MSME manufacturing operations. Your task is to break down complex questions into clear, executable steps.

## Context: Manufacturing Data Analysis
You work with production, quality, maintenance, and inventory data from a manufacturing facility. Understanding relationships between these datasets is crucial for accurate analysis.

## Available Data Tables:

### production_logs
Purpose: {self.schema_info['production_logs']['description']}
Key Columns:
{self._format_columns(self.schema_info['production_logs']['columns'])}
Relationships: {self.schema_info['production_logs']['relationships'][0]}

### quality_control
Purpose: {self.schema_info['quality_control']['description']}
Key Columns:
{self._format_columns(self.schema_info['quality_control']['columns'])}
Relationships: {self.schema_info['quality_control']['relationships'][0]}

### maintenance_logs
Purpose: {self.schema_info['maintenance_logs']['description']}
Key Columns:
{self._format_columns(self.schema_info['maintenance_logs']['columns'])}
Relationships: {self.schema_info['maintenance_logs']['relationships'][0]}

### inventory_logs
Purpose: {self.schema_info['inventory_logs']['description']}
Key Columns:
{self._format_columns(self.schema_info['inventory_logs']['columns'])}
Relationships: {self.schema_info['inventory_logs']['relationships'][0]}

## Example Analysis (Few-Shot Learning):

**Question:** {example['question']}

**Step-by-Step Methodology:**
{self._format_steps(example['methodology'])}

## Your Task:

**Question:** {question}

**Question Category:** {question_category}

**Instructions:**
1. First, identify which table(s) contain the required data
2. Determine if you need to join multiple tables (check relationships above)
3. Break down the question into specific, numbered steps
4. For each step, specify:
   - Which table(s) to use
   - What filters to apply (be specific with column names and values)
   - What aggregations or calculations to perform
   - How to combine data if multiple tables are needed
5. Consider edge cases (NULL values, date ranges, etc.)

**Response Format:**
Provide a numbered list of steps. Be precise and specific. Use this format:

```steps
1. [Specific action with table and column names]
2. [Next specific action]
...
```

**Important Notes:**
- For date filtering, use EXTRACT(YEAR FROM Date) or date range comparisons
- For joining tables, match on both Date and Product when both are available
- For Line_Machine, extract Line prefix (e.g., 'Line-1' from 'Line-1/Machine-M1')
- Always specify exact column names and filter values
- Consider NULL handling for optional fields
"""
        return prompt
    
    def generate_enhanced_sql_prompt(self, question: str, methodology_steps: List[str] = None, version: str = "baseline") -> str:
        """
        Generate enhanced SQL prompt with schema details and examples.
        
        Args:
            question: The question to answer
            methodology_steps: Optional list of methodology steps to guide SQL generation
            version: Prompt version ("v1" or "v2")
        
        Returns:
            Enhanced SQL prompt string
        """
        # Use baseline SQL prompt (same as original benchmark)
        baseline_prompt_file = self.base_dir.parent / "llm_benchmarking" / "prompts" / "sql_generation_prompt.txt"
        
        if baseline_prompt_file.exists():
            try:
                with open(baseline_prompt_file, 'r', encoding='utf-8') as f:
                    base_prompt = f.read()
                # Replace {question} placeholder
                prompt = base_prompt.replace("{question}", question)
                return prompt
            except Exception as e:
                print(f"Warning: Could not load baseline SQL prompt: {e}. Using fallback.")
        
        # Fallback: simple baseline prompt
        prompt = f"""You are an expert SQL developer working with MSME manufacturing databases.

## Database Schema (Use EXACT Column Names):

### production_logs
{self._format_sql_schema('production_logs')}

### quality_control
{self._format_sql_schema('quality_control')}

### maintenance_logs
{self._format_sql_schema('maintenance_logs')}

### inventory_logs
{self._format_sql_schema('inventory_logs')}

## Example Query Pattern:

**Question:** {example['question']}

**SQL Query:**
```sql
{example['sql']}
```

**Why This Works:**
- Direct SELECT with exact column names (Product, Line, Rework_Count)
- Simple WHERE clause with AND/OR conditions
- GROUP BY matches SELECT columns
- AVG() for averaging
- No unnecessary CTEs or subqueries

{methodology_section}
## Your Task:

**Question:** {question}

## SQL Generation Guidelines (Follow Exactly):

1. **Keep It Simple**: Prefer direct SELECT statements over CTEs or subqueries unless absolutely necessary

2. **Column Names**: Use exact case from schema:
   - ✅ Product, Line, Rework_Count, Downtime_Minutes
   - ❌ product, line, rework_count, downtime_minutes

3. **String Values**: Always use single quotes: 'Widget-A', 'Line-1', 'Breakdown'

4. **Date Filtering**:
   - Year: `strftime('%Y', Date) = '2026'` (SQLite) or `EXTRACT(YEAR FROM Date) = 2026` (PostgreSQL)
   - Range: `Date >= '2026-01-01' AND Date <= '2026-12-31'`
   - Relative: `Date >= DATE('now', '-3 months')` or `Date >= DATE('now', '-6 months')`

5. **Aggregations**:
   - AVG(column) for averages
   - SUM(column) for totals
   - COUNT(*) or COUNT(column) for counts
   - Always GROUP BY non-aggregated columns

6. **WHERE Clauses**:
   - Simple: `WHERE Product = 'Widget-A'`
   - Multiple: `WHERE Product = 'Widget-A' AND Line = 'Line-1'`
   - OR: `WHERE (Line = 'Line-1' OR Line = 'Line-2')`
   - Use parentheses for clarity: `WHERE Product = 'X' AND (Line = 'Y' OR Line = 'Z')`

7. **Line_Machine Handling**:
   - To extract Line: `SUBSTRING(Line_Machine, 1, 5)` or `Line_Machine LIKE 'Line-1%'`
   - To extract Machine: `SUBSTRING(Line_Machine FROM POSITION('/') + 1)`

8. **Joins** (only if question requires multiple tables):
   - production_logs ↔ quality_control: `JOIN quality_control ON production_logs.Date = quality_control.Inspection_Date AND production_logs.Product = quality_control.Product`
   - Use table aliases: `FROM production_logs pl JOIN quality_control qc ON ...`

9. **Calculations**:
   - Percentage: `(Wastage_Kg * 1.0 / Consumption_Kg) * 100`
   - Average percentage: `AVG(Wastage_Kg * 1.0 / Consumption_Kg)`
   - Always use `* 1.0` for decimal division

10. **ORDER BY & LIMIT**:
    - `ORDER BY column DESC` for descending
    - `ORDER BY column ASC` for ascending
    - `LIMIT 1` for single result, `LIMIT 3` for top 3

11. **NULL Handling**:
    - Filter NULLs: `WHERE Consumption_Kg IS NOT NULL AND Consumption_Kg > 0`
    - Prevent division by zero: `WHERE Consumption_Kg > 0`

## CRITICAL: Match Expected Format
- Use standard SQL syntax (SQLite/PostgreSQL compatible)
- No table aliases unless joining multiple tables
- Keep queries concise and readable
- Follow the example pattern above

## Response Format:
Return ONLY the SQL query in a ```sql code block. No explanations.

```sql
YOUR SQL QUERY HERE
```
"""
        return prompt
    
    def generate_enhanced_table_selection_prompt(self, question: str) -> str:
        """Generate enhanced table/column selection prompt."""
        example = self.few_shot_examples.get(
            self._identify_question_type(question),
            self.few_shot_examples["simple_aggregation"]
        )
        
        prompt = f"""You are a database expert analyzing MSME manufacturing data queries.

## Available Tables and Columns:

{self._format_all_tables()}

## Example:

**Question:** {example['question']}

**Required Tables:** {', '.join(example['tables'])}
**Required Columns:** {', '.join(example['columns'])}

**Reasoning:**
- The question asks about rework count in a specific line
- quality_control table contains Rework_Count and Line columns
- Product column may be needed if filtering by product

## Your Task:

**Question:** {question}

**Instructions:**
1. Identify which table(s) contain the data needed to answer this question
2. List all columns that will be used (for filtering, grouping, or calculation)
3. Consider if multiple tables need to be joined
4. Think about relationships: production_logs joins with quality_control on Date and Product

**Response Format:**
Return ONLY a JSON object with "tables" (array) and "columns" (array):

```json
{{
  "tables": ["table_name1", "table_name2"],
  "columns": ["Column1", "Column2", "Column3"]
}}
```
"""
        return prompt
    
    def _identify_question_type(self, question: str) -> str:
        """Identify the type of question to select appropriate few-shot example."""
        question_lower = question.lower()
        
        if "correlation" in question_lower or "relationship" in question_lower or "impact" in question_lower:
            return "correlation_analysis"
        elif "top" in question_lower and ("3" in question or "5" in question or "10" in question):
            return "top_n_query"
        elif "differ" in question_lower or "difference" in question_lower or "compare" in question_lower:
            return "complex_query"  # Use complex query example for comparison questions
        elif "2025" in question or "2024" in question or "year" in question_lower:
            return "date_filtering"
        else:
            return "simple_aggregation"
    
    def _format_columns(self, columns: Dict[str, str]) -> str:
        """Format columns dictionary into readable string."""
        return "\n".join(f"- {col}: {desc}" for col, desc in columns.items())
    
    def _format_steps(self, steps: List[str]) -> str:
        """Format methodology steps into numbered list."""
        return "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
    
    def _format_sql_schema(self, table_name: str) -> str:
        """Format table schema for SQL prompt."""
        table_info = self.schema_info[table_name]
        schema = f"Purpose: {table_info['description']}\n"
        schema += "Columns:\n"
        for col, desc in table_info['columns'].items():
            schema += f"  - {col}: {desc}\n"
        return schema
    
    def _format_all_tables(self) -> str:
        """Format all tables information."""
        result = ""
        for table_name, table_info in self.schema_info.items():
            result += f"### {table_name}\n"
            result += f"Purpose: {table_info['description']}\n"
            result += "Columns:\n"
            for col, desc in table_info['columns'].items():
                result += f"  - {col}: {desc}\n"
            result += "\n"
        return result
    
    def query_llm(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.1) -> Tuple[str, float, int]:
        """
        Query the LLM with enhanced prompt.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation (lower = more deterministic)
        
        Returns:
            Tuple of (response_text, latency_ms, tokens_used)
        """
        # Try to initialize client if not already done
        if not self.client:
            if HAS_GROQ:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    try:
                        self.client = Groq(api_key=api_key)
                    except Exception as e:
                        raise RuntimeError(f"Failed to initialize Groq client: {str(e)}")
                else:
                    raise RuntimeError("GROQ_API_KEY not found in environment variables")
            else:
                raise RuntimeError("groq package not installed")
        
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert data analyst and SQL developer specializing in MSME manufacturing operations. Provide precise, accurate responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            latency_ms = (time.time() - start_time) * 1000
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            return response_text, latency_ms, tokens_used
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            raise RuntimeError(f"LLM query failed: {str(e)}")
    
    def test_question(self, question: Dict, prompt_version: str = "enhanced_v1") -> PromptResult:
        """
        Test a question with enhanced prompts.
        
        Args:
            question: Question dictionary with id, question, category, etc.
            prompt_version: Version identifier for the prompt
        
        Returns:
            PromptResult with response and metrics
        """
        question_text = question.get('question', question.get('question_text', ''))
        question_id = question.get('id', question.get('question_id', 'unknown'))
        category = question.get('category', 'Medium')
        
        error = None
        response = ""
        latency_ms = 0
        tokens = 0
        
        try:
            # Generate methodology
            methodology_prompt = self.generate_enhanced_methodology_prompt(question_text, category)
            methodology_response, meth_latency, meth_tokens = self.query_llm(methodology_prompt)
            
            # Extract steps from methodology response
            methodology_steps = self._extract_steps(methodology_response)
            
            # Generate SQL using baseline prompt (same as original benchmark)
            sql_prompt = self.generate_enhanced_sql_prompt(question_text, methodology_steps, version="baseline")
            sql_response, sql_latency, sql_tokens = self.query_llm(sql_prompt)
            
            # Generate table selection
            table_prompt = self.generate_enhanced_table_selection_prompt(question_text)
            table_response, table_latency, table_tokens = self.query_llm(table_prompt)
            
            total_latency = meth_latency + sql_latency + table_latency
            total_tokens = meth_tokens + sql_tokens + table_tokens
            
            response = {
                "methodology": methodology_response,
                "sql": sql_response,
                "table_selection": table_response
            }
            
        except Exception as e:
            error = str(e)
        
        # Note: Score calculation would require evaluation against ground truth
        # This is a placeholder - you'd integrate with your evaluators
        score = 0.0  # Would be calculated by evaluators
        
        return PromptResult(
            question_id=question_id,
            question_text=question_text,
            category=category,
            prompt_version=prompt_version,
            response=json.dumps(response) if isinstance(response, dict) else str(response),
            score=score,
            latency_ms=total_latency if 'total_latency' in locals() else latency_ms,
            tokens=total_tokens if 'total_tokens' in locals() else tokens,
            error=error
        )
    
    def _extract_steps(self, methodology_response: str) -> List[str]:
        """Extract numbered steps from methodology response."""
        steps = []
        lines = methodology_response.split('\n')
        for line in lines:
            line = line.strip()
            # Look for numbered steps (1., 2., etc.)
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering and clean
                step = line.split('.', 1)[-1].strip() if '.' in line else line.lstrip('- ').strip()
                if step and len(step) > 10:  # Filter out very short lines
                    steps.append(step)
        return steps[:10]  # Limit to 10 steps


def main():
    """Main function to test prompt engineering."""
    print("="*70)
    print("Llama 4 Maverick Prompt Engineering Optimizer")
    print("="*70)
    
    # Initialize optimizer
    optimizer = EnhancedPromptEngineer()
    
    # Test with a sample question
    test_question = {
        "id": "test_1",
        "question": "What is the correlation between downtime minutes and failed quantity per line machine and product?",
        "category": "Complex"
    }
    
    print(f"\nTesting question: {test_question['question']}")
    print(f"Category: {test_question['category']}\n")
    
    result = optimizer.test_question(test_question, prompt_version="enhanced_v1")
    
    print(f"Question ID: {result.question_id}")
    print(f"Latency: {result.latency_ms:.0f}ms")
    print(f"Tokens: {result.tokens}")
    if result.error:
        print(f"Error: {result.error}")
    else:
        print("✓ Query successful")
        print(f"\nResponse preview:")
        response_data = json.loads(result.response) if result.response.startswith('{') else {}
        if 'methodology' in response_data:
            print(f"Methodology: {response_data['methodology'][:200]}...")
        if 'sql' in response_data:
            print(f"SQL: {response_data['sql'][:200]}...")


if __name__ == "__main__":
    main()

