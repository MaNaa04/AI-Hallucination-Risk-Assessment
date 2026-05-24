# AI Hallucination Risk Assessment — Complete Backend System Summary

> **Status**: ✅ Backend Fully Implemented & Running  
> **Version**: 0.1.0  
> **Updated**: March 2026  
> **Stack**: Python · FastAPI · Pydantic v2 · Google Gemini / OpenAI / Groq / Grok / Anthropic · httpx (async) · SerpAPI

---

## 1. What This System Does (The Big Picture)

AI language models are confident — sometimes too confident. They produce fluent, plausible text that can be factually wrong (a phenomenon called **hallucination**). This backend detects that risk by:

1. **Receiving** a question and an AI-generated answer.
2. **Extracting** the key factual claims from the answer.
3. **Searching** trusted external sources (Wikipedia, Google via SerpAPI) for evidence.
4. **Grounding** an LLM judge in that evidence to score the answer.
5. **Returning** a structured hallucination-risk score + verdict + explanation to the caller.

The frontend (a Chrome Extension — see `chrome-extension/`) calls this backend's REST API. The backend is the "brain" — the extension is the "face."

---

## 2. Architecture Philosophy

### Why Evidence-Grounded Judging?

A naive approach ("just ask GPT to judge the answer") fails because **the judge LLM can itself hallucinate**. The solution is **Retrieval-Augmented Judging (RAJ)**:

```
Question + Answer
      ↓
  Fetch real-world evidence from Wikipedia / Google
      ↓
  Feed (Question + Answer + Evidence) to LLM
      ↓
  LLM judges based ONLY on what the evidence says
```

This reduces false positives and makes the judge more reliable, because it is anchored to external ground truth.

### The 5-Layer Pipeline

The entire pipeline is implemented as a chain of discrete, independently testable layers:

```
Layer 1:  API Gateway         — HTTP entry point, request validation
Layer 2:  Query Preprocessor  — Claim extraction + query type classification
Layer 3:  Retrieval Engine    — Wikipedia + SerpAPI + routing + aggregation
Layer 4:  LLM Judge           — Evidence-grounded scoring via LLM
Layer 5:  Response Builder    — Maps score → user-friendly verdict
```

---

## 3. Project Structure (Fully Implemented)

```
AI-Hallucination-Risk-Assessment/
│
├── main.py                     # FastAPI app entrypoint, CORS, routing
├── requirements.txt            # All Python dependencies
├── .env / .env.example         # Environment configuration
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                   # Cross-cutting configuration & utilities
│   │   ├── config.py           # Pydantic Settings — env var loading
│   │   └── logging.py          # Centralised logger factory
│   │
│   ├── models/                 # Request & Response schemas (Pydantic v2)
│   │   ├── request.py          # VerifyRequest model
│   │   └── response.py         # VerifyResponse + JudgeResponse models
│   │
│   ├── api/
│   │   └── routes/
│   │       └── verify.py       # POST /api/verify + GET /api/health
│   │
│   ├── services/
│   │   ├── preprocessing/
│   │   │   └── query_preprocessor.py   # Layer 2
│   │   ├── retrieval/
│   │   │   ├── wikipedia_retriever.py  # Layer 3A
│   │   │   ├── serp_retriever.py       # Layer 3B
│   │   │   ├── source_router.py        # Layer 3C
│   │   │   └── evidence_aggregator.py  # Layer 3D
│   │   └── judge/
│   │       └── llm_judge.py            # Layer 4
│   │
│   └── utils/
│       └── cache.py            # In-memory cache skeleton (TTL-ready)
│
├── tests/                      # Test suite directory
├── chrome-extension/           # Browser extension frontend
│   ├── manifest.json
│   ├── popup.html / popup.js
│   ├── content.js
│   ├── background.js
│   └── ai-chat-injector.js
│
└── docs/
    ├── README.md
    ├── ARCHITECTURE.md
    ├── QUICKSTART.md
    ├── API_TESTING.md
    ├── VERIFICATION.md
    ├── CONTRIBUTING.md
    └── IMPLEMENTATION_PLAN.md
```

---

## 4. Layer-by-Layer Implementation Details

### Layer 1 — API Gateway (`app/api/routes/verify.py`)

**File**: `app/api/routes/verify.py`  
**Endpoints**: `POST /api/verify` and `GET /api/health`

This is the **orchestrator** of the entire pipeline. Every incoming request gets:
- A unique `request_id` (UUID) for end-to-end tracing
- A `pipeline_start` timestamp for latency measurement
- Step-by-step logging at each layer with per-step timing in milliseconds

**Request flow**:
```python
POST /api/verify
  Body: { "question": "...", "answer": "..." }

  → Layer 2: QueryPreprocessor.preprocess_async(question, answer)
  → Layer 3: SourceRouter().retrieve_evidence(claims, query_type)
  → Layer 3: EvidenceAggregator().aggregate(evidence_list)
  → Layer 4: LLMJudge().judge(question, answer, aggregated_evidence)
  → Layer 4b: LLMJudge().judge_per_claim(question, answer, evidence, claims)  ← NEW
  → Layer 5: VerifyResponse.from_judge_response(judge_response, sources, provider, model, ...)
```

**Error resilience**: Each layer is wrapped in `try/except`. If retrieval or aggregation fails, the pipeline continues with empty evidence. If the LLM judge fails, it falls back to a heuristic scorer. Only preprocessing failure results in HTTP 500.

**Response example**:
```json
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "Verified against Wikipedia. Paris is indeed the capital of France.",
  "flag": false,
  "sources_used": ["Wikipedia"],
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "processing_time_ms": 1250,
  "cache_hit": false,
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "claim_results": [
    {
      "claim_text": "Paris is the capital of France",
      "score": 95,
      "verdict": "accurate",
      "explanation": "Confirmed by Wikipedia."
    }
  ]
}
```

---

### Layer 2 — Query Preprocessor (`app/services/preprocessing/query_preprocessor.py`)

**Purpose**: Transform the raw answer into a set of searchable factual claims, and classify the question type so retrieval can be routed intelligently.

#### 2a. Claim Extraction

Uses a **pure heuristic pipeline** (no LLM call, no external dependency):

1. **Split** the answer into sentences using regex (with abbreviation protection — `Dr.`, `U.S.`, `etc.` are not split).
2. **Filter** for factual sentences:
   - Must be ≥ 15 characters
   - Must not be a question (`?`)
   - Must not be filler/opinion (pattern-matched against phrases like `"In summary"`, `"I believe"`, `"Feel free to"`)
3. **Clean** each sentence:
   - Strip leading connectors (`"However,"`, `"Also,"`, `"Moreover,"`)
   - Strip trailing punctuation (`.`, `!`, `;`, `:`)
   - Collapse whitespace
4. **Select** the top `max_claims` (default: 3) by sentence length (longer = more specific = better search query).

**Config**: `max_claims_per_request` is set in `.env` (default: 3).

#### 2b. Query Type Classification

Classifies the question using keyword/pattern matching (no LLM):

| Type | Detection | Routing Effect |
|---|---|---|
| `opinion_subjective` | `"should"`, `"recommend"`, `"what's better"` | Skip retrieval entirely |
| `numeric_statistical` | `"how many"`, `"how much"`, `"percentage"` | Query both Wikipedia + SerpAPI |
| `recent_event` | `"today"`, `"latest"`, `"2024"`, `"2025"`, `"2026"` | SerpAPI first, Wikipedia fallback |
| `encyclopedic` | Default fallback | Wikipedia + SerpAPI |

**Output**: A `ProcessedQuery` dataclass:
```python
@dataclass
class ProcessedQuery:
    original_question: str
    original_answer: str
    extracted_claims: list[str]   # Ready-to-search queries
    query_type: QueryType         # Literal enum
```

---

### Layer 3A — Wikipedia Retriever (`app/services/retrieval/wikipedia_retriever.py`)

**Implementation**: Direct async `httpx.AsyncClient` HTTP calls to the Wikipedia MediaWiki API  
**Free**: Yes — no API key required.  
**Best for**: Named entities, historical facts, biographical info, scientific concepts.

**Search strategy — multi-term fallback**:

Wikipedia's API works best with article titles, not sentences. So when given a claim like `"The 2022 FIFA World Cup was won by Argentina"`, the retriever:

1. Extracts multi-word entities first (e.g., `"2022 FIFA World Cup"`, `"Argentina"`)
2. Tries capitalized proper nouns
3. Tries acronyms (e.g., `"FIFA"`, `"NATO"`)
4. Falls back to the full query string

For each candidate term, it makes two async HTTP calls:
- **Search call**: `action=query&list=search` to find the best matching article title
- **Extract call**: `action=query&prop=extracts&exchars=2000` to fetch page content

Then extracts the top 5 most-relevant snippets ranked by keyword overlap. Results are cached in-memory.

**Returns**: Content string or `None` on failure.

---

### Layer 3B — SerpAPI Retriever (`app/services/retrieval/serp_retriever.py`)

**Library**: `google-search-results` (SerpAPI SDK)  
**Cost**: ~$0.01–$0.05 per search (gated behind API key check)  
**Best for**: Recent events, live news, current statistics.

**Search flow**:
1. If `serpapi_key` is empty or `"your_serpapi_key_here"`, skip and return `{"found": False}`.
2. Call Google Search via SerpAPI with `engine: google`, `num: 3`.
3. Extract:
   - **Answer Box** (Knowledge Graph snippet) — highest-quality result if present
   - **Organic results** — top 3 snippets
4. Join all snippets into a single evidence string.

**Graceful degradation**: If SerpAPI has no key or fails, the pipeline continues with whatever Wikipedia returned.

---

### Layer 3C — Source Router (`app/services/retrieval/source_router.py`)

**Purpose**: Decide which retrievers to call based on `query_type`.

**Routing table** (no LLM — pure logic):

```python
routing_rules = {
    "encyclopedic":        ["wikipedia", "serpapi"],
    "recent_event":        ["serpapi", "wikipedia"],  # SerpAPI first
    "numeric_statistical": ["wikipedia", "serpapi"],
    "opinion_subjective":  [],  # Skip — nothing to retrieve
}
```

**Iteration**: Loops over `claims × sources`. For each combination, it calls the appropriate retriever and collects evidence per source. Failures in any individual retrieval are caught and logged — they don't break the pipeline.

**Output**: `dict[str, str]` — e.g., `{"Wikipedia": "...", "SerpAPI": "..."}`.

---

### Layer 3D — Evidence Aggregator (`app/services/retrieval/evidence_aggregator.py`)

**Purpose**: Clean, deduplicate, rank, and trim raw evidence from multiple sources into a single high-quality string for the LLM judge.

**4-step pipeline**:

1. **Flatten** — Combined per-source strings are split back into individual paragraphs.

2. **Deduplicate**:
   - Exact duplicate removal (normalized: lowercase, strip punctuation, collapse whitespace)
   - Substring containment removal (if snippet A is entirely contained within snippet B, drop A)

3. **Rank** by quality score:
   - Medium-length snippets (50–500 chars): +3.0
   - 500–1000 chars: +2.0
   - >1000 chars: +1.0
   - Very short (<50 chars): +0.5
   - Contains numbers: +0.5 (numerical data is often factual)
   - Contains boilerplate phrases (`"click here"`, `"subscribe"`, `"cookie"`): −1.0 each

4. **Trim** to token budget (default: **2000 tokens ≈ 8,000 characters**):
   - Cuts at the last sentence boundary before the limit (not mid-sentence)
   - Configurable via `MAX_EVIDENCE_TOKENS` in `.env`

---

### Layer 4 — LLM Judge (`app/services/judge/llm_judge.py`)

This is the core intelligence of the system. It takes the question, answer, and aggregated evidence and returns a structured verdict.

#### Multi-Provider Support

Configured via `.env` — **no code changes needed to switch providers**:

| `LLM_PROVIDER` | SDK | Notes |
|---|---|---|
| `gemini` (default) | `openai` (compat endpoint) | Free tier available; `gemini-2.0-flash` default |
| `openai` | `openai` | GPT-4, GPT-4o, GPT-3.5-turbo |
| `grok` | `openai` (custom base URL) | `https://api.x.ai/v1` |
| `groq` | `openai` (custom base URL) | `https://api.groq.com/openai/v1` |
| `anthropic` | `anthropic` (native SDK) | Claude Sonnet/Haiku; uses `AsyncAnthropic` |

> **⚠️ Tested & Verified (May 2026):**
>
> | Provider | Model | Status |
> |----------|-------|--------|
> | **Groq** | `llama-3.3-70b-versatile` | ✅ **Working** — Free, ~3s judge response, recommended for development |
> | Gemini | `gemini-2.0-flash` | ⚠️ Free tier daily quota exhausts quickly |
> | OpenAI | `gpt-4` / `gpt-4o-mini` | ⚠️ Requires paid billing — free keys return `insufficient_quota` |
> | Groq | `llama3-70b-8192` | ❌ **Decommissioned** — use `llama-3.3-70b-versatile` instead |

#### Judge Prompt (Evidence-Grounded)

```
You are a fact-verification assistant.
You will be given a question, an AI-generated answer, and retrieved evidence from
trusted sources. Your job is to assess whether the answer is factually accurate
based solely on the evidence provided.

QUESTION: {question}
ANSWER: {answer}
EVIDENCE: {evidence}

Respond in JSON format:
{
  "score": <0-100>,
  "verdict": "<verified | likely_hallucination | unverifiable>",
  "explanation": "<1-2 sentences grounded in evidence>",
  "flag": <true if score < 60>
}
```

Key constraint: `"Only use information from the evidence provided."` This is what prevents the judge from hallucinating its verdict.

#### Heuristic Fallback Judge

When the LLM API is unavailable (no key, quota exceeded, network error), the system **does not crash** — it falls back to a keyword-overlap heuristic:

1. Extract all meaningful words (>3 chars) from the answer.
2. Count how many appear in the evidence text.
3. Compute `overlap = matches / total_words`.
4. Map: `score = 30 + (overlap × 62)` → clamped to [0, 100].
5. `score ≥ 70` → `verified`; `score ≥ 45` → `unverifiable`; else → `likely_hallucination`.

This ensures the system always returns a response, even without API credentials.

#### Response Parsing

The JSON parser handles:
- Markdown code blocks (` ```json ... ``` `)
- Raw JSON objects in plain text
- Fallback to heuristic on `JSONDecodeError`

---

### Layer 5 — Response Builder (`app/models/response.py`)

Converts the judge's internal `JudgeResponse` (internal verdict vocabulary) to the user-facing `VerifyResponse` (simplified vocabulary):

| Judge Score | Internal Verdict | User-Facing Verdict |
|---|---|---|
| 75 – 100 | `verified` | `accurate` ✅ |
| 40 – 74 | `unverifiable` | `uncertain` ⚠️ |
| 0 – 39 | `likely_hallucination` | `hallucination` 🚩 |

**Full response schema**:
```python
class VerifyResponse(BaseModel):
    score: int                              # 0-100
    verdict: Literal["accurate", "uncertain", "hallucination"]
    explanation: str                        # 1-2 sentences
    flag: bool                              # True if score < 60
    sources_used: Optional[list[str]]       # e.g. ["Wikipedia", "SerpAPI"]
    request_id: Optional[str]               # UUID for tracing
    processing_time_ms: Optional[int]       # End-to-end latency
    cache_hit: bool                         # True if served from cache
    provider: Optional[str]                 # LLM provider (gemini, anthropic, etc.)
    model: Optional[str]                    # Specific model (gemini-2.0-flash, etc.)
    claim_results: Optional[list[ClaimResult]]  # Per-claim scoring breakdown
```

---

## 5. Data Models

### Input (`VerifyRequest`)

```python
class VerifyRequest(BaseModel):
    question: str  # 5–2000 characters, whitespace-stripped
    answer: str    # 5–5000 characters, whitespace-stripped
```

Pydantic v2 field validators auto-strip whitespace. Violations → HTTP 422 Unprocessable Entity.

### Internal (`JudgeResponse`)

```python
class JudgeResponse(BaseModel):
    score: int      # 0-100, clamped
    verdict: Literal["verified", "likely_hallucination", "unverifiable"]
    explanation: str
    flag: bool      # score < 60
```

---

## 6. Configuration (`app/core/config.py` + `.env`)

All configuration is loaded from `.env` via `pydantic-settings`. No hardcoded secrets anywhere.

| Variable | Default | Description |
|---|---|---|
| `APP_DEBUG` | `false` | Enable debug mode + hot reload |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai`, `grok`, `groq`, `anthropic` |
| `LLM_API_KEY` | _(empty)_ | API key for the chosen LLM provider |
| `LLM_MODEL` | `gemini-2.0-flash` | Model name |
| `SERPAPI_KEY` | _(empty)_ | SerpAPI key (optional — graceful skip if absent) |
| `WIKIPEDIA_API_ENABLED` | `true` | Toggle Wikipedia retrieval |
| `CACHE_ENABLED` | `true` | Toggle in-memory cache |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL (1 hour) |
| `MAX_EVIDENCE_TOKENS` | `2000` | Evidence budget (~8,000 chars) |
| `MAX_CLAIMS_PER_REQUEST` | `3` | Max factual claims to extract per request |

Settings are cached with `@lru_cache()` — loaded once, reused across all requests.

---

## 7. Application Entry Point (`main.py`)

```python
app = FastAPI(
    title="AI Hallucination Detection Backend",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan   # Async startup/shutdown lifecycle
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)  # TODO: restrict in prod
app.include_router(verify_router)                             # /api/verify, /api/health

@app.get("/")
async def root():
    return {"name": ..., "version": ..., "status": "running"}
```

**CORS**: Currently open (`allow_origins=["*"]`) for development. Restrict to the Chrome extension origin in production.

**Startup/shutdown lifecycle**: Logs app name + version on boot, logs shutdown on stop.

**Run with**:
```bash
# Development with hot reload
uvicorn main:app --reload --port 8000

# Or via Python entrypoint
python main.py
```

---

## 8. Dependencies (`requirements.txt`)

```
# Core Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# External APIs
httpx>=0.25.0                     # Async HTTP (Wikipedia, general)
google-search-results>=2.4.0      # SerpAPI SDK

# LLM Clients
openai>=1.3.0                     # OpenAI / Gemini / Grok / Groq (compat endpoint)
anthropic>=0.39.0                 # Anthropic Claude (native AsyncAnthropic SDK)

# Optional Caching
redis==5.0.1                      # For production Redis cache

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

---

## 9. API Endpoints Reference

### `POST /api/verify`

Verifies an AI answer for hallucination risk.

**Request**:
```json
{
  "question": "What is the capital of France?",
  "answer": "The capital of France is Paris, located along the Seine River."
}
```

**Response (200 OK)**:
```json
{
  "score": 92,
  "verdict": "accurate",
  "explanation": "Verified against Wikipedia: Paris is the capital and largest city of France.",
  "flag": false,
  "sources_used": ["Wikipedia"],
  "request_id": "3f4a1b2c-d5e6-7890-abcd-ef1234567890",
  "processing_time_ms": 1480
}
```

**Error responses**:
| Status | Cause |
|---|---|
| 422 | Input validation failure (question/answer too short/long) |
| 500 | Preprocessing pipeline failure |

### `GET /api/health`

```json
{ "status": "ok", "service": "hallucination-detection" }
```

### `GET /`

```json
{ "name": "AI Hallucination Detection Backend", "version": "0.1.0", "status": "running" }
```

---

## 10. Logging & Observability

All logging uses a centralised factory from `app/core/logging.py`:

```python
logger = get_logger(__name__)  # Used in every module
```

Each request produces a structured log trail:
```
[req-id] Verification request received | question_len=45 answer_len=87
[req-id] Step 1: Preprocessing query
[req-id] Step 1 complete (12ms) | claims=2 type=encyclopedic
[req-id] Step 2: Retrieving evidence
[req-id] Step 2 complete (834ms) | sources_found=2
[req-id] Step 3: Aggregating evidence
[req-id] Step 3 complete (3ms) | evidence_chars=1842
[req-id] Step 4: Judging with LLM
[req-id] Step 4 complete (1102ms) | judge_score=92 judge_verdict=verified
[req-id] Verification complete (1951ms) | score=92 verdict=accurate
```

---

## 11. Error Handling & Graceful Degradation

| Failure Point | Behaviour |
|---|---|
| Input too short/long | HTTP 422 with Pydantic detail |
| Wikipedia timeout/failure | **Continue** with empty evidence, log warning |
| SerpAPI missing key | Skip silently, log warning |
| SerpAPI API error | **Continue** with empty evidence, log error |
| LLM API unavailable | **Fall back** to keyword-overlap heuristic judge |
| LLM returns invalid JSON | **Fall back** to heuristic judge |
| Preprocessing crash | HTTP 500 |

The system is designed so that **only a preprocessing crash returns an error**. Everything else degrades gracefully, ensuring a response is always returned.

---

## 12. Caching (`app/utils/cache.py`)

A `CacheManager` skeleton is implemented with:
- In-memory dict store
- TTL awareness (structure in place, TTL eviction logic marked `TODO`)
- Global singleton `cache_manager` instance

**Next step**: Wire it into the retrieval layer — cache `(claim, source) → evidence` with `CACHE_TTL_SECONDS` (default 1 hour) to avoid duplicate API calls for the same query.

**Production path**: Swap the in-memory dict for a Redis client (dependency already in `requirements.txt`).

---

## 13. Chrome Extension Frontend

Located in `chrome-extension/`. Key files:

| File | Role |
|---|---|
| `manifest.json` | Extension manifest (permissions, content scripts) |
| `popup.html/js` | Extension popup UI |
| `content.js` | Injected into web pages to capture AI responses |
| `ai-chat-injector.js` | Monitors AI chat interfaces, intercepts Q&A pairs |
| `background.js` | Service worker for message routing |

The extension captures `(question, answer)` pairs from AI platforms (ChatGPT, Gemini, etc.) and POSTs them to `http://localhost:8000/api/verify`, then displays the score badge inline.

---

## 14. What Was Planned vs. What Was Implemented

This table maps the original design decisions from the planning phase to their actual implementation status:

| Planned | Implemented As | Notes |
|---|---|---|
| 5-layer pipeline | ✅ Fully built | Exact layer structure as planned |
| Regex-based claim extraction (Option A) | ✅ Implemented | Deliberate choice; no LLM overhead |
| Wikipedia retrieval | ✅ Implemented | Multi-term fallback search |
| SerpAPI retrieval | ✅ Implemented | Graceful skip if no key |
| Source routing (if/else) | ✅ Implemented | No LLM needed |
| Evidence aggregation | ✅ Implemented | Dedup + rank + trim |
| LLM judge (Gemini default) | ✅ Implemented | Multi-provider: Gemini, OpenAI, Grok, Groq |
| Heuristic fallback judge | ✅ Implemented | Keyword overlap scoring |
| Evidence token budget (2000) | ✅ Implemented | Configurable via env |
| Pydantic v2 models | ✅ Implemented | Full validation |
| UUID request tracing | ✅ Implemented | Per-request UUID in logs + response |
| Per-step timing | ✅ Implemented | Millisecond timing logged per step |
| Caching layer | 🔶 Skeleton only | Structure in place, TTL eviction TODO |
| Async I/O for retrieval | ✅ Fully async | All methods use `httpx.AsyncClient`, `AsyncOpenAI`, `AsyncAnthropic` |
| Anthropic/Claude support | ✅ Implemented | Native `AsyncAnthropic` SDK, routes through all judge methods |
| Per-claim scoring | ✅ Implemented | `judge_per_claim()` + `ClaimResult` model + Chrome Extension UI |
| Redis caching | 🔶 In-memory only | Structure in place, Redis wiring is next step |

---


## 15. Quick Reference

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set LLM_API_KEY, optionally SERPAPI_KEY

# Run server
uvicorn main:app --reload --port 8000
```

### Quick Test
```bash
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{"question": "Who invented the telephone?", "answer": "Alexander Graham Bell invented the telephone in 1876."}'
```

### Interactive API Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---


