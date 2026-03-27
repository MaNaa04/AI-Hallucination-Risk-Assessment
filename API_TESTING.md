# API Testing - Postman Collection

This file documents API endpoints for testing with Postman or curl.

## Collection Variables

```json
{
  "base_url": "http://localhost:8000",
  "api_base": "http://localhost:8000/api"
}
```

---

## Endpoint 1: Health Check

**Name**: Health Check  
**Method**: GET  
**URL**: `{{base_url}}/health`  

### Response
```json
{
  "status": "ok",
  "service": "hallucination-detection"
}
```

---

## Endpoint 2: Server Info

**Name**: Server Info  
**Method**: GET  
**URL**: `{{base_url}}/`  

### Response
```json
{
  "name": "AI Hallucination Detection Backend",
  "version": "0.1.0",
  "status": "running"
}
```

---

## Endpoint 3: Verify Answer

**Name**: Verify Hallucination  
**Method**: POST  
**URL**: `{{api_base}}/verify`  

### Headers
```
Content-Type: application/json
```

### Request Body

#### Test Case 1: Accurate Answer
```json
{
  "question": "What is the capital of France?",
  "answer": "The capital of France is Paris, located along the Seine River in northern France."
}
```

**Expected Response** (Score: 75-100):
```json
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "Verified against Wikipedia. Paris is indeed the capital of France.",
  "flag": false,
  "sources_used": ["Wikipedia"]
}
```

---

#### Test Case 2: Hallucination
```json
{
  "question": "Who is the current president of France?",
  "answer": "Vincent Van Gogh is the current president of France (as of 2024)."
}
```

**Expected Response** (Score: 0-39):
```json
{
  "score": 5,
  "verdict": "hallucination",
  "explanation": "Vincent Van Gogh was a 19th-century artist who died in 1890. This is factually incorrect.",
  "flag": true,
  "sources_used": ["Wikipedia"]
}
```

---

#### Test Case 3: Uncertain/Unverifiable
```json
{
  "question": "What will the weather be tomorrow?",
  "answer": "Tomorrow will be sunny with 72°F temperature."
}
```

**Expected Response** (Score: 40-74):
```json
{
  "score": 50,
  "verdict": "uncertain",
  "explanation": "Future weather predictions cannot be verified against current sources.",
  "flag": false,
  "sources_used": null
}
```

---

#### Test Case 4: Complex Multi-Claim Answer
```json
{
  "question": "Tell me about the Moon",
  "answer": "The Moon is Earth's natural satellite. It orbits Earth every 27.3 days and has a diameter of about 3,474 km. The Moon was formed about 4.5 billion years ago from a giant impact theory hypothesis."
}
```

**Expected Response**:
```json
{
  "score": 78,
  "verdict": "accurate",
  "explanation": "Key facts verified: Moon is Earth's satellite, orbital period ~27 days, diameter ~3,474 km, formation ~4.5B years ago.",
  "flag": false,
  "sources_used": ["Wikipedia"]
}
```

---

#### Test Case 5: Recent Event (Requires SerpAPI)
```json
{
  "question": "What happened in recent tech news?",
  "answer": "A new AI model breakthrough was announced in January 2024 demonstrating improved reasoning capabilities."
}
```

**Expected Response**:
```json
{
  "score": 65,
  "verdict": "uncertain",
  "explanation": "Multiple AI breakthroughs claimed in early 2024. Need more specific details to verify exact claim.",
  "flag": false,
  "sources_used": ["SerpAPI"]
}
```

---

#### Test Case 6: Invalid Input - Missing Field
```json
{
  "question": "What is 2+2?"
}
```

**Expected Response** (422):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "answer"],
      "msg": "Field required"
    }
  ]
}
```

---

#### Test Case 7: Invalid Input - Too Short
```json
{
  "question": "Hi?",
  "answer": "42"
}
```

**Expected Response** (422):
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "question"],
      "msg": "String should have at least 5 characters"
    }
  ]
}
```

---

## curl Commands for Quick Testing

### Test 1: Verify with curl
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the capital of France?",
    "answer": "Paris is the capital of France."
  }'
```

### Test 2: Hallucination Detection
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Who discovered America?",
    "answer": "The Earth is located in the Andromeda Galaxy."
  }'
```

### Test 3: Health Check
```bash
curl http://localhost:8000/health
```

### Test 4: Pretty Print Response
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "answer": "Python is a programming language."
  }' | python -m json.tool
```

---

## Building Custom Postman Collection

1. **Import into Postman**:
   - Click "Import"
   - Paste this file or import from URL
   - Set `{{base_url}}` variable to `http://localhost:8000`

2. **Create Variables**:
   - Environment name: "Local"
   - Variables:
     - `base_url`: `http://localhost:8000`
     - `api_base`: `http://localhost:8000/api`

3. **Run Tests**:
   - Select a request
   - Click "Send"
   - View response in "Body" tab

4. **Automate**:
   - Click "Runner"
   - Select collection
   - Select environment "Local"
   - Click "Start Test Run"

---

## Expected Score Ranges

| Score | Verdict | UI Badge | Warning |
|-------|---------|----------|---------|
| 75-100 | accurate | ✅ Green | None |
| 40-74 | uncertain | ⚠️ Yellow | "Verify this information" |
| 0-39 | hallucination | 🚩 Red | "High hallucination risk" |

---

## Response Time Targets

- **Health Check**: <10ms
- **Simple Verify**: 2-8 seconds (typical)
  - 1s: Wikipedia search
  - 2s: Evidence aggregation
  - 5s: LLM judge call
  - 1s: Response formatting

---

## Debugging Tips

### View Full Response Headers
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test?", "answer": "Test answer"}' \
  -i
```

### View Request/Response with Details
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test?", "answer": "Test answer"}' \
  -v
```

### Test with Python
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/api/verify",
    json={"question": "Test?", "answer": "Test answer"},
    timeout=30
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

---

## Success Criteria

- ✅ All requests return proper HTTP status codes
- ✅ Responses match expected JSON schema
- ✅ Scores are between 0-100
- ✅ Verdicts are one of: "accurate", "uncertain", "hallucination"
- ✅ Response times are reasonable (<15 seconds)

---

**Note**: As backend develops, add actual responses here to track progress!
