# Troubleshooting 500 Internal Server Errors

## Quick Diagnostic Steps

### 1. Check Backend Logs
When you run `python3 main.py`, watch the console output. You should see:
- `INFO` messages for successful operations
- `ERROR` messages with detailed error information
- Full tracebacks showing where errors occur

### 2. Test Backend Status
```bash
# Test if backend is running
curl http://localhost:8000/api/health

# Test file upload system
curl http://localhost:8000/api/files/test
```

### 3. Check Browser Console
Open browser DevTools (F12):
- **Console tab**: Look for JavaScript errors
- **Network tab**: 
  - Click on the failed request
  - Check "Response" tab for error details
  - Check "Headers" for request details

### 4. Common Causes

#### A. File Reading Issue
**Symptom**: Error during `await file.read()`
**Solution**: Check if file is being sent correctly from frontend

#### B. Metadata Extraction Failure
**Symptom**: Error in `metadata_extractor.extract_metadata()`
**Possible causes**:
- File is corrupted
- File is too large
- Pandas can't parse the file
**Check**: Can you open the file manually in Excel/LibreOffice?

#### C. File Validation Failure
**Symptom**: Error in `file_validator.validate_file()`
**Possible causes**:
- File format mismatch
- File is corrupted
- Encoding issues
**Check**: File extension matches actual content

#### D. Disk/IO Issues
**Symptom**: Error saving file
**Possible causes**:
- Disk full
- Permission denied
- Path doesn't exist
**Check**: 
```bash
df -h .
ls -la uploaded_files/
```

### 5. Debugging Steps

#### Step 1: Check Test Endpoint
```bash
curl http://localhost:8000/api/files/test
```
Should return:
```json
{
  "status": "ok",
  "message": "File upload system is ready",
  "tests": {
    "excel_loader": true,
    "file_validator": true,
    "metadata_extractor": true,
    "uploaded_files_dir_exists": true,
    "uploaded_files_dir_writable": true
  }
}
```

#### Step 2: Check Backend Logs
Look for ERROR messages when upload fails. The log will show:
- Exact error message
- Error type
- Full traceback
- File ID (if generated)

#### Step 3: Test with Small File
Try uploading a very small CSV file (few rows):
```csv
Name,Age
Alice,25
Bob,30
```

#### Step 4: Check File Manually
- Can you open the file in Excel/LibreOffice?
- Is the file actually CSV/Excel format?
- Check file size (not 0 bytes)

### 6. Error Response Format

When a 500 error occurs, the response should now include:
```json
{
  "detail": {
    "message": "Error uploading file",
    "error": "Actual error message",
    "error_type": "ExceptionType",
    "file_id": "uuid-if-generated",
    "filename": "original-filename"
  }
}
```

### 7. What to Share for Debugging

If errors persist, share:
1. **Backend console output** - The ERROR message and traceback
2. **File details**:
   - File size
   - File type (.csv, .xlsx)
   - Number of rows/columns
   - Can you open it manually?
3. **Test endpoint response**:
   ```bash
   curl http://localhost:8000/api/files/test
   ```
4. **Browser console errors** - Any JavaScript errors
5. **Network tab** - Request/Response details

### 8. Quick Fixes

```bash
# 1. Ensure directory exists and is writable
mkdir -p uploaded_files
chmod 755 uploaded_files

# 2. Check disk space
df -h .

# 3. Restart backend
# Kill existing process (Ctrl+C) and restart:
cd backend
python3 main.py

# 4. Check Python dependencies
pip install pandas openpyxl python-dateutil chardet python-multipart
```

### 9. Enable Debug Mode

Set environment variable for more detailed errors:
```bash
export DEBUG=true
python3 backend/main.py
```

This will include tracebacks in error responses.

---

## Next Steps

1. **Restart backend** and watch console output
2. **Try uploading a file** and note the ERROR message
3. **Check test endpoint**: `GET /api/files/test`
4. **Share the error message** from backend logs for further debugging

The improved error handling should now provide detailed error information to help diagnose the issue.

