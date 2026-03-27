# Implementation Assignment Sheet

Use this document to track which team member is responsible for which layer/component.

## Layer 1: API Gateway
**File**: `app/api/routes/verify.py`
**Status**: Core structure done, needs refinement
**Assigned to**: 
**Tasks**:
- [x] Route structure
- [x] Pydantic validation  
- [x] Pipeline orchestration
- [ ] Error handling refinement
- [ ] Add request/response logging

**Blockers**: None (can test with mocked services)

---

## Layer 2: Query Preprocessor
**File**: `app/services/preprocessing/query_preprocessor.py`
**Status**: Stub with TODOs
**Assigned to**: 
**Tasks**:
- [ ] Implement `extract_claims()` - Use either:
  - Regex-based + heuristics (simpler, start here)
  - Small LLM call (more accurate, add later)
- [ ] Implement `determine_query_type()` - Classify query for routing
- [ ] Add tests

**Blockers**: None (can use test data)

---

## Layer 3A: Wikipedia Retriever
**File**: `app/services/retrieval/wikipedia_retriever.py`
**Status**: Stub with TODOs
**Assigned to**: 
**Tasks**:
- [ ] Install `wikipedia-api` library
- [ ] Implement `search()` method
- [ ] Extract first 2 paragraphs as evidence
- [ ] Add error handling (timeouts, not found)
- [ ] Add tests with mock Wikipedia responses

**Blockers**: None (free API, no key needed)

**Testing**:
```python
retriever = WikipediaRetriever()
result = retriever.search("Paris")
assert result["found"] == True
assert "France" in result["content"].lower()
```

---

## Layer 3B: SerpAPI Retriever
**File**: `app/services/retrieval/serp_retriever.py`
**Status**: Stub with TODOs
**Assigned to**: 
**Tasks**:
- [ ] Install `google-search-results` library
- [ ] Implement `search()` method
- [ ] Extract top 3 search snippets
- [ ] Add API key validation
- [ ] Add error handling (invalid key, rate limits)
- [ ] **Watch cost**: ~$0.01-0.05 per call

**Blockers**: Needs SerpAPI key in `.env`

**Testing**:
```python
# Test with mock responses first
retriever = SerpAPIRetriever()
result = retriever.search("Paris")
assert isinstance(result["results"], list)
```

---

## Layer 3C: Source Router
**File**: `app/services/retrieval/source_router.py`
**Status**: Routing rules defined, implementation needed
**Assigned to**: 
**Tasks**:
- [ ] Implement `retrieve_evidence()` method
- [ ] Call Wikipedia and/or SerpAPI based on query type
- [ ] Handle partial failures (one source down, continue with other)
- [ ] Add tests

**Blockers**: Needs Layer 3A and 3B implementations

---

## Layer 3D: Evidence Aggregator
**File**: `app/services/retrieval/evidence_aggregator.py`
**Status**: Stub with TODOs
**Assigned to**: 
**Tasks**:
- [ ] Implement `deduplicate()` - Remove duplicate snippets
- [ ] Implement `rank_evidence()` - Prioritize by relevance
- [ ] Implement `trim_to_budget()` - Fit within token limit
- [ ] Add tests with various evidence inputs

**Blockers**: None (pure Python logic)

**Testing**:
```python
evidence = ["Fact A", "Fact A", "Fact B"]
deduped = aggregator.deduplicate(evidence)
assert len(deduped) == 2  # "Fact A" deduplicated
```

---

## Layer 4: LLM Judge
**File**: `app/services/judge/llm_judge.py`
**Status**: Prompt template ready, implementation needed
**Assigned to**: 
**Tasks**:
- [ ] Choose LLM provider (OpenAI, Anthropic, etc.)
- [ ] Install client library
- [ ] Implement `judge()` method to call LLM
- [ ] Parse JSON response from LLM
- [ ] Add error handling (timeouts, invalid JSON)
- [ ] Add tests

**Blockers**: Needs LLM API key in `.env`

**LLM Provider Options**:
- OpenAI (most tested, `pip install openai`)
- Anthropic Claude (good, `pip install anthropic`)
- Azure OpenAI (if using Azure)
- Local LLM (Ollama, LLaMA)

**Testing**:
```python
judge = LLMJudge()
response = judge.judge(
    "What is Paris?",
    "It's a city",
    "Paris is the capital of France"
)
assert 0 <= response.score <= 100
```

---

## Layer 5: Response Builder
**File**: `app/models/response.py`
**Status**: Mapping logic done, tested needed
**Assigned to**: 
**Tasks**:
- [x] Create `VerifyResponse` model
- [x] Implement `from_judge_response()` factory method
- [ ] Add tests for score→verdict mapping
- [ ] Verify validation works

**Blockers**: None (depends on Layer 4 response format)

---

## Supporting Components

### Configuration & Logging
**Files**: `app/core/config.py`, `app/core/logging.py`
**Status**: ✅ Done
**Assigned to**: N/A

### Models
**Files**: `app/models/request.py`, `app/models/response.py`
**Status**: ✅ Done
**Assigned to**: N/A

### Caching (Optional - Phase 2)
**File**: `app/utils/cache.py`
**Status**: Stub
**Assigned to**: 
**Priority**: Medium (optimize after core works)
**Tasks**:
- [ ] Implement in-memory caching
- [ ] Optional: Add Redis support

---

## Integration Checkpoints

### Checkpoint 1: Basic Validation (Week 1)
- [ ] Layer 1 working (accepts requests)
- [ ] Layer 2 working (extracts claims)
- [ ] Can test with curl

### Checkpoint 2: Evidence Retrieval (Week 2)
- [ ] Layer 3A working (Wikipedia)
- [ ] Layer 3B working (SerpAPI - optional)
- [ ] Layer 3C+D working (routing + aggregation)

### Checkpoint 3: End-to-End Verification (Week 3)
- [ ] Layer 4 working (LLM judge)
- [ ] Layer 5 working (response formatting)
- [ ] Full pipeline end-to-end ✅

### Checkpoint 4: Hardening (Week 4)
- [ ] Error handling
- [ ] Caching
- [ ] Tests
- [ ] Documentation

---

## Testing Plans

### Unit Testing by Layer
Each layer should have corresponding test file:
- `tests/test_models.py` - Request/response validation
- `tests/test_preprocessor.py` - Claim extraction & routing
- `tests/test_retrievers.py` - Wikipedia & SerpAPI
- `tests/test_judge.py` - LLM judge
- `tests/test_integration.py` - Full pipeline

### Manual Testing via Postman
```
POST http://localhost:8000/api/verify
{
  "question": "What is the capital of France?",
  "answer": "Paris is the capital of France."
}
```

**Expected**: Score ~85-100, verdict "accurate"

---

## Communication Log

| Date | Update | Assigned To |
|------|--------|-------------|
| - | Initial structure created | - |
| | Layer 1 routing implemented | |
| | Layer 2 claim extraction done | |
| | Layer 3 retrievers completed | |
| | Layer 4 judge integrated | |
| | Full pipeline tested | |

---

## Questions & Blockers

**Question 1**: Which LLM provider should we use?
- Recommendation: Start with OpenAI GPT-4 (most reliable)
- Review options before assigning Layer 4

**Question 2**: How do we handle unverifiable claims?
- Decision: Return score=50 with "unverifiable" verdict
- May adjust based on user feedback

**Question 3**: What about caching?
- Phase 2 feature: Implement after core pipeline works
- Can use simple in-memory cache initially

---

## Assignment Template

For team members, fill in your name:

```
## Layer [X]: [Name]
**Assigned to**: [Your Name]
**Start Date**: [Date]
**Target Completion**: [Date]
**Status**: [Not Started / In Progress / Completed]
```
