# EXCELLLM - ACTION PLAN
## Current Status & Next Steps

**Date:** 2026-01-15  
**Status:** Ready to start Phase 1 (Excel Parser) from scratch

---

## 🔍 CURRENT STATE ANALYSIS

### ✅ What's Already Working:
1. **Backend Infrastructure:**
   - FastAPI server with CORS configured
   - Error handling and logging
   - Environment variable loading
   - File upload directory structure (`uploaded_files/`)

2. **Frontend Infrastructure:**
   - React + Vite setup
   - Routing configured
   - Sidebar navigation
   - UI components (Button, Header, Sidebar)
   - Visualization components for Benchmarking, Comparison, Model Optimization

3. **Existing Modules:**
   - Data Generator (`datagenerator/`)
   - Question Generator (`question_generator/`)
   - LLM Benchmarking (`llm_benchmarking/`)
   - Prompt Engineering (`prompt_engineering/`)
   - Comparison Analysis (`enhanced_vs_baseline_vs_groundtruth/`)

### ❌ What Needs Cleanup:
1. **Backend (`backend/main.py`):**
   - Lines 1070-1428: Old Phase 1 file upload endpoints still exist
   - Lines 1078-1080: Imports from deleted `excel_parser` module
   - Lines 1083-1085: Initialization of deleted parser components
   - Line 1088: `uploaded_files_registry` dictionary

2. **Frontend:**
   - `App.jsx` line 12: Import for deleted `FileUpload` component
   - `App.jsx` line 65: Route for `/file-upload`
   - `Sidebar.jsx` line 9: Menu item for "File Upload"

### 📋 What's Remaining (According to Master Plan):

**PHASE 1:** Excel Parser & Data Loading (NOT STARTED - Starting fresh)  
**PHASE 2:** Schema Detection & Type Inference (NOT STARTED)  
**PHASE 3:** Intelligent Schema Normalization (NOT STARTED)  
**PHASE 4:** Cross-File Relationship Detection (NOT STARTED)  
**PHASE 5:** Data Validation & Cleaning (NOT STARTED)  
**PHASE 6:** Schema Registry & Storage (NOT STARTED)  
**PHASE 7:** Visualization System (NOT STARTED)  
**PHASE 8:** API Integration & Frontend (NOT STARTED)  
**PHASE 9:** Testing & Documentation (NOT STARTED)

---

## 🎯 IMMEDIATE ACTION PLAN

### STEP 1: Cleanup (Before Starting Phase 1)
**Priority:** HIGH  
**Estimated Time:** 30 minutes

#### 1.1 Backend Cleanup (`backend/main.py`)
- [ ] Remove lines 1070-1428 (old Phase 1 endpoints)
- [ ] Remove imports from `excel_parser` (lines 1074-1080)
- [ ] Remove `uploaded_files_registry` initialization
- [ ] Keep only working endpoints (data generator, benchmarking, prompt engineering, comparison, visualizations)

#### 1.2 Frontend Cleanup
- [ ] Remove `FileUpload` import from `App.jsx`
- [ ] Remove `/file-upload` route from `App.jsx`
- [ ] Remove "File Upload" menu item from `Sidebar.jsx`
- [ ] Remove unused `FiUpload` icon import if not used elsewhere

#### 1.3 Verify Backend Runs
- [ ] Test that backend starts without errors
- [ ] Verify existing endpoints still work (benchmarking, comparison, etc.)

---

### STEP 2: Phase 1 - Excel Parser & Data Loading
**Priority:** HIGH  
**Estimated Time:** 1-2 weeks  
**Status:** NOT STARTED

#### 2.1 Create Directory Structure
```
excel_parser/
├── __init__.py
├── excel_loader.py
├── file_validator.py
└── metadata_extractor.py
```

#### 2.2 Implement Core Modules

**excel_loader.py:**
- [ ] Load .xlsx files with multiple sheets support
- [ ] Load .csv files
- [ ] Handle large files (>50k rows) with chunking
- [ ] Preserve data types during loading
- [ ] Error handling for corrupted files
- [ ] Progress tracking for large files

**file_validator.py:**
- [ ] Validate file format (.xlsx, .csv)
- [ ] Check file size limits (e.g., max 100MB)
- [ ] Verify file is not corrupted
- [ ] Check encoding (UTF-8, etc.)
- [ ] Return validation results with error messages

**metadata_extractor.py:**
- [ ] Extract file metadata (name, size, modified date)
- [ ] Count rows and columns per sheet
- [ ] Detect file encoding
- [ ] Extract sheet names (for Excel)
- [ ] Get sample data (first 5 rows)
- [ ] Return comprehensive metadata dictionary

#### 2.3 Create Requirements File
- [ ] Create `excel_parser/requirements.txt`:
  - pandas>=2.0.0
  - openpyxl>=3.1.0
  - python-dateutil>=2.8.0
  - chardet>=5.0.0 (for encoding detection)

#### 2.4 Write Unit Tests
- [ ] Test .xlsx loading (single and multiple sheets)
- [ ] Test .csv loading
- [ ] Test error handling (corrupted files, invalid formats)
- [ ] Test large file handling (chunking)
- [ ] Test metadata extraction accuracy

#### 2.5 Backend API Integration
- [ ] Create `POST /api/files/upload` endpoint (clean implementation)
- [ ] Create `GET /api/files/list` endpoint
- [ ] Create `GET /api/files/{file_id}` endpoint
- [ ] Create `GET /api/files/{file_id}/metadata` endpoint
- [ ] Create `POST /api/files/{file_id}/load` endpoint (load data with sheet selection)
- [ ] Create `DELETE /api/files/{file_id}` endpoint

#### 2.6 Frontend File Upload Page
- [ ] Create `frontend/src/pages/FileUpload.jsx`
- [ ] Implement drag-and-drop file upload
- [ ] Show upload progress
- [ ] Display uploaded files list
- [ ] Show file metadata (rows, columns, sheets)
- [ ] Allow data preview (first 10 rows)
- [ ] Allow file deletion

---

### STEP 3: Phase 2 - Schema Detection & Type Inference
**Priority:** HIGH  
**Estimated Time:** 1 week  
**Status:** NOT STARTED  
**Dependencies:** Phase 1

#### 3.1 Create Schema Detection Modules
```
excel_parser/
├── schema_detector.py
└── type_inference.py
```

#### 3.2 Implement Schema Detection
- [ ] Detect all columns in DataFrame
- [ ] Extract column names
- [ ] Get basic statistics (count, unique values, nulls)
- [ ] Identify potential primary keys
- [ ] Detect potential foreign keys

#### 3.3 Implement Type Inference
- [ ] Infer column types: date, numeric, categorical, text, id
- [ ] Date detection (multiple formats)
- [ ] Numeric detection (int, float, with commas)
- [ ] Categorical detection (limited unique values)
- [ ] ID detection (high uniqueness, patterns)
- [ ] Text detection (free-form strings)

#### 3.4 Backend API Integration
- [ ] Create `GET /api/schema/{file_id}` endpoint
- [ ] Return schema with column types and statistics

---

### STEP 4: Phase 3 - Intelligent Schema Normalization
**Priority:** HIGH  
**Estimated Time:** 2 weeks  
**Status:** NOT STARTED  
**Dependencies:** Phase 1, Phase 2

**Note:** This is the most complex phase. See `MASTER_IMPLEMENTATION_PLAN.txt` Section "PHASE 3" for detailed TODO list.

---

### STEP 5: Phase 4 - Cross-File Relationship Detection
**Priority:** HIGH  
**Estimated Time:** 1-2 weeks  
**Status:** NOT STARTED  
**Dependencies:** Phase 1, Phase 2, Phase 3

**Note:** See `MASTER_IMPLEMENTATION_PLAN.txt` Section "PHASE 4" for detailed TODO list.

---

### STEP 6: Phase 5-9
**Priority:** MEDIUM  
**Status:** NOT STARTED  
**Dependencies:** Previous phases

**Note:** See `MASTER_IMPLEMENTATION_PLAN.txt` for detailed TODO lists for each phase.

---

## 📝 IMPLEMENTATION ORDER

### Critical Path:
```
Cleanup → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9
```

### Parallel Work Opportunities:
- Phase 5 (Data Cleaning) can start after Phase 2
- Phase 6 (Registry) can start after Phase 3
- Phase 7 (Visualizations) can start after Phase 4
- Phase 8 (API/Frontend) can start after Phase 7

---

## 🔧 TECHNICAL DECISIONS

### Backend Structure:
- Keep `backend/main.py` as main FastAPI app
- Create `excel_parser/` module at project root (not in backend/)
- Create `schema_intelligence/` module at project root (Phase 3)
- Create `schema_registry/` module at project root (Phase 4, 6)
- Create `visualizations/` module at project root (Phase 7)

### Frontend Structure:
- Keep existing React structure
- Add `frontend/src/pages/FileUpload.jsx` (Phase 1)
- Add `frontend/src/components/visualizations/` folder (Phase 7-8)

### Storage:
- Use file-based storage initially (JSON files)
- Can migrate to database later if needed
- Store schemas in `schema_registry/data/`
- Store learned patterns in `schema_intelligence/learned_patterns/`

---

## ✅ SUCCESS CRITERIA

### Phase 1 Complete When:
- ✓ Can upload .xlsx and .csv files via API
- ✓ Can load files with multiple sheets
- ✓ Can extract metadata (rows, columns, sheets)
- ✓ Can preview data (first N rows)
- ✓ Frontend file upload page working
- ✓ Unit tests passing (>80% coverage)

### Phase 2 Complete When:
- ✓ Can detect all columns in a file
- ✓ Can infer column types accurately (>90%)
- ✓ Can detect date columns and formats
- ✓ Can identify key columns (primary/foreign keys)
- ✓ API endpoint returns schema with types

### Phase 3 Complete When:
- ✓ Can normalize column names intelligently
- ✓ Multi-strategy matching working (semantic, fuzzy, LLM, context)
- ✓ Confidence scoring working
- ✓ Pattern learning working
- ✓ >85% accuracy on test data

### Phase 4 Complete When:
- ✓ Can detect relationships between files
- ✓ >90% relationship detection accuracy
- ✓ Can build relationship graph
- ✓ Can find join paths

---

## 🚨 RISKS & MITIGATION

### Risk 1: Phase 3 Complexity
**Mitigation:** Allocate extra time, start with simpler strategies first

### Risk 2: Performance with Large Files
**Mitigation:** Implement chunking early, test with 50k+ row files

### Risk 3: LLM API Costs
**Mitigation:** Batch requests, cache results, use LLM only when confidence is low

### Risk 4: Frontend-Backend Integration
**Mitigation:** Test API endpoints independently first, then integrate

---

## 📚 REFERENCE DOCUMENTS

1. `MASTER_IMPLEMENTATION_PLAN.txt` - Complete phase-by-phase plan
2. `projectPrd.md` - Product requirements
3. `projectRoadmap.txt` - Project roadmap
4. `problemStatement.txt` - Problem statement

---

## 🎯 NEXT IMMEDIATE STEPS

1. **Cleanup** (30 min)
   - Remove old Phase 1 code from backend
   - Remove FileUpload references from frontend
   - Verify backend runs without errors

2. **Start Phase 1** (Week 1-2)
   - Create `excel_parser/` directory
   - Implement `excel_loader.py`
   - Implement `file_validator.py`
   - Implement `metadata_extractor.py`
   - Write unit tests
   - Create backend API endpoints
   - Create frontend FileUpload page

3. **Test Phase 1** (End of Week 2)
   - Test with real MSME Excel files
   - Verify all endpoints work
   - Verify frontend integration

---

**Last Updated:** 2026-01-15  
**Next Review:** After Phase 1 completion




