# Verification Guide

## Prerequisites

```bash
cd /Users/aadi/projects/AI-Hallucination-Risk-Assessment
source venv/bin/activate
```

---

## Layer 1: API Gateway

### Automated Tests

```bash
python -m pytest tests/test_models.py tests/test_verify.py -v
```

**Expected**: 31 tests pass (21 model + 10 endpoint)

### Manual Testing

Start the server:
```bash
python main.py
```

In another terminal:

```bash
# ✅ Valid request → 200 with score, verdict, request_id, processing_time_ms
curl -s -X POST http://localhost:8000/api/verify \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the capital of France?", "answer": "Paris is the capital of France."}' | python3 -m json.tool

# ❌ Question too short → 422
curl -s -X POST http://localhost:8000/api/verify \
  -H 'Content-Type: application/json' \
  -d '{"question": "Hi", "answer": "Paris is the capital of France."}' | python3 -m json.tool

# ❌ Missing field → 422
curl -s -X POST http://localhost:8000/api/verify \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the capital of France?"}' | python3 -m json.tool

# 💚 Health check → {"status": "ok"}
curl -s http://localhost:8000/api/health | python3 -m json.tool
```

### Interactive Docs

Visit **http://localhost:8000/docs** for Swagger UI.

### Expected Output (Stubs Active)

Since Layers 3-4 are stubs, valid requests return:
- `score: 50`, `verdict: "uncertain"` (neutral default from stub judge)
- `request_id` (UUID) and `processing_time_ms`
- Server logs show claim extraction and query type from Layer 2

---

## Layer 2: Query Preprocessor

### Automated Tests

```bash
python -m pytest tests/test_preprocessor.py -v
```

**Expected**: 24 tests pass (9 extraction + 12 query type + 3 pipeline)

### Quick Manual Test

```bash
python -c "
from app.services.preprocessing.query_preprocessor import QueryPreprocessor

# Test claim extraction
claims = QueryPreprocessor.extract_claims(
    'Paris is the capital of France. It is located along the Seine River. The city has over 2 million residents.'
)
print('Claims:', claims)

# Test query type detection
print('Type:', QueryPreprocessor.determine_query_type('What is the capital of France?'))
print('Type:', QueryPreprocessor.determine_query_type('What happened today in politics?'))
print('Type:', QueryPreprocessor.determine_query_type('How many countries are in the EU?'))
print('Type:', QueryPreprocessor.determine_query_type('Should I learn Python or JavaScript?'))
"
```

