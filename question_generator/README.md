# MSME Shopfloor Question Generator

Automatically generates categorized questions (Easy, Medium, Complex) with answers and formulas based on analysis of all data files in the `generated_data` directory.

## Features

- **Comprehensive Data Analysis**: Analyzes all CSV files, columns, rows, and relationships
- **Relationship Detection**: Identifies connections between files (dates, products, machines, materials)
- **Categorized Questions**: Generates 35 questions each in Easy, Medium, and Complex categories
- **Duplicate Prevention**: Automatically filters duplicate questions
- **Persistent Storage**: Saves questions to JSON file, preserves existing questions on re-runs
- **Formula Generation**: Provides SQL and Excel formulas for each question
- **Step-by-step Calculations**: Includes detailed calculation methods

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key**:
   - Ensure `GEMINI_API_KEY` is set in `.env` file (same as data generator)
   - Or create `.env` in `question_generator/` directory:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

## Usage

### Basic Usage

```bash
# Using Anaconda Python (recommended)
/opt/anaconda3/bin/python3 question_generator.py

# Or with system Python
python3 question_generator.py
```

### What It Does

1. **Loads Data**: Reads all CSV files from `datagenerator/generated_data/`
2. **Analyzes Schema**: Examines columns, data types, and sample values
3. **Detects Relationships**: Finds connections between files:
   - Date links (production dates → QC dates → maintenance dates)
   - Product links (products across production, QC, inventory)
   - Machine links (machines in production and maintenance)
   - Common columns (shared fields across files)
4. **Generates Questions**: Uses Gemini API to create realistic questions
5. **Categorizes**: Assigns questions to Easy/Medium/Complex based on complexity
6. **Saves**: Stores questions in `generated_questions.json`

## Question Categories

### Easy (35 questions)
- Simple aggregations (SUM, COUNT, AVG) on single tables
- Basic filtering by date ranges or categories
- Finding min/max values
- Example: "What is the total production quantity for Widget-A?"

### Medium (35 questions)
- JOINs between 2-3 tables
- GROUP BY with aggregations
- Date calculations and percentages
- Conditional aggregations
- Example: "What is the defect rate by product line?"

### Complex (35 questions)
- Multi-table JOINs (3+ tables)
- Complex aggregations with subqueries
- Time-series analysis
- Correlation and trend calculations
- Predictive queries
- Example: "What is the correlation between machine downtime and production efficiency?"

## Output Format

Questions are saved in both **JSON** and **CSV** formats:

### JSON Format (`generated_questions.json`)

```json
{
  "metadata": {
    "last_updated": "2025-11-27T...",
    "total_questions": 105,
    "questions_by_category": {
      "Easy": 35,
      "Medium": 35,
      "Complex": 35
    }
  },
  "questions": {
    "Easy": [
      {
        "id": "Easy_1",
        "question": "What is the total production quantity for Widget-A?",
        "category": "Easy",
        "sql_formula": "SELECT SUM(Actual_Qty) FROM production_logs WHERE Product = 'Widget-A'",
        "excel_formula": "=SUMIFS(production_logs[Actual_Qty], production_logs[Product], \"Widget-A\")",
        "calculation_steps": [
          "Filter production_logs for Product = 'Widget-A'",
          "Sum the Actual_Qty column"
        ],
        "answer_format": "integer (total quantity)",
        "related_tables": ["production_logs"],
        "related_columns": ["Product", "Actual_Qty"],
        "created_at": "2025-11-27T..."
      }
    ],
    "Medium": [...],
    "Complex": [...]
  }
}
```

### CSV Format (`generated_questions.csv`)

The CSV file contains all questions in a flat, tabular format with the following columns:
- `id` - Unique question identifier
- `category` - Question category (Easy/Medium/Complex)
- `question` - The question text
- `sql_formula` - SQL query to answer the question
- `excel_formula` - Excel formula to answer the question
- `calculation_steps` - Step-by-step calculation (pipe-separated)
- `answer_format` - Expected answer format
- `related_tables` - Comma-separated list of related tables
- `related_columns` - Comma-separated list of related columns
- `created_at` - Timestamp when question was created

The CSV format is ideal for:
- Importing into Excel or Google Sheets
- Database import
- Spreadsheet analysis
- Easy filtering and sorting

## Duplicate Prevention

- Questions are compared by normalized text (lowercase, trimmed)
- Existing questions are preserved when re-running
- Only new, unique questions are added
- Target: 35 questions per category (will generate only what's needed)

## Re-running

You can run the script multiple times:
- Existing questions are preserved
- Only missing questions are generated
- No duplicates are created
- Questions are appended to existing files (both JSON and CSV)

## Data Files Analyzed

The generator analyzes all CSV files in `datagenerator/generated_data/`:
- `production_logs.csv` - Production data
- `quality_control.csv` - QC/inspection data
- `maintenance_logs.csv` - Maintenance records
- `inventory_logs.csv` - Inventory/material data

## Error Handling

- Gracefully handles missing data files
- Continues if some files fail to load
- Retries API calls with error handling
- Saves progress after each batch

## Requirements

- Python 3.8+
- Google Gemini API key
- pandas
- google-generativeai
- python-dotenv

## Notes

- Uses same Gemini API key as data generator
- Questions are generated using AI, so they may vary between runs
- Each question includes SQL and Excel formulas for flexibility
- Calculation steps help understand the logic

