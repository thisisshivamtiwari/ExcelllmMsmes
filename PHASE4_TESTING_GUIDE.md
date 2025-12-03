# Phase 4 Testing Guide

## 🧪 Complete Testing Guide for LangChain Agent System

---

## Prerequisites

### 1. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 2. Set Up Groq API (Required for Agent)

**Get Groq API Key:**
1. Sign up at: https://console.groq.com
2. Get your API key from the dashboard
3. Add to `.env` file:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

**No Model Download Required:**
- Groq provides inference API - no local installation needed
- Uses optimized prompts from `prompt_engineering/` module

### 3. Environment Variables

Create/update `.env` file in project root:
```env
# Agent Configuration (Groq API)
GROQ_API_KEY=your_groq_api_key_here
AGENT_MODEL_NAME=meta-llama/llama-4-maverick-17b-128e-instruct

# Existing variables
GEMINI_API_KEY=your_gemini_key_here
```

---

## Starting the System

### 1. Start Backend
```bash
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Verify:** http://localhost:8000/docs

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

**Verify:** http://localhost:5173

### 3. Verify Groq API Key
```bash
# Check .env file has GROQ_API_KEY set
# No need to verify - will be checked when agent initializes
```

---

## Testing Steps

### Step 1: Verify Agent Status

**API Test:**
```bash
curl http://localhost:8000/api/agent/status
```

**Expected Response:**
```json
{
  "available": true,
  "agent_initialized": true,
  "embeddings_available": true,
  "model_name": "meta-llama/llama-4-maverick-17b-128e-instruct",
  "provider": "Groq API",
  "prompt_engineering": true
}
```

**Frontend Test:**
1. Navigate to http://localhost:5173/agent-chat
2. Check status indicator at top
3. Should show "Agent is ready" in green

---

### Step 2: Test Basic Query

**Test Query:** "What files are uploaded?"

**API Test:**
```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What files are uploaded?"}'
```

**Frontend Test:**
1. Go to Agent Chat page
2. Type: "What files are uploaded?"
3. Click Send
4. Should receive a response

---

### Step 3: Test Data Retrieval

**Prerequisites:**
- Upload at least one Excel/CSV file
- File should be indexed (automatic on upload)

**Test Query:** "Show me production data"

**Expected Behavior:**
1. Agent uses semantic search to find relevant columns
2. Retrieves data from file
3. Returns data summary

---

### Step 4: Test Calculations

**Test Query:** "What is the total production quantity?"

**Expected Behavior:**
1. Agent finds production quantity column
2. Retrieves data
3. Calculates sum
4. Returns total

**Test Query:** "What is the average defect rate?"

**Expected Behavior:**
1. Agent finds defect-related columns
2. Calculates average
3. Returns result

---

### Step 5: Test Trend Analysis

**Test Query:** "Show me production trends over time"

**Expected Behavior:**
1. Agent finds date and production columns
2. Analyzes trends
3. Returns trend data with direction

---

### Step 6: Test Comparative Analysis

**Test Query:** "Which product has the most defects?"

**Expected Behavior:**
1. Agent finds product and defect columns
2. Groups by product
3. Compares values
4. Returns best/worst products

---

### Step 7: Test KPI Calculation

**Test Query:** "Calculate OEE for all machines"

**Expected Behavior:**
1. Agent finds OEE-related columns
2. Calculates OEE
3. Returns OEE values

---

## Test Scenarios

### Scenario 1: Simple Data Query
**Query:** "Show me the first 10 rows of production data"
**Expected:** Returns first 10 rows with data

### Scenario 2: Aggregation Query
**Query:** "What is the sum of all production quantities?"
**Expected:** Returns sum value

### Scenario 3: Filtered Query
**Query:** "Show me production data for Product A"
**Expected:** Returns filtered data

### Scenario 4: Comparison Query
**Query:** "Compare production efficiency between Line 1 and Line 2"
**Expected:** Returns comparison results

### Scenario 5: Trend Query
**Query:** "What are the production trends for the last month?"
**Expected:** Returns trend analysis

### Scenario 6: KPI Query
**Query:** "Calculate First Pass Yield"
**Expected:** Returns FPY calculation

---

## Troubleshooting

### Issue: Agent Not Available

**Symptoms:**
- Status shows "Agent unavailable"
- Error in logs

**Solutions:**
1. Check GROQ_API_KEY is set in .env file
2. Verify API key is valid (not starting with "your_")
3. Check backend logs for specific error messages
4. Ensure groq package is installed: `pip install groq`

### Issue: No Response from Agent

**Symptoms:**
- Query sent but no response
- Loading indicator stuck

**Solutions:**
1. Check backend logs for API errors
2. Verify GROQ_API_KEY is valid and has credits
3. Check Groq API status: https://status.groq.com
4. Verify model name: `AGENT_MODEL_NAME=meta-llama/llama-4-maverick-17b-128e-instruct`
5. Check network connectivity to Groq API

### Issue: Semantic Search Not Working

**Symptoms:**
- Agent can't find relevant columns
- "No relevant columns found" error

**Solutions:**
1. Verify files are indexed: Check `/api/semantic/stats`
2. Re-index files: POST `/api/semantic/index-all`
3. Check embeddings are available

### Issue: Data Retrieval Fails

**Symptoms:**
- Agent finds columns but can't retrieve data
- File not found errors

**Solutions:**
1. Verify files exist in `uploaded_files/`
2. Check file metadata exists
3. Verify file paths in metadata

---

## Expected Performance

- **Simple Query:** 2-5 seconds
- **Data Retrieval:** 1-3 seconds
- **Calculation:** 1-2 seconds
- **Trend Analysis:** 3-8 seconds
- **Complex Query:** 5-15 seconds

---

## Success Criteria

✅ **Agent Status:**
- Agent initializes successfully
- Status endpoint returns `available: true`

✅ **Basic Queries:**
- Agent responds to simple questions
- Returns relevant answers

✅ **Data Retrieval:**
- Finds relevant columns/files
- Retrieves actual data

✅ **Calculations:**
- Performs aggregations correctly
- Returns accurate results

✅ **Analysis:**
- Trend analysis works
- Comparative analysis works
- KPI calculations work

✅ **Frontend:**
- Chat interface works
- Messages display correctly
- Loading states work
- Error handling works

---

## Next Steps After Testing

1. **If all tests pass:** Phase 4 is complete! ✅
2. **If issues found:** Fix and retest
3. **Performance issues:** Optimize agent/tools
4. **Accuracy issues:** Improve prompts/tools

---

## Additional Resources

- **Backend API Docs:** http://localhost:8000/docs
- **Ollama Docs:** https://ollama.ai/docs
- **LangChain Docs:** https://python.langchain.com

---

**Happy Testing!** 🚀

