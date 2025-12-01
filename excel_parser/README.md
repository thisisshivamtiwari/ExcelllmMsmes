# Excel Parser Module

Phase 1: Excel Parser & Data Loading

## Overview

This module provides functionality for loading, validating, and extracting metadata from Excel (.xlsx, .xls) and CSV files.

## Components

### 1. ExcelLoader (`excel_loader.py`)
- Load `.xlsx` files with multiple sheets support
- Load `.csv` files
- Handle large files with chunking (>100MB)
- Preserve data types during loading
- Error handling for corrupted files

### 2. FileValidator (`file_validator.py`)
- Validate file format (.xlsx, .csv)
- Check file size limits (max 100MB)
- Verify file is not corrupted (magic bytes check)
- Detect encoding (UTF-8, etc.) using chardet

### 3. MetadataExtractor (`metadata_extractor.py`)
- Extract file metadata (name, size, modified date)
- Count rows and columns (with estimation for large files)
- Detect file encoding
- Extract sheet names (for Excel files)
- Include sample data option

## Usage

```python
from excel_parser.excel_loader import ExcelLoader
from excel_parser.file_validator import FileValidator
from excel_parser.metadata_extractor import MetadataExtractor
from pathlib import Path

# Initialize
loader = ExcelLoader()
validator = FileValidator()
extractor = MetadataExtractor()

# Validate file
file_path = Path("data.csv")
validation = validator.validate_file(file_path)
if validation['is_valid']:
    # Extract metadata
    metadata = extractor.extract_metadata(file_path)
    
    # Load file
    result = loader.load_file(file_path)
    if result['error'] is None:
        df = result['data']  # DataFrame
        print(f"Loaded {len(df)} rows")
```

## API Endpoints

- `POST /api/files/upload` - Upload Excel/CSV files
- `GET /api/files/list` - List all uploaded files
- `GET /api/files/{file_id}` - Get file info
- `GET /api/files/{file_id}/metadata` - Get file metadata
- `POST /api/files/{file_id}/load` - Load file data (preview)
- `DELETE /api/files/{file_id}` - Delete uploaded file

## Dependencies

See `requirements.txt`:
- pandas>=2.0.0
- openpyxl>=3.1.0
- python-dateutil>=2.8.0
- chardet>=5.0.0

## Testing

Run tests with pytest:
```bash
pytest tests/excel_parser/
```

## Status

✅ Phase 1 Complete
- Excel loader implemented
- File validator implemented
- Metadata extractor implemented
- Unit tests written
- Backend API endpoints added
- Frontend integration complete

