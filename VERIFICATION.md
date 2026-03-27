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

Since Layers 2-4 are stubs, valid requests return:
- `score: 50`, `verdict: "uncertain"` (neutral default)
- `request_id` (UUID) and `processing_time_ms`
- Server logs show each pipeline step with timing
