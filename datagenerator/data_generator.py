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
                print(f"✓ Generated {len(batch_data)} rows")
            else:
                print("⚠ No data generated")
            
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
        
        all_rows = []
        batch_size = 50
        
        # Sample from production data to create QC entries
        sampled_production = production_df.sample(min(num_rows, len(production_df)), replace=True)
        total_batches = (len(sampled_production) + batch_size - 1) // batch_size
        
        for batch_num, batch_start in enumerate(range(0, len(sampled_production), batch_size), 1):
            batch_end = min(batch_start + batch_size, len(sampled_production))
            batch_prod = sampled_production.iloc[batch_start:batch_end]
            print(f"  Generating QC batch {batch_num}/{total_batches} ({len(batch_prod)} rows)...", end=" ", flush=True)
            
            prompt = f"""Generate {len(batch_prod)} quality control inspection entries as JSON array.
Each entry should be a JSON object with these exact fields:
- Inspection_Date (YYYY-MM-DD, same or day after production date)
- Batch_ID (unique identifier like BATCH-001, BATCH-002, etc.)
- Product (from production data: {batch_prod['Product'].unique().tolist() if 'Product' in batch_prod.columns else PRODUCTS})
- Line (one of: {', '.join(LINES)})
- Inspected_Qty (integer, typically 50-200)
- Passed_Qty (integer, should be <= Inspected_Qty, typically 85-98% pass rate)
- Failed_Qty (integer, Inspected_Qty - Passed_Qty)
- Defect_Type (one of: {', '.join(DEFECT_TYPES)}, or "None" if Passed_Qty == Inspected_Qty)
- Rework_Count (integer, 0-20, typically 30-50% of Failed_Qty)
- Inspector_Name (one of: {', '.join(OPERATORS[:3])})

Context:
- Products with higher production volumes should have proportionally more inspections
- Some products/lines have higher defect rates (create realistic patterns)
- Defect types should correlate: Dimensional issues often lead to Assembly Errors
- Rework counts should be realistic (not all failures are reworkable)

Return ONLY valid JSON array, no markdown."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
                # Link to production dates
                for i, row in enumerate(batch_data):
                    if i < len(batch_prod) and "Date" in batch_prod.columns:
                        prod_date = batch_prod.iloc[i]["Date"]
                        if isinstance(prod_date, str):
                            prod_date = pd.to_datetime(prod_date, format='mixed', errors='coerce')
                        elif not isinstance(prod_date, pd.Timestamp):
                            prod_date = pd.to_datetime(prod_date, format='mixed', errors='coerce')
                        if pd.notna(prod_date):
                            row["Inspection_Date"] = (prod_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        if "Product" in batch_prod.columns:
                            row["Product"] = batch_prod.iloc[i]["Product"]
                
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
- Maintenance_Date (YYYY-MM-DD)
- Machine (one of: {', '.join(MACHINES)})
- Maintenance_Type (one of: "Preventive", "Breakdown", "Routine Check", "Repair")
- Breakdown_Date (YYYY-MM-DD, same as Maintenance_Date if Maintenance_Type is "Breakdown", null otherwise)
- Downtime_Hours (float, 0.5-8.0 for breakdowns, 0-2 for preventive)
- Issue_Description (realistic description like "Bearing failure", "Motor overheating", "Scheduled lubrication", etc.)
- Technician (one of: {', '.join(OPERATORS[:2])})
- Parts_Replaced (comma-separated string like "Bearing-101, Belt-B2" or "None")
- Cost_Rupees (integer, 500-50000, higher for breakdowns)

Context:
- Machines with lower efficiency should have more breakdowns
- Machines that recently broke down should have preventive maintenance scheduled
- Create realistic patterns: some machines break down more frequently
- Preventive maintenance should reduce future breakdowns
- Breakdown dates should correlate with production downtime

Current machine states: {machine_states_str}

Return ONLY valid JSON array, no markdown."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
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
        
        all_rows = []
        batch_size = 50
        total_batches = (num_rows + batch_size - 1) // batch_size
        
        for batch_num, batch_start in enumerate(range(0, num_rows, batch_size), 1):
            batch_end = min(batch_start + batch_size, num_rows)
            current_batch_size = batch_end - batch_start
            print(f"  Generating inventory batch {batch_num}/{total_batches} ({current_batch_size} rows)...", end=" ", flush=True)
            
            prompt = f"""Generate {current_batch_size} inventory/material consumption entries as JSON array.
Each entry should be a JSON object with these exact fields:
- Date (YYYY-MM-DD)
- Material_Code (one of: {', '.join(RAW_MATERIALS)})
- Material_Name (descriptive name like "Steel Sheet 101", "PVC Granules", etc.)
- Opening_Stock_Kg (integer, 1000-10000)
- Consumption_Kg (integer, 100-2000, should correlate with production volume)
- Received_Kg (integer, 0-5000, periodic replenishments)
- Closing_Stock_Kg (integer, calculated as Opening_Stock_Kg - Consumption_Kg + Received_Kg)
- Wastage_Kg (integer, 0-100, typically 1-5% of Consumption_Kg)
- Supplier (one of: "Supplier-A", "Supplier-B", "Supplier-C", "Local Vendor")
- Unit_Cost_Rupees (float, 50-500 per kg)

Context:
- Higher production should correlate with higher material consumption
- Create realistic stock levels (low stock triggers orders)
- Wastage should be realistic (some materials have higher wastage)
- Material consumption should vary by product type

Return ONLY valid JSON array, no markdown."""

            response = self._generate_with_gemini(prompt)
            batch_data = self._parse_json_response(response)
            
            if batch_data:
                all_rows.extend(batch_data)
                print(f"✓ Generated {len(batch_data)} rows")
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
