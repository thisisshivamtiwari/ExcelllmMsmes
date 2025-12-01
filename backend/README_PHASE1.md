# Backend Setup for Phase 1

## Installation

Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

Or install Excel Parser dependencies separately:
```bash
pip install pandas openpyxl python-dateutil chardet
```

## Running the Backend

**Option 1: From project root (Recommended)**
```bash
cd /Users/shivamtiwari/Softwares/ExcelllmMsmes
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Option 2: From backend directory**
```bash
cd backend
python3 main.py
```

**Option 3: Using uvicorn directly**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Testing File Upload API

Once backend is running, test the endpoints:

1. **Upload a file:**
```bash
curl -X POST "http://localhost:8000/api/files/upload" \
  -F "file=@/path/to/your/file.csv"
```

2. **List uploaded files:**
```bash
curl "http://localhost:8000/api/files/list"
```

3. **Get file metadata:**
```bash
curl "http://localhost:8000/api/files/{file_id}/metadata"
```

## Troubleshooting

### ModuleNotFoundError: No module named 'chardet'
```bash
pip install chardet
```

### ModuleNotFoundError: No module named 'excel_parser'
Make sure you're running from the project root, or the Python path includes the project root.

### Import errors
The backend adds the project root to sys.path automatically, but if you're running tests or scripts directly, you may need to:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

