# AI Hallucination Detection System - Backend

## Project Overview

This backend system detects and flags AI hallucinations by grounding LLM judgments in external evidence sources.

### Key Features
- **Evidence-Grounded Verification**: Uses Wikipedia and SerpAPI to retrieve evidence
- **Smart Query Routing**: Routes queries to appropriate sources based on type
- **LLM Judge**: Evidence-based evaluation reduces judge hallucinations
- **Extensible Architecture**: Layered design allows easy addition of new components

## Architecture

The backend follows a 5-layer architecture:

### Layer 1: API Gateway
- **File**: `app/api/routes/verify.py`
- **Responsibility**: Validate input, parse request, coordinate pipeline
- **Endpoint**: `POST /verify`
- Input: `{ "question": "...", "answer": "..." }`

### Layer 2: Query Preprocessor
- **File**: `app/services/preprocessing/query_preprocessor.py`
- **Responsibility**: Extract factual claims, determine query type
- **Output**: Structured claims and type classification

### Layer 3: Retrieval Engine
- **Files**:
  - `app/services/retrieval/wikipedia_retriever.py` - Encyclopedic facts
  - `app/services/retrieval/serp_retriever.py` - Recent events & web results
  - `app/services/retrieval/source_router.py` - Routing logic
  - `app/services/retrieval/evidence_aggregator.py` - Dedup, rank, trim evidence

### Layer 4: LLM Judge
- **File**: `app/services/judge/llm_judge.py`
- **Responsibility**: Evidence-grounded fact verification
- **Output**: Score (0-100), verdict, explanation

### Layer 5: Response Builder
- **File**: `app/models/response.py`
- **Responsibility**: Format judge output for frontend
- **Output**: User-friendly verdict (accurate/uncertain/hallucination)

## Project Structure

```
.
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   └── verify.py              # Layer 1 - API Gateway
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py                  # Settings & environment
│   │   ├── logging.py                 # Shared logger
│   │   └── __init__.py
│   ├── models/
│   │   ├── request.py                 # Pydantic request model
│   │   ├── response.py                # Pydantic response model
│   │   └── __init__.py
│   ├── services/
│   │   ├── preprocessing/
│   │   │   ├── query_preprocessor.py  # Layer 2
│   │   │   └── __init__.py
│   │   ├── retrieval/
│   │   │   ├── wikipedia_retriever.py # Layer 3a
│   │   │   ├── serp_retriever.py      # Layer 3b
│   │   │   ├── source_router.py       # Layer 3c
│   │   │   ├── evidence_aggregator.py # Layer 3d
│   │   │   └── __init__.py
│   │   ├── judge/
│   │   │   ├── llm_judge.py           # Layer 4
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── utils/
│   │   ├── cache.py                   # Caching utilities
│   │   └── __init__.py
│   └── __init__.py
├── main.py                            # FastAPI entrypoint
├── requirements.txt                   # Dependencies
├── .env.example                       # Environment template
└── README.md                          # This file
```

## Getting Started

### 1. Clone & Setup
```bash
git clone <repo-url>
cd ai-hallucination-detection
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in your API keys:
# - LLM_API_KEY (OpenAI, Anthropic, etc.)
# - SERPAPI_KEY (for web search)
```

### 4. Run the Backend
```bash
python main.py
```

Server will start at `http://localhost:8000`

Visit API docs: `http://localhost:8000/docs` (Swagger UI)

### 5. Test the Endpoint
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the capital of France?",
    "answer": "The capital of France is Paris, located on the Seine River."
  }'
```

Expected response:
```json
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "Verified against Wikipedia. Paris is indeed the capital of France.",
  "flag": false,
  "sources_used": ["Wikipedia"]
}
```

## Implementation Roadmap

### Phase 1: Core Pipeline (MVP)
- [x] Basic folder structure
- [ ] Layer 1: API Gateway (input validation done, coordinate pipeline)
- [ ] Layer 4: LLM Judge (basic version, no evidence first)
- [ ] Layer 5: Response formatting
- [ ] Basic testing with Postman

### Phase 2: Evidence Retrieval
- [ ] Layer 2: Query Preprocessor (claim extraction)
- [ ] Layer 3a: Wikipedia integration
- [ ] Layer 3b: SerpAPI integration
- [ ] Layer 3c: Source Router
- [ ] Layer 3d: Evidence Aggregator

### Phase 3: Production Hardening
- [ ] Caching layer (Redis or in-memory)
- [ ] Error handling & logging
- [ ] Rate limiting
- [ ] Batch processing
- [ ] Monitoring & metrics

## Todo List by Layer

Each file contains `TODO` comments marking implementation points.

### Layer 1: API Gateway (`app/api/routes/verify.py`)
- ✅ Route structure defined
- ✅ Pydantic validation
- ✅ Pipeline orchestration
- [ ] Error handling refinement

### Layer 2: Query Preprocessor (`app/services/preprocessing/query_preprocessor.py`)
- [ ] Implement `extract_claims()` - use small LLM or regex
- [ ] Implement `determine_query_type()` - classify query for routing

### Layer 3a: Wikipedia Retriever (`app/services/retrieval/wikipedia_retriever.py`)
- [ ] Install `wikipedia-api` library
- [ ] Implement `search()` - call Wikipedia API
- [ ] Extract first 2 paragraphs as evidence

### Layer 3b: SerpAPI Retriever (`app/services/retrieval/serp_retriever.py`)
- [ ] Install `google-search-results` library
- [ ] Implement `search()` - call SerpAPI
- [ ] Extract top 3 snippets as evidence

### Layer 3c: Source Router (`app/services/retrieval/source_router.py`)
- ✅ Routing rules defined
- [ ] Implement `retrieve_evidence()` - call appropriate retrievers

### Layer 3d: Evidence Aggregator (`app/services/retrieval/evidence_aggregator.py`)
- [ ] Implement `deduplicate()` - remove duplicate snippets
- [ ] Implement `rank_evidence()` - prioritize best evidence
- [ ] Implement `trim_to_budget()` - fit within token limit

### Layer 4: LLM Judge (`app/services/judge/llm_judge.py`)
- ✅ Prompt template defined
- [ ] Initialize LLM client (OpenAI, Anthropic, etc.)
- [ ] Implement `judge()` - make API call, parse response

### Layer 5: Response Builder (`app/models/response.py`)
- ✅ Mapping logic defined (score ranges to verdicts)
- ✅ `from_judge_response()` implemented
- [ ] Test with various score ranges

## Key Design Decisions

### Why Evidence-Grounded Judging?
- Pure GPT-as-Judge has hallucination risk
- Grounding judge in retrieved evidence reduces false positives
- Wikipedia + SerpAPI provide diverse, reliable sources

### How to Handle Unverifiable Claims?
*Currently: Return score=50 with "unverifiable" verdict*
- Alternative: Treat absence of evidence as hallucination risk
- Recommendation: Start with neutral, adjust based on user feedback

### Single Score vs. Per-Claim Scores?
*Currently: Single score for entire answer*
- Simpler UI, easier to understand
- Per-claim scores: More precise, but harder to aggregate

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM provider | `sk-...` |
| `LLM_MODEL` | Model to use | `gpt-4` |
| `LLM_API_BASE` | LLM API endpoint | `https://api.openai.com/v1` |
| `SERPAPI_KEY` | SerpAPI key for web search | `abc123...` |
| `WIKIPEDIA_API_ENABLED` | Enable Wikipedia retrieval | `true` |
| `CACHE_ENABLED` | Enable caching | `true` |
| `MAX_EVIDENCE_TOKENS` | Token limit for evidence | `800` |

## API Endpoints

### POST /verify
Verify if an answer contains hallucinations.

**Request**:
```json
{
  "question": "What is the capital of France?",
  "answer": "The capital of France is Paris, on the Seine River."
}
```

**Response**:
```json
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "Verified against Wikipedia.",
  "flag": false,
  "sources_used": ["Wikipedia"]
}
```

**Score Ranges**:
- 75-100: ✅ Likely accurate
- 40-74: ⚠️ Uncertain, verify
- 0-39: 🚩 High hallucination risk

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "service": "hallucination-detection"
}
```

## Logging

All modules use `app.core.logging.get_logger()` for consistent logging.

Enable debug logs:
```bash
# In .env
APP_DEBUG=true
```

## Testing

### Manual Testing with curl
```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is the president of USA?", "answer": "Joe Biden"}'
```

### Automated Tests
```bash
# TODO: Add pytest tests
pytest tests/
```

## Contributing

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Add TODOs with layer numbers

### Adding New Retrievers
1. Create new file in `app/services/retrieval/`
2. Implement retriever class with `search()` method
3. Update `SourceRouter` to include new retriever
4. Add configuration to `.env.example`

### Adding New LLM Providers
1. Modify `app/services/judge/llm_judge.py`
2. Initialize new LLM client
3. Update prompt if needed
4. Test with existing endpoints

## Troubleshooting

### "LLM API key not configured"
- Check `.env` file exists
- Verify `LLM_API_KEY` is set
- Run: `python -c "from app.core.config import get_settings; print(get_settings().llm_api_key)"`

### Wikipedia API returns empty results
- Check `WIKIPEDIA_API_ENABLED=true` in `.env`
- Verify claim extraction is working (check logs)
- Try different search terms

### Score always 50
- Judge likely not implemented yet
- Check `app/services/judge/llm_judge.py` for TODOs
- Verify LLM API is configured and working

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Wikipedia API](https://pypi.org/project/wikipedia-api/)
- [SerpAPI Docs](https://serpapi.com/docs)
- [OpenAI API](https://platform.openai.com/docs)

## License

[Add your license here]
