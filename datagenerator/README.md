# MSME Shopfloor Manufacturing Data Generator

This module generates realistic, stateful manufacturing data for MSME shopfloor operations using Google Gemini API. The generator creates interconnected datasets with preserved relationships and realistic variations.

## Features

- **Stateful Generation**: Each batch references previous data to maintain consistency
- **Relationship Preservation**: 
  - Machines that broke down show reduced efficiency in production
  - Products produced together maintain relationships
  - Operator performance affects production outcomes
- **Realistic Variations**: Story-driven data generation, not random
- **Multiple Data Types**: Production logs, QC reports, maintenance records, and inventory data

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key**:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Edit `.env` and add your API key:
     ```
     GEMINI_API_KEY=your_actual_api_key_here
     ```
   
   **Note**: Without a valid API key, the script will fail with an error.

## Usage

### Important: Python Environment

**If you're using Anaconda/Conda**, make sure to use the conda Python:
```bash
# Use Anaconda Python (recommended)
/opt/anaconda3/bin/python3 data_generator.py

# Or activate conda environment first
conda activate base
python data_generator.py
```

**Or use the helper script** (automatically detects correct Python):
```bash
./run_generator.sh
```

### Basic Usage

Generate default amounts of all data types:
```bash
# Using helper script (recommended)
./run_generator.sh

# Or directly with Python
python3 data_generator.py
```

### Custom Configuration

Generate specific amounts of each data type:
```bash
python data_generator.py \
  --production-rows 500 \
  --qc-rows 300 \
  --maintenance-rows 100 \
  --inventory-rows 200
```

### Fresh Start

Generate new data without continuing from existing files:
```bash
python data_generator.py --no-continue
```

## Generated Data Files

All generated CSV files are saved in the `generated_data/` directory:

1. **production_logs.csv**
   - Date, Shift, Line_Machine, Product
   - Target_Qty, Actual_Qty, Downtime_Minutes
   - Operator

2. **quality_control.csv**
   - Inspection_Date, Batch_ID, Product, Line
   - Inspected_Qty, Passed_Qty, Failed_Qty
   - Defect_Type, Rework_Count, Inspector_Name

3. **maintenance_logs.csv**
   - Maintenance_Date, Machine, Maintenance_Type
   - Breakdown_Date, Downtime_Hours
   - Issue_Description, Technician, Parts_Replaced, Cost_Rupees

4. **inventory_logs.csv**
   - Date, Material_Code, Material_Name
   - Opening_Stock_Kg, Consumption_Kg, Received_Kg
   - Closing_Stock_Kg, Wastage_Kg, Supplier, Unit_Cost_Rupees

## Data Relationships

The generator maintains realistic relationships:

- **Machine Efficiency**: Machines with recent breakdowns show lower production efficiency
- **Product Patterns**: Products produced together maintain relationships across batches
- **Operator Performance**: Better operators achieve Actual_Qty closer to Target_Qty
- **Defect Correlation**: Certain defect types correlate (e.g., Dimensional → Assembly Error)
- **Maintenance Impact**: Breakdowns affect production data in subsequent days

## Incremental Generation

By default, the generator continues from existing data:
- Loads existing CSV files if present
- Updates internal state based on existing data
- Appends new data maintaining relationships
- Preserves machine states, operator performance, and product history

## API Rate Limits

The generator includes:
- Automatic retry logic for API failures
- Rate limiting delays between batches
- Batch processing (50-100 rows per API call)

## Error Handling

- Invalid JSON responses are logged with warnings
- Missing data files are handled gracefully
- API failures trigger retries with exponential backoff

## Example Output

```bash
$ python data_generator.py --production-rows 200

============================================================
MSME Shopfloor Manufacturing Data Generator
============================================================

Generating data with the following configuration:
  - Production logs: 200 rows
  - QC entries: 150 rows
  - Maintenance logs: 50 rows
  - Inventory logs: 100 rows
  - Continue from existing: True

Starting generation...

Generated 200 production log entries. Saved to generated_data/production_logs.csv
Generated 150 QC entries. Saved to generated_data/quality_control.csv
Generated 50 maintenance entries. Saved to generated_data/maintenance_logs.csv
Generated 100 inventory entries. Saved to generated_data/inventory_logs.csv

============================================================
Data generation completed successfully!
============================================================

Generated files in 'generated_data' directory:
  - production_logs.csv (200 rows)
  - quality_control.csv (150 rows)
  - maintenance_logs.csv (50 rows)
  - inventory_logs.csv (100 rows)
```

## Notes

- The generator uses Google Gemini API, which requires internet connection
- API calls consume credits based on your Google AI Studio plan
- Generated data is synthetic but designed to mimic real MSME shopfloor patterns
- All dates are sequential and relationships are preserved across data types
- **Important**: Use Anaconda Python (`/opt/anaconda3/bin/python3`) or activate conda environment before running
- The script automatically uses the latest available Gemini model (gemini-2.0-flash or newer)

## Troubleshooting

**If you get "ModuleNotFoundError"**:
- Make sure you're using Anaconda Python: `/opt/anaconda3/bin/python3 data_generator.py`
- Or use the helper script: `./run_generator.sh`

**If you get "404 model not found"**:
- The script now automatically tries newer models (gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro)
- This should be resolved automatically, but if issues persist, check your API key permissions

