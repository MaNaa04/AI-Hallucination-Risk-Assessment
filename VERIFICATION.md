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

---

## Layer 3: Retrieval Engine

### Automated Tests

```bash
python -m pytest tests/test_retrievers.py -v
```

**Expected**: 25 tests pass (5 Wikipedia + 3 SerpAPI + 8 router + 9 aggregator)

### Quick Manual Test

```bash
python -c "
from app.services.retrieval.wikipedia_retriever import WikipediaRetriever

retriever = WikipediaRetriever()
result = retriever.search('Paris')
print('Found:', result['found'])
print('Title:', result['title'])
print('Content:', result['content'][:200] if result['content'] else 'None')
"
```

---

## Layer 4: LLM Judge

### Automated Tests

```bash
python -m pytest tests/test_judge.py -v
```

**Expected**: 14 tests pass (3 prompt + 7 parsing + 4 judge)

### Setup

1. Copy `.env.example` to `.env`
2. Set your Gemini API key:
```bash
cp .env.example .env
# Edit .env and set:
# LLM_PROVIDER=gemini
# LLM_API_KEY=your_gemini_api_key
# LLM_MODEL=gemini-2.0-flash
```

### Full Pipeline Test

With a valid `.env`, restart the server and test end-to-end:

```bash
python main.py
```

```bash
curl -s -X POST http://localhost:8000/api/verify \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the capital of France?", "answer": "Paris is the capital of France."}' | python3 -m json.tool
```

**Expected**: Real score, verdict, explanation from LLM judge (not 50/unverifiable)

---

## Run All Tests

```bash
python -m pytest tests/ -v
```

**Expected**: 94 tests pass
