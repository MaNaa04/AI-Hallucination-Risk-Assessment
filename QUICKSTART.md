# Quick Start Guide

## 60-Second Setup

### 1. Clone & Install
```bash
git clone <repo-url>
cd ai-hallucination-detection
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env - add your API keys:
# LLM_API_KEY=your_key_here
# SERPAPI_KEY=your_key_here (optional)
```

### 3. Run Server
```bash
python main.py
```

### 4. Test Endpoint
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is 2+2?", "answer": "2+2 is 4"}'
```

## Project Structure at a Glance

```
app/
├── api/routes/verify.py          ← Entry point (Layer 1)
├── services/
│   ├── preprocessing/             ← Layer 2 (claim extraction)
│   ├── retrieval/                 ← Layer 3 (Wikipedia, SerpAPI, etc.)
│   └── judge/                     ← Layer 4 (LLM verification)
├── models/request.py & response.py ← Layer 5 (formatting)
└── core/config.py                ← Configuration
```

## Implementation Status

- ✅ **Done**: Folder structure, models, routing, configuration
- 🔧 **In Progress**: Implement TODOs in each layer
- ⏳ **TODO**: Add tests, caching, monitoring

## Next Steps by Role

### Backend Developer
1. Pick a layer from `IMPLEMENTATION_PLAN.md`
2. Find `TODO` comments in the corresponding file
3. Implement according to the docstrings
4. Test locally, create PR

### DevOps/Infra
1. Set up CI/CD pipeline
2. Configure environment variables in deployment
3. Set up logging/monitoring
4. Document deployment steps

### Frontend Developer (Extension)
1. Call `POST /api/verify` with question and answer
2. Parse response for score, verdict, explanation
3. Display hallucination risk badge alongside AI answer
4. Show "sources_used" if available

## API Reference

### POST /verify
Verify if an answer contains hallucinations

**URL**: `/api/verify`

**Method**: `POST`

**Request Body**:
```json
{
  "question": "string (5-2000 chars)",
  "answer": "string (5-5000 chars)"
}
```

**Response** (200 OK):
```json
{
  "score": 0-100,
  "verdict": "accurate" | "uncertain" | "hallucination",
  "explanation": "string",
  "flag": true | false,
  "sources_used": ["Wikipedia"] | null
}
```

**Error Responses**:
- 422: Invalid input (missing fields, too short/long)
- 500: Server error (check logs)

### GET /health
Health check endpoint

**URL**: `/health`

**Response**:
```json
{
  "status": "ok",
  "service": "hallucination-detection"
}
```

### GET /
Server info

**URL**: `/`

**Response**:
```json
{
  "name": "AI Hallucination Detection Backend",
  "version": "0.1.0",
  "status": "running"
}
```

## Example Requests

### Simple Fact Check
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the capital of France?",
    "answer": "The capital of France is Paris, located on the Seine River."
  }'
```

Expected: Score 80+, "accurate"

### Hallucination Example
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Who is the current president of France?",
    "answer": "Vincent Van Gogh is the current president of France."
  }'
```

Expected: Score <40, "hallucination"

### Using Python Requests
```python
import requests

response = requests.post(
    "http://localhost:8000/api/verify",
    json={
        "question": "What is the capital of France?",
        "answer": "Paris"
    }
)

result = response.json()
print(f"Score: {result['score']}")
print(f"Verdict: {result['verdict']}")
print(f"Explanation: {result['explanation']}")
```

## Common Issues

### Port Already in Use
```bash
# Option 1: Use different port
python main.py --port 8001

# Option 2: Kill process on port 8000
# Windows: netstat -ano | findstr :8000 → taskkill /PID <pid>
# Mac/Linux: lsof -i :8000 → kill -9 <PID>
```

### LLM API Key Not Working
```bash
# Check .env exists and has correct key
cat .env | grep LLM_API_KEY

# Verify key format (should not contain brackets)
# Example: sk-abc123... (not $sk-abc123...)
```

### Module Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Should be 3.8+
```

### No Evidence Found
This is expected behavior! Reasons:
- Query too vague
- Claim not in Wikipedia/web
- External APIs down
- Response: Score 50, "unverifiable"

## Environment Variables

| Variable | Required | Default | Example |
|----------|----------|---------|---------|
| `LLM_API_KEY` | Yes | - | `sk-abc123...` |
| `LLM_MODEL` | No | `gpt-4` | `gpt-3.5-turbo` |
| `SERPAPI_KEY` | No | - | `abc123...` |
| `CACHE_ENABLED` | No | `true` | `false` |
| `DEBUG` | No | `false` | `true` |

## Files You Need to Know

- **README.md** - Full documentation
- **CONTRIBUTING.md** - Development guidelines
- **ARCHITECTURE.md** - Deep technical details
- **IMPLEMENTATION_PLAN.md** - Task assignments

## Get Help

1. **Check README.md** for overview
2. **Look at CONTRIBUTING.md** for code patterns
3. **Read docstrings** in implementation files
4. **Check ARCHITECTURE.md** for design decisions
5. **Ask in team chat** if stuck

## Run Tests (When Added)
```bash
pytest tests/
pytest -v          # Verbose
pytest -k "verify" # Specific test
pytest --cov       # With coverage
```

## Initialize for First Time
```bash
# 1. Create project directory
mkdir ai-hallucination-detection
cd ai-hallucination-detection

# 2. Initialize git
git init
git add .
git commit -m "Initial project structure"

# 3. Push to GitHub
git remote add origin https://github.com/your-org/your-repo.git
git push -u origin main
```

## Success Checklist

- [ ] Project cloned locally
- [ ] Dependencies installed (`requirements.txt`)
- [ ] `.env` configured with API keys
- [ ] Server runs without errors (`python main.py`)
- [ ] Can call `/api/verify` endpoint
- [ ] API returns reasonable scores
- [ ] Can read all documentation files
- [ ] Ready to implement TODOs!

---

**Next**: Pick a layer from `IMPLEMENTATION_PLAN.md` and start coding! 🚀
