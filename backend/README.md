# ExcelLLM Data Generator Backend API

FastAPI backend for triggering the data generator from the frontend.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

### POST /api/generate
Trigger data generation with custom parameters.

**Request Body:**
```json
{
  "production_rows": 200,
  "qc_rows": 150,
  "maintenance_rows": 50,
  "inventory_rows": 100,
  "no_continue": false
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Data generation completed successfully",
  "output": "...",
  "files": {
    "production_logs.csv": 200,
    "quality_control.csv": 150,
    "maintenance_logs.csv": 50,
    "inventory_logs.csv": 100
  }
}
```

### GET /api/files
Get list of generated files with row counts.

**Response:**
```json
{
  "files": {
    "production_logs.csv": {
      "rows": 200,
      "size_bytes": 12345,
      "exists": true
    },
    ...
  }
}
```

### GET /api/health
Health check endpoint.


