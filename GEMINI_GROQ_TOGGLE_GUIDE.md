# Gemini & Groq Toggle Guide

## ✅ Implementation Complete

The agent now supports both **Gemini** and **Groq** APIs with a frontend toggle to switch between them.

---

## 📋 What Was Changed

### 1. **Agent (`agent/agent.py`)**
- ✅ Added Gemini support via `langchain-google-genai`
- ✅ Added provider parameter (`groq` or `gemini`)
- ✅ Supports dynamic model selection per provider

### 2. **Backend (`backend/main.py`)**
- ✅ Updated to support multiple agent instances (one per provider)
- ✅ API endpoint accepts `provider` parameter
- ✅ Status endpoint shows availability for both providers

### 3. **Frontend (`frontend/src/pages/AgentChat.jsx`)**
- ✅ Added provider toggle (Groq/Gemini)
- ✅ Shows current provider and model name
- ✅ Displays provider badge in messages

### 4. **Dependencies (`backend/requirements.txt`)**
- ✅ Added `langchain-google-genai>=1.0.0`

---

## 🔧 Setup

### 1. Install Dependencies
```bash
cd backend
pip install langchain-google-genai
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Make sure both API keys are in `backend/.env`:
```env
# Groq API Key
GROQ_API_KEY=gsk_your_groq_key_here

# Gemini API Key
GEMINI_API_KEY=your_gemini_key_here

# Optional: Set default models
AGENT_MODEL_NAME=meta-llama/llama-4-maverick-17b-128e-instruct
GEMINI_MODEL_NAME=gemini-2.5-flash
```

### 3. Start Backend
```bash
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start Frontend
```bash
cd frontend
npm run dev
```

---

## 🎯 Usage

### Frontend Toggle

1. Open the chat interface: http://localhost:5173/agent-chat
2. Use the toggle buttons at the top to switch between **Groq** and **Gemini**
3. The status indicator shows which provider is ready
4. Ask questions - they'll be processed by the selected provider

### API Usage

**Query with provider:**
```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the total production quantity?",
    "provider": "gemini"
  }'
```

**Check status:**
```bash
curl http://localhost:8000/api/agent/status
```

Response shows availability for both providers:
```json
{
  "available": true,
  "providers": {
    "groq": {
      "available": true,
      "initialized": true,
      "model_name": "meta-llama/llama-4-maverick-17b-128e-instruct",
      "api_key_set": true
    },
    "gemini": {
      "available": true,
      "initialized": true,
      "model_name": "gemini-2.5-flash",
      "api_key_set": true
    }
  }
}
```

---

## 🔍 Features

### Provider Selection
- **Groq**: Fast inference, good for structured queries
- **Gemini**: Free tier available, good for complex reasoning

### Model Information
- Each message shows which provider was used
- Model name displayed in message badge
- Status shows current model for each provider

### Error Handling
- If one provider fails, the other can still be used
- Clear error messages if API key is missing
- Graceful fallback if provider unavailable

---

## 📝 Commits Made

All changes were committed file by file:

1. `feat: Add Gemini API support to agent with provider selection (groq/gemini)`
2. `feat: Add langchain-google-genai dependency for Gemini support`
3. `feat: Add provider selection (groq/gemini) to agent API endpoints`
4. `feat: Add provider toggle (Groq/Gemini) to frontend chat interface`

---

## 🐛 Troubleshooting

### Gemini Not Available
- Check `GEMINI_API_KEY` is set in `backend/.env`
- Verify key is valid: https://console.cloud.google.com/apis/credentials
- Check logs for initialization errors

### Groq Not Available
- Check `GROQ_API_KEY` is set in `backend/.env`
- Verify key starts with `gsk_`
- Check logs for initialization errors

### Toggle Not Working
- Make sure backend is running
- Check browser console for errors
- Verify API endpoint is accessible

---

## 💡 Tips

1. **Free Usage**: Gemini has a generous free tier - use it when Groq tokens are exhausted
2. **Performance**: Groq is typically faster, Gemini may be better for complex reasoning
3. **Switching**: You can switch providers mid-conversation
4. **Status Check**: Always check the status indicator before asking questions

---

## 🎉 Ready to Use!

The toggle is now live. Switch between Groq and Gemini as needed!

