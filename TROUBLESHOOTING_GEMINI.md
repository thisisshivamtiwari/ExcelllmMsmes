# Gemini API Key Fix Guide

## ⚠️ Issue: API Key Reported as Leaked

**Error**: `403 Your API key was reported as leaked. Please use another API key.`

This means your Gemini API key has been flagged as compromised and Google has disabled it.

---

## ✅ Current Status

- ✅ Backend is running successfully
- ✅ Groq agent is working perfectly
- ✅ Gemini agent initialized but API key is invalid
- ⚠️ Need to replace Gemini API key

---

## 🔧 How to Fix

### Step 1: Get a New Gemini API Key

1. **Go to Google Cloud Console**:
   - Visit: https://console.cloud.google.com/apis/credentials
   - Sign in with your Google account

2. **Delete Old Key** (if visible):
   - Find the compromised key
   - Click "Delete" to remove it

3. **Create New API Key**:
   - Click "Create Credentials" → "API Key"
   - Copy the new key immediately (you won't see it again)

4. **Restrict the Key** (Recommended):
   - Click "Restrict Key"
   - Under "API restrictions", select "Restrict key"
   - Choose "Generative Language API"
   - Save

### Step 2: Update Your .env File

Edit `backend/.env`:

```env
# Replace with your new Gemini API key
GEMINI_API_KEY=your_new_gemini_api_key_here

# Keep your Groq key
GROQ_API_KEY=gsk_your_groq_key_here
```

### Step 3: Restart Backend

```bash
# Stop the current backend (Ctrl+C)
# Then restart:
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎯 Alternative: Use Groq Only

If you don't need Gemini right now:

1. **Keep using Groq** - It's working perfectly
2. **Toggle to Groq** in the frontend
3. **Fix Gemini key later** when you have time

---

## 🔒 Security Best Practices

To prevent this in the future:

1. **Never commit API keys to Git**
   - ✅ Already done - `.env` is in `.gitignore`

2. **Use environment variables**
   - ✅ Already configured

3. **Rotate keys regularly**
   - Generate new keys every few months

4. **Restrict API keys**
   - Limit to specific APIs/IPs when possible

5. **Monitor usage**
   - Check Google Cloud Console for unusual activity

---

## 📝 Quick Checklist

- [ ] Get new Gemini API key from Google Cloud Console
- [ ] Update `backend/.env` with new key
- [ ] Restart backend
- [ ] Test Gemini toggle in frontend
- [ ] Verify both providers work

---

## 💡 Why This Happened

API keys can be flagged as "leaked" if:
- They were accidentally committed to public repositories
- They were shared in screenshots or logs
- They were exposed in error messages
- Google detected suspicious usage patterns

**Good news**: This is a security feature, not a bug. Google is protecting your account.

---

## 🚀 After Fixing

Once you update the key and restart:

1. Both Groq and Gemini should work
2. You can toggle between them in the frontend
3. Each message will show which provider was used

---

## 📞 Need Help?

If you continue to have issues:
1. Verify the new key works: https://aistudio.google.com/app/apikey
2. Check Google Cloud Console for any restrictions
3. Ensure the key has "Generative Language API" enabled

