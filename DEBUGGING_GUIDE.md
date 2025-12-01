# Debugging Guide - File Upload Issues

## Common Issues and Solutions

### 1. Intermittent 500 Errors

**Symptoms:**
- Sometimes upload works (200 OK)
- Sometimes fails with 500 Internal Server Error
- No clear pattern

**Possible Causes:**

#### A. File Size Issues
- **Check:** Large files (>50MB) may timeout
- **Solution:** Check file size before upload
- **Debug:** Look for timeout errors in logs

#### B. Disk Space
- **Check:** `df -h` to check disk space
- **Solution:** Ensure enough disk space in `uploaded_files/` directory
- **Debug:** Check for "No space left on device" errors

#### C. File Permissions
- **Check:** `ls -la uploaded_files/`
- **Solution:** Ensure directory is writable: `chmod 755 uploaded_files/`
- **Debug:** Check for "Permission denied" errors

#### D. Concurrent Uploads
- **Check:** Multiple files uploaded simultaneously
- **Solution:** Check for race conditions in file ID generation
- **Debug:** Look for file locking errors

#### E. Memory Issues
- **Check:** Large files loading into memory
- **Solution:** Use chunking for large files
- **Debug:** Monitor memory usage during upload

### 2. How to Debug

#### Check Backend Logs
```bash
# When running backend, logs will show:
# - File upload start
# - File save operations
# - Validation results
# - Metadata extraction
# - Errors with tracebacks
```

#### Test File Upload Manually
```bash
# Test with curl
curl -X POST "http://localhost:8000/api/files/upload" \
  -F "file=@/path/to/test.csv" \
  -v

# Check response
# - Status code
# - Error message
# - Response body
```

#### Check File System
```bash
# Check uploaded_files directory
ls -lh uploaded_files/

# Check disk space
df -h .

# Check permissions
ls -la uploaded_files/
```

#### Monitor Backend Output
When running `python3 main.py`, watch for:
- `INFO` messages (normal operations)
- `WARNING` messages (potential issues)
- `ERROR` messages (failures)
- Tracebacks (detailed error info)

### 3. Things to Check

#### ✅ File Format
- Is the file actually .xlsx, .xls, or .csv?
- Check file extension matches content
- Try opening file in Excel/LibreOffice

#### ✅ File Integrity
- Is the file corrupted?
- Can you open it manually?
- Check file size (not 0 bytes)

#### ✅ Backend Status
- Is backend running?
- Check `http://localhost:8000/docs` (FastAPI docs)
- Test health endpoint: `GET /api/health`

#### ✅ Network Issues
- CORS errors in browser console?
- Network timeout?
- Check browser DevTools → Network tab

#### ✅ File Content
- Empty files?
- Files with only headers?
- Files with special characters in names?

### 4. Testing Checklist

- [ ] Small CSV file (<1MB)
- [ ] Medium CSV file (1-10MB)
- [ ] Large CSV file (>10MB)
- [ ] Excel file (.xlsx)
- [ ] Excel file with multiple sheets
- [ ] File with special characters in name
- [ ] Empty file (should fail validation)
- [ ] Corrupted file (should fail validation)
- [ ] Multiple files uploaded quickly
- [ ] Same file uploaded twice

### 5. Error Messages to Look For

#### Common Error Patterns:

**"Error saving file to disk"**
- Disk space issue
- Permission issue
- Path doesn't exist

**"File validation failed"**
- File is corrupted
- File format mismatch
- File is empty

**"Error extracting metadata"**
- File too large
- Memory issue
- Pandas error reading file

**"File not found on disk"**
- File was deleted
- Path issue
- Registry out of sync

### 6. Quick Fixes

```bash
# Ensure directory exists and is writable
mkdir -p uploaded_files
chmod 755 uploaded_files

# Check Python dependencies
pip install pandas openpyxl python-dateutil chardet python-multipart

# Restart backend
# Kill existing process and restart
python3 backend/main.py
```

### 7. Enable Debug Mode

Add to backend startup:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 8. Check Browser Console

Open browser DevTools (F12) → Console tab:
- Look for JavaScript errors
- Check network requests
- Verify API responses

### 9. Verify API Endpoints

Test each endpoint:
```bash
# Health check
curl http://localhost:8000/api/health

# List files
curl http://localhost:8000/api/files/list

# Upload file
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@test.csv"
```

### 10. Next Steps if Still Failing

1. **Check backend logs** - Look for ERROR messages
2. **Test with curl** - Isolate frontend vs backend issues
3. **Try different files** - Is it file-specific?
4. **Check file size** - Try smaller files first
5. **Monitor resources** - CPU, memory, disk during upload

---

## Reporting Issues

When reporting issues, include:
1. Backend log output (ERROR messages)
2. File size and type
3. Browser console errors
4. Network tab (request/response)
5. Steps to reproduce

