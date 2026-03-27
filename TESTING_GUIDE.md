# AI Hallucination Detection - Testing Guide

## Current Status

✅ **Wikipedia**: Working - retrieves evidence from Wikipedia
⚠️ **Gemini API**: Quota exceeded - now using FALLBACK rule-based scoring
❓ **SerpAPI**: Only activates for RECENT EVENTS (not encyclopedic queries)

---

## How to Test

### 1. Start Server
```bash
cd c:\Users\prath\OneDrive\Desktop\AI-Hallucination-Risk-Assessment
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Test Cases for Postman

### ✅ TEST 1: Encyclopedic Query (Uses Wikipedia ONLY)

**POST** `http://localhost:8000/api/verify`

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "question": "What is the capital of France?",
  "answer": "The capital of France is Paris."
}
```

**Expected Response:**
```json
{
  "score": 85-95,
  "verdict": "accurate" or "verified",
  "explanation": "Answer keywords match evidence (90% overlap). Verified by Wikipedia.",
  "flag": false,
  "sources_used": ["wikipedia"]
}
```

---

### ✅ TEST 2: Recent Event Query (Uses SerpAPI + Wikipedia)

**POST** `http://localhost:8000/api/verify`

**Body:**
```json
{
  "question": "What happened in the 2024 US elections?",
  "answer": "Donald Trump won the 2024 presidential election."
}
```

**Expected Response:**
```json
{
  "score": 70-100,
  "verdict": "accurate",
  "explanation": "...",
  "sources_used": ["serpapi", "wikipedia"]
}
```

> **Note:** This will use SerpAPI if you have `SERPAPI_KEY` in your `.env` file!

---

### ✅ TEST 3: Hallucination Test

**Body:**
```json
{
  "question": "What is the capital of France?",
  "answer": "The capital of France is Berlin."
}
```

**Expected Response:**
```json
{
  "score": 0-30,
  "verdict": "hallucination" or "likely_hallucination",
  "explanation": "Low match with evidence. Claims not supported.",
  "flag": true,
  "sources_used": ["wikipedia"]
}
```

---

## Query Type Detection

The system automatically routes queries:

| Query Contains | Type | Uses |
|----------------|------|------|
| "2024", "today", "recent", "latest" | `recent_event` | SerpAPI + Wikipedia |
| General facts, people, places | `encyclopedic` | Wikipedia only |
| "how many", "statistics" | `numeric_statistical` | Both |
| "should", "opinion", "think" | `opinion_subjective` | Skip retrieval |

---

## Current System Behavior

### ✅ What's Working:
1. **Wikipedia retrieval** - Fetches evidence successfully
2. **Claim extraction** - Extracts key facts from answers
3. **Query routing** - Routes to appropriate sources
4. **Fallback scoring** - Works even when Gemini API fails

### ⚠️ Known Issues:
1. **Gemini API quota exceeded** - Using rule-based fallback
2. **SerpAPI** - Only works if you add `SERPAPI_KEY` to `.env`

---

## How to Fix Gemini Quota Issue

**Option 1: Wait** (Free tier resets daily)
**Option 2: Create new API key** at https://aistudio.google.com/app/apikey
**Option 3: Use fallback** (already working - no action needed!)

---

## How to Enable SerpAPI

1. Get free API key: https://serpapi.com/manage-api-key (100 searches/month free)
2. Add to `.env`:
   ```
   SERPAPI_KEY=your-serpapi-key-here
   ```
3. Restart server
4. Test with recent event query (TEST 2 above)

---

## Environment File (.env)

Your `.env` should look like this:

```bash
# Gemini API (FREE - but quota exceeded currently)
GEMINI_API_KEY=your-gemini-key-here
GEMINI_MODEL=gemini-2.0-flash

# SerpAPI (Optional - for web search)
SERPAPI_KEY=your-serpapi-key-here

# Server
DEBUG=true
PORT=8000

# Features
WIKIPEDIA_API_ENABLED=true
CACHE_ENABLED=true
MAX_EVIDENCE_TOKENS=800
```

---

## Expected Behavior Summary

### With Working Gemini API:
- **Score**: 0-100 (AI-powered)
- **Explanation**: Detailed reasoning from Gemini

### With Fallback (Current):
- **Score**: Based on keyword overlap
- **Explanation**: "Answer keywords match evidence (X% overlap)"
- **Works well enough for demo!**

---

## Test in Postman NOW

Run TEST 1 above - it will work with the fallback system!

You should get a response like:
```json
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "Answer keywords match evidence (87% overlap). Verified by Wikipedia.",
  "flag": false,
  "sources_used": ["wikipedia"]
}
```
