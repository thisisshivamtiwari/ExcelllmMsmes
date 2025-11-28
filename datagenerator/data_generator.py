#!/usr/bin/env python3
"""
MSME Shopfloor Manufacturing Data Generator
Uses Google Gemini API to generate realistic, stateful manufacturing data
with preserved relationships and realistic variations.
"""

import os
import json
import csv
import sys
import subprocess
from pathlib import Path

# Try to detect and use Anaconda Python if available
def find_python_with_packages():
    """Find Python interpreter that has required packages installed."""
    python_paths = [
        "/opt/anaconda3/bin/python3",
        os.path.expanduser("~/anaconda3/bin/python3"),
        os.path.expanduser("~/miniconda3/bin/python3"),
    ]
    
    # Check common Anaconda locations first (most likely to have packages)
    for python_path in python_paths:
        if os.path.exists(python_path):
            # Quick test - just check if it can import (with longer timeout)
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
                # If timeout or error, assume it might work (Anaconda Python usually has packages)
                # Return it anyway as it's likely the correct one
                if "anaconda" in python_path.lower() or "miniconda" in python_path.lower():
                    return python_path
                continue
    
    return None

# Check for required packages with helpful error messages
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
        print("\nOr use the helper script:")
        print("  ./run_generator.sh")
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
        print("\nOr use the helper script:")
        print("  ./run_generator.sh")
        sys.exit(1)
    else:
        print("Error: google-generativeai not installed.")
        print("Run: pip install google-generativeai")
        print("\nIf using Anaconda, try: /opt/anaconda3/bin/python3 -m pip install google-generativeai")
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
        print("\nOr use the helper script:")
        print("  ./run_generator.sh")
        sys.exit(1)
    else:
        print("Error: python-dotenv not installed. Run: pip install python-dotenv")
        sys.exit(1)

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    env_file = Path(__file__).parent / ".env"
    print("=" * 60)
    print("ERROR: GEMINI_API_KEY not found!")
    print("=" * 60)
    print(f"\nPlease create a .env file in {Path(__file__).parent}")
    print("Example:")
    print("  1. Copy .env.example to .env:")
    print("     cp .env.example .env")
    print("  2. Edit .env and add your API key:")
    print("     GEMINI_API_KEY=your_actual_api_key_here")
    print("\nGet your API key from: https://makersuite.google.com/app/apikey")
    print("=" * 60)
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Configuration
OUTPUT_DIR = Path("generated_data")
OUTPUT_DIR.mkdir(exist_ok=True)

# Manufacturing domain constants
PRODUCTS = ["Widget-A", "Widget-B", "Widget-C", "Component-X", "Component-Y", "Assembly-Z"]
LINES = ["Line-1", "Line-2", "Line-3"]
SHIFTS = ["Morning", "Afternoon", "Night"]
OPERATORS = ["Rajesh Kumar", "Priya Sharma", "Amit Patel", "Sneha Desai", "Vikram Singh"]
MACHINES = ["Machine-M1", "Machine-M2", "Machine-M3", "Machine-M4", "Machine-M5"]
DEFECT_TYPES = ["Dimensional", "Surface Finish", "Assembly Error", "Material Defect", "Packaging Issue"]
RAW_MATERIALS = ["Steel-101", "Plastic-PVC", "Aluminum-AL", "Rubber-RB", "Copper-CU"]


class MSMEDataGenerator:
    """Generates realistic MSME shopfloor manufacturing data using Gemini API."""
    
    def __init__(self, industry_type: str = "manufacturing", model_name: str = "gemini-2.0-flash"):
        self.industry_type = industry_type
        # Use gemini-2.0-flash (fastest, recommended) or gemini-2.5-flash/gemini-2.5-pro (newer)
        # Older models like gemini-pro and gemini-1.5-* are deprecated
        try:
            self.model = genai.GenerativeModel(model_name)
            print(f"Using model: {model_name}")
        except Exception as e:
            # Fallback to gemini-2.5-flash if 2.0-flash is not available
            print(f"Warning: {model_name} not available, trying gemini-2.5-flash...")
            try:
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                print("Using model: gemini-2.5-flash")
            except Exception as e2:
                # Last fallback to gemini-2.5-pro
                print("Warning: gemini-2.5-flash not available, trying gemini-2.5-pro...")
                try:
                    self.model = genai.GenerativeModel('gemini-2.5-pro')
                    print("Using model: gemini-2.5-pro")
                except Exception as e3:
                    raise Exception(f"Could not initialize Gemini model. Tried {model_name}, gemini-2.5-flash, and gemini-2.5-pro. Error: {e3}")
        self.state = {
            "last_production_date": None,
            "machine_states": {machine: {"last_breakdown": None, "efficiency": 0.85} for machine in MACHINES},
            "product_history": {},
            "operator_performance": {op: 0.80 for op in OPERATORS},
            "seasonal_factor": 1.0
        }
        
    def _load_existing_data(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load existing CSV data if continuing generation."""
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                # Convert date columns to datetime with flexible parsing
                date_columns = [col for col in df.columns if 'date' in col.lower() or col == 'Date']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
                return df
            except Exception as e:
                print(f"Warning: Could not load existing data from {file_path}: {e}")
                return None
        return None
    
    def _update_state_from_existing(self, df: pd.DataFrame, data_type: str):
        """Update internal state based on existing data."""
        if df is None or df.empty:
            return
            
        if data_type == "production":
            if "Date" in df.columns:
                # Handle dates with or without time components
                self.state["last_production_date"] = pd.to_datetime(df["Date"], format='mixed', errors='coerce').max()
            if "Machine" in df.columns and "Actual_Qty" in df.columns and "Target_Qty" in df.columns:
                machine_perf = df.groupby("Machine").apply(
                    lambda x: (x["Actual_Qty"].sum() / x["Target_Qty"].sum()) if x["Target_Qty"].sum() > 0 else 0.85
                )
                for machine, perf in machine_perf.items():
                    if machine in self.state["machine_states"]:
                        self.state["machine_states"][machine]["efficiency"] = min(0.95, max(0.70, perf))
        
        elif data_type == "maintenance":
            if "Machine" in df.columns and "Breakdown_Date" in df.columns:
                # Handle dates with or without time components
                breakdowns = pd.to_datetime(df["Breakdown_Date"], format='mixed', errors='coerce').groupby(df["Machine"]).max()
                for machine, date in breakdowns.items():
                    if machine in self.state["machine_states"]:
                        self.state["machine_states"][machine]["last_breakdown"] = date
    
    def _generate_with_gemini(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini API with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"API call failed, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Gemini API call failed after {max_retries} attempts: {e}")
    
    def _parse_json_response(self, response_text: str) -> List[Dict]:
        """Parse JSON response from Gemini, handling markdown code blocks."""
        # Remove markdown code blocks if present
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        
        try:
            data = json.loads(response_text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return [data]
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON response: {e}")
            print(f"Response text: {response_text[:500]}")
            return []
    
    def generate_production_data(self, num_rows: int, start_date: Optional[datetime] = None, 
                                continue_from_existing: bool = True) -> pd.DataFrame:
        """Generate production log data with stateful relationships."""
        file_path = OUTPUT_DIR / "production_logs.csv"
        existing_df = None
        
        if continue_from_existing:
            existing_df = self._load_existing_data(file_path)
            if existing_df is not None:
                self._update_state_from_existing(existing_df, "production")
                start_date = self.state["last_production_date"] + timedelta(days=1) if self.state["last_production_date"] else datetime.now() - timedelta(days=30)
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        
        all_rows = []
        batch_size = 50
        total_batches = (num_rows + batch_size - 1) // batch_size
        
        for batch_num, batch_start in enumerate(range(0, num_rows, batch_size), 1):
            batch_end = min(batch_start + batch_size, num_rows)
            current_batch_size = batch_end - batch_start
            print(f"  Generating production batch {batch_num}/{total_batches} ({current_batch_size} rows)...", end=" ", flush=True)
            
            # Build context from state
            state_context = {
                "machine_efficiencies": {k: v["efficiency"] for k, v in self.state["machine_states"].items()},
                "operator_performance": self.state["operator_performance"],
                "last_date": start_date.strftime("%Y-%m-%d") if start_date else None
            }
            
            prompt = f"""Generate {current_batch_size} realistic manufacturing production log entries as JSON array.
Each entry should be a JSON object with these exact fields:
- Date (YYYY-MM-DD format, sequential dates starting from {start_date.strftime('%Y-%m-%d') if start_date else 'today'})
- Shift (one of: {', '.join(SHIFTS)})
- Line_Machine (one of: {', '.join([f'{line}/{machine}' for line in LINES for machine in MACHINES[:2]])})
- Product (one of: {', '.join(PRODUCTS)})
- Target_Qty (integer, typically 100-500)
- Actual_Qty (integer, should be close to Target_Qty but vary based on machine efficiency)
- Downtime_Minutes (integer, 0-120, higher if machine recently broke down)
- Operator (one of: {', '.join(OPERATORS)})

Context for realistic generation:
- Machine efficiencies: {state_context['machine_efficiencies']}
- Operator performance: {state_context['operator_performance']}
- Machines with recent breakdowns should have lower Actual_Qty and higher Downtime_Minutes
- Better operators should achieve Actual_Qty closer to Target_Qty
- Create realistic relationships: same operator on same machine, products that were produced together before
- Add some seasonal variation (slightly higher production on certain days)

Return ONLY valid JSON array, no markdown, no explanations."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
                # Ensure dates are sequential starting from start_date
                current_date = start_date
                for row in batch_data:
                    if "Date" in row:
                        row["Date"] = current_date.strftime("%Y-%m-%d")
                        current_date += timedelta(days=1)
                
                all_rows.extend(batch_data)
                # Update state based on generated data
                for row in batch_data:
                    if "Line_Machine" in row:
                        machine = row["Line_Machine"].split("/")[-1] if "/" in row["Line_Machine"] else row["Line_Machine"]
                        if machine in self.state["machine_states"]:
                            if "Actual_Qty" in row and "Target_Qty" in row:
                                efficiency = row["Actual_Qty"] / row["Target_Qty"] if row["Target_Qty"] > 0 else 0.85
                                # Smooth update
                                self.state["machine_states"][machine]["efficiency"] = (
                                    0.7 * self.state["machine_states"][machine]["efficiency"] + 0.3 * efficiency
                                )
                    # Update last production date
                    if "Date" in row:
                        row_date = pd.to_datetime(row["Date"], format='mixed', errors='coerce')
                        if pd.notna(row_date):
                            if self.state["last_production_date"] is None or row_date > self.state["last_production_date"]:
                                self.state["last_production_date"] = row_date
                
                print(f"✓ Generated {len(batch_data)} rows")
            else:
                print("⚠ No data generated")
            
            # Update start_date for next batch
            if batch_data and "Date" in batch_data[-1]:
                last_date = pd.to_datetime(batch_data[-1]["Date"], format='mixed', errors='coerce')
                if pd.notna(last_date):
                    start_date = last_date + timedelta(days=1)
            
            # Small delay to avoid rate limits
            time.sleep(1)
        
        df = pd.DataFrame(all_rows)
        
        # Ensure proper data types
        if "Date" in df.columns:
            # Handle dates with or without time components
            df["Date"] = pd.to_datetime(df["Date"], format='mixed', errors='coerce')
        if "Target_Qty" in df.columns:
            df["Target_Qty"] = pd.to_numeric(df["Target_Qty"], errors='coerce').fillna(0).astype(int)
        if "Actual_Qty" in df.columns:
            df["Actual_Qty"] = pd.to_numeric(df["Actual_Qty"], errors='coerce').fillna(0).astype(int)
        if "Downtime_Minutes" in df.columns:
            df["Downtime_Minutes"] = pd.to_numeric(df["Downtime_Minutes"], errors='coerce').fillna(0).astype(int)
        
        # Append to existing or create new
        if existing_df is not None and not existing_df.empty:
            df = pd.concat([existing_df, df], ignore_index=True)
            # Sort by date to ensure chronological order
            if "Date" in df.columns:
                df = df.sort_values("Date").reset_index(drop=True)
        
        df.to_csv(file_path, index=False)
        print(f"Generated {len(df)} production log entries. Saved to {file_path}")
        return df
    
    def generate_quality_data(self, num_rows: int, production_df: Optional[pd.DataFrame] = None,
                             continue_from_existing: bool = True) -> pd.DataFrame:
        """Generate QC/inspection data linked to production data."""
        file_path = OUTPUT_DIR / "quality_control.csv"
        existing_df = None
        
        if continue_from_existing:
            existing_df = self._load_existing_data(file_path)
        
        if production_df is None:
            production_file = OUTPUT_DIR / "production_logs.csv"
            if production_file.exists():
                production_df = pd.read_csv(production_file)
            else:
                raise ValueError("Production data required. Generate production data first.")
        
        # Ensure proper data types
        if "Date" in production_df.columns:
            production_df["Date"] = pd.to_datetime(production_df["Date"], format='mixed', errors='coerce')
        if "Actual_Qty" in production_df.columns:
            production_df["Actual_Qty"] = pd.to_numeric(production_df["Actual_Qty"], errors='coerce').fillna(0).astype(int)
        
        # Filter out production dates that already have QC entries
        if existing_df is not None and not existing_df.empty:
            if "Inspection_Date" in existing_df.columns:
                existing_df["Inspection_Date"] = pd.to_datetime(existing_df["Inspection_Date"], format='mixed', errors='coerce')
                # Get production dates that already have QC entries (inspection date - 1 day = production date)
                existing_qc_dates = set()
                for qc_date in existing_df["Inspection_Date"].dropna():
                    prod_date = qc_date - timedelta(days=1)
                    existing_qc_dates.add(prod_date.strftime("%Y-%m-%d"))
                
                # Filter production to exclude dates that already have QC
                if existing_qc_dates:
                    production_df["Date_Str"] = production_df["Date"].dt.strftime("%Y-%m-%d")
                    production_df = production_df[~production_df["Date_Str"].isin(existing_qc_dates)]
                    production_df = production_df.drop(columns=["Date_Str"])
                    if production_df.empty:
                        print("  All production dates already have QC entries. No new QC data to generate.")
                        return existing_df
        
        all_rows = []
        batch_size = 50
        
        # Sample from production data to create QC entries (only from dates without existing QC)
        available_production = production_df if not production_df.empty else None
        if available_production is None or len(available_production) == 0:
            print("  No new production data available for QC generation.")
            return existing_df if existing_df is not None else pd.DataFrame()
        
        sampled_production = available_production.sample(min(num_rows, len(available_production)), replace=True)
        total_batches = (len(sampled_production) + batch_size - 1) // batch_size
        
        for batch_num, batch_start in enumerate(range(0, len(sampled_production), batch_size), 1):
            batch_end = min(batch_start + batch_size, len(sampled_production))
            batch_prod = sampled_production.iloc[batch_start:batch_end]
            print(f"  Generating QC batch {batch_num}/{total_batches} ({len(batch_prod)} rows)...", end=" ", flush=True)
            
            # Prepare production context for linking
            prod_context = []
            for idx, prod_row in batch_prod.iterrows():
                line_machine = prod_row.get("Line_Machine", "")
                line = line_machine.split("/")[0] if "/" in line_machine else line_machine
                prod_qty = int(prod_row.get("Actual_Qty", 0))
                # Inspection quantity should be 20-30% of production
                inspected_qty = max(50, min(200, int(prod_qty * 0.25)))
                prod_context.append({
                    "line": line,
                    "product": prod_row.get("Product", ""),
                    "production_qty": prod_qty,
                    "suggested_inspected_qty": inspected_qty
                })
            
            prompt = f"""Generate {len(batch_prod)} quality control inspection entries as JSON array.
Each entry should be a JSON object with these exact fields:
- Inspection_Date (YYYY-MM-DD, will be set from production date)
- Batch_ID (unique identifier like BATCH-001, BATCH-002, etc.)
- Product (will be set from production data)
- Line (will be extracted from production Line_Machine)
- Inspected_Qty (integer, typically 20-30% of production quantity, range 50-200)
- Passed_Qty (integer, should be <= Inspected_Qty, typically 85-98% pass rate)
- Failed_Qty (integer, Inspected_Qty - Passed_Qty)
- Defect_Type (one of: {', '.join(DEFECT_TYPES)}, or "None" if Passed_Qty == Inspected_Qty)
- Rework_Count (integer, 0-20, typically 30-50% of Failed_Qty)
- Inspector_Name (one of: {', '.join(OPERATORS[:3])})

Production context for linking:
{json.dumps(prod_context, indent=2)}

Context:
- Inspected_Qty should be proportional to production Actual_Qty (20-30% of production)
- Some products/lines have higher defect rates (create realistic patterns)
- Defect types should correlate: Dimensional issues often lead to Assembly Errors
- Rework counts should be realistic (not all failures are reworkable)

Return ONLY valid JSON array, no markdown."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
                # Link to production data - extract Line, Product, Date, and link quantities
                for i, row in enumerate(batch_data):
                    if i < len(batch_prod):
                        prod_row = batch_prod.iloc[i]
                        
                        # Link date (inspection happens 1 day after production)
                        if "Date" in prod_row:
                            prod_date = prod_row["Date"]
                            if isinstance(prod_date, str):
                                prod_date = pd.to_datetime(prod_date, format='mixed', errors='coerce')
                            elif not isinstance(prod_date, pd.Timestamp):
                                prod_date = pd.to_datetime(prod_date, format='mixed', errors='coerce')
                            if pd.notna(prod_date):
                                row["Inspection_Date"] = (prod_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        
                        # Link product
                        if "Product" in prod_row:
                            row["Product"] = prod_row["Product"]
                        
                        # Extract and link Line from Line_Machine
                        if "Line_Machine" in prod_row:
                            line_machine = prod_row["Line_Machine"]
                            line = line_machine.split("/")[0] if "/" in line_machine else line_machine
                            row["Line"] = line
                        
                        # Link inspection quantity to production (20-30% of production)
                        if "Actual_Qty" in prod_row:
                            prod_qty = int(prod_row["Actual_Qty"])
                            if "Inspected_Qty" not in row or row.get("Inspected_Qty", 0) == 0:
                                row["Inspected_Qty"] = max(50, min(200, int(prod_qty * 0.25)))
                            # Ensure inspected doesn't exceed production
                            row["Inspected_Qty"] = min(row.get("Inspected_Qty", 100), prod_qty)
                
                all_rows.extend(batch_data)
                print(f"✓ Generated {len(batch_data)} rows")
            else:
                print("⚠ No data generated")
            
            time.sleep(1)
        
        df = pd.DataFrame(all_rows)
        
        # Ensure proper data types
        if "Inspection_Date" in df.columns:
            # Handle dates with or without time components
            df["Inspection_Date"] = pd.to_datetime(df["Inspection_Date"], format='mixed', errors='coerce')
        numeric_cols = ["Inspected_Qty", "Passed_Qty", "Failed_Qty", "Rework_Count"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        if existing_df is not None and not existing_df.empty:
            df = pd.concat([existing_df, df], ignore_index=True)
        
        df.to_csv(file_path, index=False)
        print(f"Generated {len(df)} QC entries. Saved to {file_path}")
        return df
    
    def generate_maintenance_data(self, num_rows: int, production_df: Optional[pd.DataFrame] = None,
                                  continue_from_existing: bool = True) -> pd.DataFrame:
        """Generate maintenance records with breakdowns affecting production."""
        file_path = OUTPUT_DIR / "maintenance_logs.csv"
        existing_df = None
        
        if continue_from_existing:
            existing_df = self._load_existing_data(file_path)
            if existing_df is not None:
                self._update_state_from_existing(existing_df, "maintenance")
        
        if production_df is None:
            production_file = OUTPUT_DIR / "production_logs.csv"
            if production_file.exists():
                production_df = pd.read_csv(production_file)
        
        # Ensure proper data types
        if production_df is not None and not production_df.empty:
            if "Date" in production_df.columns:
                production_df["Date"] = pd.to_datetime(production_df["Date"], format='mixed', errors='coerce')
            if "Downtime_Minutes" in production_df.columns:
                production_df["Downtime_Minutes"] = pd.to_numeric(production_df["Downtime_Minutes"], errors='coerce').fillna(0)
            if "Line_Machine" in production_df.columns:
                # Extract machines from Line_Machine
                production_df["Machine"] = production_df["Line_Machine"].apply(
                    lambda x: x.split("/")[-1] if "/" in str(x) else str(x)
                )
        
        # Find production dates with significant downtime (potential breakdowns)
        breakdown_candidates = []
        if production_df is not None and not production_df.empty:
            high_downtime = production_df[production_df["Downtime_Minutes"] > 60].copy()
            if not high_downtime.empty:
                # Get existing breakdown dates to avoid duplicates
                existing_breakdown_dates = set()
                if existing_df is not None and not existing_df.empty:
                    if "Breakdown_Date" in existing_df.columns:
                        existing_df["Breakdown_Date"] = pd.to_datetime(existing_df["Breakdown_Date"], format='mixed', errors='coerce')
                        for bd_date in existing_df["Breakdown_Date"].dropna():
                            existing_breakdown_dates.add(bd_date.strftime("%Y-%m-%d"))
                
                for idx, row in high_downtime.iterrows():
                    machine = row.get("Machine", "")
                    prod_date_str = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else None
                    # Only add if this breakdown date doesn't already exist
                    if machine and prod_date_str and prod_date_str not in existing_breakdown_dates:
                        breakdown_candidates.append({
                            "date": prod_date_str,
                            "machine": machine,
                            "downtime_minutes": int(row.get("Downtime_Minutes", 0))
                        })
        
        # Get production date range for alignment
        prod_date_range = None
        if production_df is not None and not production_df.empty and "Date" in production_df.columns:
            prod_dates = production_df["Date"].dropna()
            if not prod_dates.empty:
                prod_date_range = {
                    "min": prod_dates.min().strftime("%Y-%m-%d"),
                    "max": prod_dates.max().strftime("%Y-%m-%d")
                }
        
        all_rows = []
        batch_size = 30
        total_batches = (num_rows + batch_size - 1) // batch_size
        
        for batch_num, batch_start in enumerate(range(0, num_rows, batch_size), 1):
            batch_end = min(batch_start + batch_size, num_rows)
            current_batch_size = batch_end - batch_start
            print(f"  Generating maintenance batch {batch_num}/{total_batches} ({current_batch_size} rows)...", end=" ", flush=True)
            
            machine_states_str = json.dumps({k: {
                "last_breakdown": str(v["last_breakdown"]) if v["last_breakdown"] else None,
                "efficiency": v["efficiency"]
            } for k, v in self.state["machine_states"].items()})
            
            prompt = f"""Generate {current_batch_size} maintenance log entries as JSON array.
Each entry should be a JSON object with these exact fields:
- Maintenance_Date (YYYY-MM-DD, must be within production date range: {prod_date_range})
- Machine (one of: {', '.join(MACHINES)})
- Maintenance_Type (one of: "Preventive", "Breakdown", "Routine Check", "Repair")
- Breakdown_Date (YYYY-MM-DD, same as Maintenance_Date if Maintenance_Type is "Breakdown", null otherwise)
- Downtime_Hours (float, 0.5-8.0 for breakdowns, 0-2 for preventive)
- Issue_Description (realistic description like "Bearing failure", "Motor overheating", "Scheduled lubrication", etc.)
- Technician (one of: {', '.join(OPERATORS[:2])})
- Parts_Replaced (comma-separated string like "Bearing-101, Belt-B2" or "None")
- Cost_Rupees (integer, 500-50000, higher for breakdowns)

Context:
- Production date range: {prod_date_range}
- Breakdown candidates from production downtime: {breakdown_candidates[:5] if breakdown_candidates else 'None'}
- Machines with lower efficiency should have more breakdowns
- Machines that recently broke down should have preventive maintenance scheduled
- Breakdown dates should align with production dates that had high downtime (Downtime_Minutes > 60)
- All dates must be within the production date range

Current machine states: {machine_states_str}

Return ONLY valid JSON array, no markdown."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
                # Link breakdown dates to production downtime dates
                for row in batch_data:
                    if row.get("Maintenance_Type") == "Breakdown" and breakdown_candidates:
                        # Try to match breakdown to a production downtime event
                        machine = row.get("Machine", "")
                        if machine:
                            matching_breakdowns = [b for b in breakdown_candidates if b["machine"] == machine]
                            if matching_breakdowns:
                                # Use the first matching breakdown date
                                breakdown = matching_breakdowns[0]
                                row["Breakdown_Date"] = breakdown["date"]
                                row["Maintenance_Date"] = breakdown["date"]
                                # Convert downtime minutes to hours
                                row["Downtime_Hours"] = round(breakdown["downtime_minutes"] / 60.0, 1)
                                breakdown_candidates.remove(breakdown)  # Use each breakdown once
                    
                    # Ensure dates are within production range
                    if prod_date_range and "Maintenance_Date" in row:
                        maint_date = pd.to_datetime(row["Maintenance_Date"], format='mixed', errors='coerce')
                        min_date = pd.to_datetime(prod_date_range["min"])
                        max_date = pd.to_datetime(prod_date_range["max"])
                        if pd.notna(maint_date):
                            if maint_date < min_date:
                                row["Maintenance_Date"] = prod_date_range["min"]
                            elif maint_date > max_date:
                                row["Maintenance_Date"] = prod_date_range["max"]
                
                all_rows.extend(batch_data)
                # Update state
                for row in batch_data:
                    if "Machine" in row and "Breakdown_Date" in row and row.get("Breakdown_Date"):
                        machine = row["Machine"]
                        if machine in self.state["machine_states"]:
                            # Handle dates with or without time components
                            breakdown_date = pd.to_datetime(row["Breakdown_Date"], format='mixed', errors='coerce')
                            if pd.notna(breakdown_date):
                                self.state["machine_states"][machine]["last_breakdown"] = breakdown_date
                                self.state["machine_states"][machine]["efficiency"] *= 0.9  # Efficiency drops after breakdown
                print(f"✓ Generated {len(batch_data)} rows")
            else:
                print("⚠ No data generated")
            
            time.sleep(1)
        
        df = pd.DataFrame(all_rows)
        
        # Ensure proper data types
        date_cols = ["Maintenance_Date", "Breakdown_Date"]
        for col in date_cols:
            if col in df.columns:
                # Handle dates with or without time components
                df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
        
        if "Downtime_Hours" in df.columns:
            df["Downtime_Hours"] = pd.to_numeric(df["Downtime_Hours"], errors='coerce').fillna(0)
        if "Cost_Rupees" in df.columns:
            df["Cost_Rupees"] = pd.to_numeric(df["Cost_Rupees"], errors='coerce').fillna(0).astype(int)
        
        if existing_df is not None and not existing_df.empty:
            df = pd.concat([existing_df, df], ignore_index=True)
        
        df.to_csv(file_path, index=False)
        print(f"Generated {len(df)} maintenance entries. Saved to {file_path}")
        return df
    
    def generate_inventory_data(self, num_rows: int, production_df: Optional[pd.DataFrame] = None,
                                continue_from_existing: bool = True) -> pd.DataFrame:
        """Generate inventory/material consumption data."""
        file_path = OUTPUT_DIR / "inventory_logs.csv"
        existing_df = None
        
        if continue_from_existing:
            existing_df = self._load_existing_data(file_path)
        
        if production_df is None:
            production_file = OUTPUT_DIR / "production_logs.csv"
            if production_file.exists():
                production_df = pd.read_csv(production_file)
        
        # Ensure proper data types and prepare production data for linking
        prod_date_range = None
        daily_production = {}
        product_material_map = {
            "Widget-A": ["Steel-101", "Plastic-PVC"],
            "Widget-B": ["Steel-101", "Aluminum-AL"],
            "Widget-C": ["Plastic-PVC", "Rubber-RB"],
            "Component-X": ["Steel-101", "Copper-CU"],
            "Component-Y": ["Aluminum-AL", "Plastic-PVC"],
            "Assembly-Z": ["Steel-101", "Plastic-PVC", "Rubber-RB"]
        }
        
        if production_df is not None and not production_df.empty:
            if "Date" in production_df.columns:
                production_df["Date"] = pd.to_datetime(production_df["Date"], format='mixed', errors='coerce')
            if "Actual_Qty" in production_df.columns:
                production_df["Actual_Qty"] = pd.to_numeric(production_df["Actual_Qty"], errors='coerce').fillna(0).astype(int)
            
            # Calculate daily production totals by product
            prod_dates = production_df["Date"].dropna()
            if not prod_dates.empty:
                prod_date_range = {
                    "min": prod_dates.min().strftime("%Y-%m-%d"),
                    "max": prod_dates.max().strftime("%Y-%m-%d")
                }
            
            # Group by date and product to calculate daily consumption
            for date, group in production_df.groupby("Date"):
                if pd.notna(date):
                    date_str = date.strftime("%Y-%m-%d")
                    daily_production[date_str] = {}
                    for product, qty in group.groupby("Product")["Actual_Qty"].sum().items():
                        daily_production[date_str][product] = int(qty)
        
        all_rows = []
        batch_size = 50
        total_batches = (num_rows + batch_size - 1) // batch_size
        
        # Sample dates from production for inventory entries
        inventory_dates = []
        if daily_production:
            # Get existing inventory dates/material combinations to avoid duplicates
            existing_inventory_keys = set()
            if existing_df is not None and not existing_df.empty:
                if "Date" in existing_df.columns and "Material_Code" in existing_df.columns:
                    existing_df["Date"] = pd.to_datetime(existing_df["Date"], format='mixed', errors='coerce')
                    for idx, row in existing_df.iterrows():
                        if pd.notna(row["Date"]) and pd.notna(row.get("Material_Code")):
                            key = f"{row['Date'].strftime('%Y-%m-%d')}_{row['Material_Code']}"
                            existing_inventory_keys.add(key)
            
            # Use production dates, sampling evenly, but filter out existing date/material combos
            date_list = sorted(daily_production.keys())
            available_dates = []
            for date in date_list:
                # Check if any materials for this date are already in inventory
                materials_for_date = set()
                prod_data = daily_production.get(date, {})
                for product in prod_data.keys():
                    materials_for_date.update(product_material_map.get(product, []))
                
                # Add date if at least one material combination doesn't exist
                for material in materials_for_date:
                    key = f"{date}_{material}"
                    if key not in existing_inventory_keys:
                        available_dates.append(date)
                        break  # Only need one material to be missing
            
            if not available_dates:
                print("  All production dates already have inventory entries. No new inventory data to generate.")
                return existing_df if existing_df is not None else pd.DataFrame()
            
            step = max(1, len(available_dates) // num_rows) if num_rows > 0 else 1
            inventory_dates = available_dates[::step][:num_rows]
            # Fill remaining with dates from available list
            while len(inventory_dates) < num_rows and available_dates:
                remaining = num_rows - len(inventory_dates)
                inventory_dates.extend(available_dates[:remaining])
        
        for batch_num, batch_start in enumerate(range(0, num_rows, batch_size), 1):
            batch_end = min(batch_start + batch_size, num_rows)
            current_batch_size = batch_end - batch_start
            batch_dates = inventory_dates[batch_start:batch_end] if inventory_dates else []
            print(f"  Generating inventory batch {batch_num}/{total_batches} ({current_batch_size} rows)...", end=" ", flush=True)
            
            # Prepare context for this batch
            batch_context = []
            for date in batch_dates:
                prod_data = daily_production.get(date, {})
                total_production = sum(prod_data.values())
                batch_context.append({
                    "date": date,
                    "products": prod_data,
                    "total_production": total_production,
                    "suggested_consumption": max(100, min(2000, int(total_production * 2)))  # Rough estimate: 2kg per unit
                })
            
            prompt = f"""Generate {current_batch_size} inventory/material consumption entries as JSON array.
Each entry should be a JSON object with these exact fields:
- Date (YYYY-MM-DD, will be set from production dates)
- Material_Code (one of: {', '.join(RAW_MATERIALS)})
- Material_Name (descriptive name like "Steel Sheet 101", "PVC Granules", etc.)
- Opening_Stock_Kg (integer, 1000-10000)
- Consumption_Kg (integer, should correlate with production volume - higher production = higher consumption)
- Received_Kg (integer, 0-5000, periodic replenishments, higher when Opening_Stock is low)
- Closing_Stock_Kg (integer, calculated as Opening_Stock_Kg - Consumption_Kg + Received_Kg)
- Wastage_Kg (integer, 0-100, typically 1-5% of Consumption_Kg)
- Supplier (one of: "Supplier-A", "Supplier-B", "Supplier-C", "Local Vendor")
- Unit_Cost_Rupees (float, 50-500 per kg)

Production context for linking:
{json.dumps(batch_context[:5], indent=2) if batch_context else 'No production data'}

Product-Material mapping:
- Widget-A, Component-X, Assembly-Z use Steel-101
- Widget-A, Widget-C, Component-Y use Plastic-PVC
- Widget-B, Component-Y use Aluminum-AL
- Widget-C, Assembly-Z use Rubber-RB
- Component-X uses Copper-CU

Context:
- Consumption_Kg should correlate with production Actual_Qty (roughly 1-3 kg per unit produced)
- Higher production days should have higher material consumption
- Create realistic stock levels (low stock triggers orders - Received_Kg > 0)
- Wastage should be realistic (some materials have higher wastage)
- Dates must be within production date range: {prod_date_range}

Return ONLY valid JSON array, no markdown."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
                # Link dates and calculate consumption from production
                filtered_batch_data = []
                for i, row in enumerate(batch_data):
                    if i < len(batch_dates):
                        date = batch_dates[i]
                        material_code = row.get("Material_Code", "")
                        
                        # Check if this date/material combination already exists
                        key = f"{date}_{material_code}"
                        if key in existing_inventory_keys:
                            continue  # Skip duplicate
                        
                        row["Date"] = date
                        
                        # Calculate consumption based on production
                        prod_data = daily_production.get(date, {})
                        total_production = sum(prod_data.values())
                        
                        # Determine which materials are needed based on products produced
                        materials_needed = set()
                        for product, qty in prod_data.items():
                            materials_needed.update(product_material_map.get(product, [RAW_MATERIALS[0]]))
                        
                        # If material matches products produced, calculate consumption
                        if material_code in materials_needed and total_production > 0:
                            # Consumption roughly 1-3 kg per unit, depending on material
                            consumption_multiplier = {
                                "Steel-101": 2.5,
                                "Plastic-PVC": 1.5,
                                "Aluminum-AL": 1.8,
                                "Rubber-RB": 1.2,
                                "Copper-CU": 2.0
                            }.get(material_code, 2.0)
                            
                            # Calculate consumption for this material based on products that use it
                            material_consumption = 0
                            for product, qty in prod_data.items():
                                if material_code in product_material_map.get(product, []):
                                    material_consumption += int(qty * consumption_multiplier)
                            
                            if material_consumption > 0:
                                row["Consumption_Kg"] = material_consumption
                        
                        # Ensure closing stock is calculated correctly
                        opening = row.get("Opening_Stock_Kg", 0)
                        consumption = row.get("Consumption_Kg", 0)
                        received = row.get("Received_Kg", 0)
                        row["Closing_Stock_Kg"] = opening - consumption + received
                        
                        filtered_batch_data.append(row)
                
                all_rows.extend(filtered_batch_data)
                print(f"✓ Generated {len(filtered_batch_data)} rows (filtered {len(batch_data) - len(filtered_batch_data)} duplicates)")
            else:
                print("⚠ No data generated")
            
            time.sleep(1)
        
        df = pd.DataFrame(all_rows)
        
        # Ensure proper data types
        if "Date" in df.columns:
            # Handle dates with or without time components
            df["Date"] = pd.to_datetime(df["Date"], format='mixed', errors='coerce')
        
        numeric_cols = ["Opening_Stock_Kg", "Consumption_Kg", "Received_Kg", "Closing_Stock_Kg", "Wastage_Kg"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        if "Unit_Cost_Rupees" in df.columns:
            df["Unit_Cost_Rupees"] = pd.to_numeric(df["Unit_Cost_Rupees"], errors='coerce').fillna(0)
        
        if existing_df is not None and not existing_df.empty:
            df = pd.concat([existing_df, df], ignore_index=True)
        
        df.to_csv(file_path, index=False)
        print(f"Generated {len(df)} inventory entries. Saved to {file_path}")
        return df


def main():
    """Main function to generate all data types."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate MSME shopfloor manufacturing data")
    parser.add_argument("--production-rows", type=int, default=200, help="Number of production log rows")
    parser.add_argument("--qc-rows", type=int, default=150, help="Number of QC entries")
    parser.add_argument("--maintenance-rows", type=int, default=50, help="Number of maintenance entries")
    parser.add_argument("--inventory-rows", type=int, default=100, help="Number of inventory entries")
    parser.add_argument("--no-continue", action="store_true", help="Don't continue from existing files")
    
    args = parser.parse_args()
    
    generator = MSMEDataGenerator(industry_type="manufacturing")
    
    print("=" * 60)
    print("MSME Shopfloor Manufacturing Data Generator")
    print("=" * 60)
    print(f"\nGenerating data with the following configuration:")
    print(f"  - Production logs: {args.production_rows} rows")
    print(f"  - QC entries: {args.qc_rows} rows")
    print(f"  - Maintenance logs: {args.maintenance_rows} rows")
    print(f"  - Inventory logs: {args.inventory_rows} rows")
    print(f"  - Continue from existing: {not args.no_continue}")
    print("\nStarting generation...\n")
    
    try:
        # Generate production data first (others depend on it)
        production_df = generator.generate_production_data(
            args.production_rows,
            continue_from_existing=not args.no_continue
        )
        
        # Generate QC data (linked to production)
        qc_df = generator.generate_quality_data(
            args.qc_rows,
            production_df=production_df,
            continue_from_existing=not args.no_continue
        )
        
        # Generate maintenance data
        maintenance_df = generator.generate_maintenance_data(
            args.maintenance_rows,
            production_df=production_df,
            continue_from_existing=not args.no_continue
        )
        
        # Generate inventory data
        inventory_df = generator.generate_inventory_data(
            args.inventory_rows,
            production_df=production_df,
            continue_from_existing=not args.no_continue
        )
        
        print("\n" + "=" * 60)
        print("Data generation completed successfully!")
        print("=" * 60)
        print(f"\nGenerated files in '{OUTPUT_DIR}' directory:")
        print(f"  - production_logs.csv ({len(production_df)} rows)")
        print(f"  - quality_control.csv ({len(qc_df)} rows)")
        print(f"  - maintenance_logs.csv ({len(maintenance_df)} rows)")
        print(f"  - inventory_logs.csv ({len(inventory_df)} rows)")
        
    except Exception as e:
        print(f"\nError during data generation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
