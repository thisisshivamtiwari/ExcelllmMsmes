"""
Gemini-Powered Smart Column Finder
Uses Gemini API for intelligent column detection and mapping
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_file = Path(__file__).parent.parent / "backend" / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()  # Try project root

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai not available. Install with: pip install google-generativeai")
    GEMINI_AVAILABLE = False


class GeminiColumnFinder:
    """
    Uses Gemini AI to intelligently find and map columns
    No hardcoded keywords - fully AI-powered
    """
    
    def __init__(self):
        self.model = None
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("✅ Gemini Column Finder initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.model = None
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("❌ Gemini API not available - install google-generativeai")
            if not self.api_key:
                logger.warning("❌ GEMINI_API_KEY not found in environment")
    
    def find_columns(
        self, 
        available_columns: List[str], 
        purpose: str,
        data_context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Use Gemini to find the best columns for a specific purpose
        
        Args:
            available_columns: List of column names from the CSV
            purpose: What we need columns for (e.g., "calculate efficiency", "find products", "calculate cost")
            data_context: Optional context about the data (e.g., "manufacturing production data")
            
        Returns:
            Dictionary mapping purpose keys to column names
        """
        if not self.model:
            logger.warning("Gemini not available, using fallback")
            return self._fallback_column_finder(available_columns, purpose)
        
        try:
            prompt = self._build_column_finding_prompt(available_columns, purpose, data_context)
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            logger.info(f"✅ Gemini found columns for '{purpose}': {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error using Gemini for column finding: {e}")
            return self._fallback_column_finder(available_columns, purpose)
    
    def _build_column_finding_prompt(
        self, 
        available_columns: List[str], 
        purpose: str,
        data_context: Optional[str]
    ) -> str:
        """Build prompt for Gemini to find columns"""
        
        context_str = f"Data context: {data_context}\n" if data_context else ""
        
        prompt = f"""You are an expert data analyst. Given a list of column names from a CSV file, identify which columns should be used for a specific purpose.

{context_str}
Available columns: {', '.join(available_columns)}

Task: {purpose}

Based on the column names and the task, identify the most appropriate columns to use. Return your answer as a JSON object.

Examples of tasks and expected responses:

Task: "calculate efficiency (actual vs target)"
Response: {{"actual_column": "Actual_Qty", "target_column": "Target_Qty"}}

Task: "find product names"
Response: {{"product_column": "Product"}}

Task: "calculate total cost"
Response: {{"cost_column": "Cost_Rupees"}}

Task: "group by production line"
Response: {{"line_column": "Line_Machine"}}

Task: "analyze time series data"
Response: {{"date_column": "Date", "value_column": "Actual_Qty"}}

Task: "calculate quality metrics"
Response: {{"passed_column": "Passed_Qty", "failed_column": "Failed_Qty", "inspected_column": "Inspected_Qty"}}

Now, for the given task "{purpose}", analyze the available columns and return ONLY a JSON object with the appropriate column mappings. Use semantic understanding to match column names to their likely purpose.

Important:
1. Return ONLY valid JSON, no additional text
2. Use descriptive key names (e.g., "product_column", "quantity_column", "date_column")
3. If a column doesn't exist for the task, omit it from the response
4. Column names are case-sensitive - use exact names from the available columns list
5. If multiple columns could work, choose the most relevant one

JSON Response:"""
        
        return prompt
    
    def _fallback_column_finder(
        self, 
        available_columns: List[str], 
        purpose: str
    ) -> Dict[str, str]:
        """
        Fallback keyword-based column finder when Gemini is not available
        """
        result = {}
        purpose_lower = purpose.lower()
        
        # Convert columns to lowercase for matching
        col_map = {col.lower(): col for col in available_columns}
        
        # Common patterns
        patterns = {
            'quantity': ['qty', 'quantity', 'amount', 'total', 'count', 'units'],
            'actual': ['actual', 'real', 'achieved'],
            'target': ['target', 'planned', 'goal'],
            'product': ['product', 'item', 'sku', 'part', 'component'],
            'date': ['date', 'time', 'timestamp', 'day', 'period'],
            'cost': ['cost', 'price', 'amount', 'rupees', 'dollar', 'value'],
            'line': ['line', 'machine', 'station', 'cell'],
            'defect': ['defect', 'failure', 'reject', 'fail'],
            'passed': ['passed', 'good', 'ok', 'success'],
            'failed': ['failed', 'bad', 'reject', 'defect'],
            'inspected': ['inspected', 'checked', 'total'],
        }
        
        # Find columns based on purpose
        if 'efficiency' in purpose_lower or 'actual' in purpose_lower or 'target' in purpose_lower:
            for col_lower, col_original in col_map.items():
                if any(p in col_lower for p in patterns['actual']):
                    result['actual_column'] = col_original
                if any(p in col_lower for p in patterns['target']):
                    result['target_column'] = col_original
        
        if 'product' in purpose_lower:
            for col_lower, col_original in col_map.items():
                if any(p in col_lower for p in patterns['product']):
                    result['product_column'] = col_original
                    break
        
        if 'cost' in purpose_lower or 'price' in purpose_lower:
            for col_lower, col_original in col_map.items():
                if any(p in col_lower for p in patterns['cost']):
                    result['cost_column'] = col_original
                    break
        
        if 'date' in purpose_lower or 'time' in purpose_lower or 'trend' in purpose_lower:
            for col_lower, col_original in col_map.items():
                if any(p in col_lower for p in patterns['date']):
                    result['date_column'] = col_original
                    break
        
        if 'quantity' in purpose_lower:
            for col_lower, col_original in col_map.items():
                if any(p in col_lower for p in patterns['quantity']):
                    result['quantity_column'] = col_original
                    break
        
        if 'quality' in purpose_lower:
            for col_lower, col_original in col_map.items():
                if any(p in col_lower for p in patterns['passed']):
                    result['passed_column'] = col_original
                if any(p in col_lower for p in patterns['failed']):
                    result['failed_column'] = col_original
                if any(p in col_lower for p in patterns['inspected']):
                    result['inspected_column'] = col_original
        
        logger.info(f"Fallback column finder for '{purpose}': {result}")
        return result
    
    def analyze_data_structure(
        self, 
        columns: List[str],
        sample_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Use Gemini to analyze overall data structure and suggest insights
        
        Args:
            columns: List of column names
            sample_data: Optional sample rows for better analysis
            
        Returns:
            Dictionary with analysis results
        """
        if not self.model:
            return {"error": "Gemini not available"}
        
        try:
            sample_str = ""
            if sample_data and len(sample_data) > 0:
                # Include first 3 rows as examples
                sample_str = "\nSample data (first 3 rows):\n"
                for i, row in enumerate(sample_data[:3], 1):
                    sample_str += f"Row {i}: {json.dumps(row, default=str)}\n"
            
            prompt = f"""Analyze this dataset structure and provide insights:

Columns: {', '.join(columns)}
{sample_str}

Please provide:
1. What type of data is this? (e.g., sales, manufacturing, HR, inventory)
2. What are the key metrics that can be calculated?
3. What are the categorical dimensions for grouping?
4. What are the numeric measures?
5. What are the time-based columns?
6. What interesting analyses or visualizations would be useful?

Return your analysis as JSON with keys: data_type, key_metrics, categorical_columns, numeric_columns, date_columns, suggested_analyses

JSON Response:"""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            logger.info(f"✅ Gemini analyzed data structure: {result.get('data_type', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing data structure with Gemini: {e}")
            return {"error": str(e)}


def test_gemini_column_finder():
    """Test the Gemini column finder"""
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    finder = GeminiColumnFinder()
    
    if not finder.model:
        print("❌ Gemini not available. Cannot run tests.")
        sys.exit(1)
    
    # Test 1: Production data
    print("\n" + "="*80)
    print("TEST 1: Production Data")
    print("="*80)
    
    production_columns = [
        "Date", "Shift", "Line_Machine", "Product", 
        "Target_Qty", "Actual_Qty", "Downtime_Minutes", "Operator"
    ]
    
    result = finder.find_columns(
        production_columns,
        "calculate efficiency (actual vs target)",
        "manufacturing production data"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 2: Quality data
    print("\n" + "="*80)
    print("TEST 2: Quality Control Data")
    print("="*80)
    
    quality_columns = [
        "Inspection_Date", "Batch_ID", "Product", "Line",
        "Inspected_Qty", "Passed_Qty", "Failed_Qty", "Defect_Type"
    ]
    
    result = finder.find_columns(
        quality_columns,
        "calculate quality metrics (pass rate and defects)",
        "quality control inspection data"
    )
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 3: Data structure analysis
    print("\n" + "="*80)
    print("TEST 3: Data Structure Analysis")
    print("="*80)
    
    sample_data = [
        {"Date": "2024-01-01", "Product": "Widget-A", "Target_Qty": 100, "Actual_Qty": 95},
        {"Date": "2024-01-02", "Product": "Widget-B", "Target_Qty": 150, "Actual_Qty": 140},
    ]
    
    analysis = finder.analyze_data_structure(production_columns, sample_data)
    print(f"Analysis: {json.dumps(analysis, indent=2)}")


if __name__ == "__main__":
    test_gemini_column_finder()

