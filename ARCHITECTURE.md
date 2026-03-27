# Development Notes & Architecture Details

## System Overview

### Problem Statement
AI language models generate confident but sometimes incorrect answers. This system detects hallucinations by:
1. Retrieving evidence from trusted sources
2. Grounding an LLM judge in that evidence
3. Returning a hallucination risk score to users

### Why Evidence-Grounded Judging?
- **Pure GPT-as-a-Judge Problem**: LLM judge itself can hallucinate
- **Solution**: Provide external evidence (Wikipedia, SerpAPI) to ground the judge
- **Benefit**: Reduces false positives and improves reliability

## Architecture Deep Dive

### Layer 1: API Gateway (verify.py)
```
Request: {"question": "...", "answer": "..."}
        ↓
   [Pydantic Validation]
        ↓
   [Coordinate Pipeline]
        ↓
   Call Layer 2 → Layer 3 → Layer 4 → Layer 5
        ↓
Response: {"score": 0-100, "verdict": "...", ...}
```

**Key Responsibility**: Orchestrate the entire pipeline
**Testability**: Mock the services to test orchestration

### Layer 2: Query Preprocessor
```
Answer: "Paris is the capital of France"
        ↓
  [Claim Extraction]
        ↓
  - "Paris is capital of France"
  - "Location: France"
        ↓
  [Query Type Detection]
        ↓
  Type: "encyclopedic" → Route to Wikipedia
```

**Implementation Strategy**:
- **Option A (Simple)**: Regex-based claim extraction + keyword matching
  - Pros: Fast, no external dependencies
  - Cons: Less accurate on complex sentences
- **Option B (Better)**: Small LLM call to extract claims
  - Pros: More accurate claim extraction
  - Cons: Adds one API call per request
- **Recommendation**: Start with Option A, upgrade to B based on feedback

### Layer 3: Retrieval Engine (Most Complex)

#### Part A: Wikipedia Retriever
```
Claim: "Paris is capital of France"
        ↓
[Call Wikipedia API with search query]
        ↓
[Extract top 2 paragraphs from article]
        ↓
Evidence: "Paris is the capital and largest city of France..."
```

**Technical Details**:
- Library: `wikipedia-api` (not `wikipedia`)
- Timeout: Set 5-10 second timeout for robustness
- Error handling: Return `{"found": False}` on failures

#### Part B: SerpAPI Retriever
```
Claim: "New COVID variant discovered Jan 2024"
        ↓
[Call SerpAPI with Google search]
        ↓
[Extract top 3 search result snippets]
        ↓
Evidence: [Snippet 1, Snippet 2, Snippet 3]
```

**Cost Consideration**:
- SerpAPI costs ~$0.01-0.05 per call
- **Gate it**: Only call if Wikipedia lacks results OR query_type == "recent_event"

#### Part C: Source Router
```
Query Type Detection (from Layer 2)
        ↓
Routing Rules:
  - "encyclopedic" → Wikipedia only
  - "recent_event" → SerpAPI first, Wikipedia fallback
  - "numeric_statistical" → Both
  - "opinion_subjective" → Skip retrieval
        ↓
Selected Sources: []
```

**No LLM call here** - Just simple if/else logic

#### Part D: Evidence Aggregator
```
[Wikipedia snippet] + [SerpAPI results] + [Additional sources]
        ↓
[Step 1: Deduplicate]
  Remove exact duplicates and near-duplicates (fuzzy matching optional)
        ↓
[Step 2: Rank by Relevance]
  Wikipedia snippets ranked higher (more reliable)
  Shorter, clearer snippets prioritized
        ↓
[Step 3: Trim to Budget]
  Max 800 tokens (~3200 chars)
  Keep important info, drop boilerplate
        ↓
Final Evidence (ready for judge)
```

**Token Estimation**:
- 1 token ≈ 4 characters (rough estimate)
- 800 tokens ≈ 3200 characters

### Layer 4: LLM Judge
```
System Prompt: [Fact-verification instructions]
User Input:
  QUESTION: {question}
  ANSWER: {answer}
  EVIDENCE: {evidence}
        ↓
   [LLM processes]
        ↓
JSON Response:
{
  "score": 85,
  "verdict": "verified",
  "explanation": "...",
  "flag": false
}
```

**Prompt Design Matters**:
- Emphasize using ONLY provided evidence
- Ask for specific JSON format
- Include score range (0-100) definition
- Request 1-2 sentence explanation

**Supported LLM Providers** (implement in config):
- OpenAI: GPT-4, GPT-3.5-turbo
- Anthropic: Claude 3, Claude 2
- Azure OpenAI
- Locally hosted: LLaMA, Mistral, etc.

### Layer 5: Response Builder
```
Judge Output: {"score": 85, "verdict": "verified", ...}
        ↓
[Map to User-Friendly Verdict]
  75-100 → "accurate"
  40-74 → "uncertain"
  0-39 → "hallucination"
        ↓
Final Response:
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "...",
  "flag": false,
  "sources_used": ["Wikipedia"]
}
```

## Key Design Decisions

### 1. Handling Unverifiable Claims
**Scenario**: Wikipedia and SerpAPI find no relevant evidence

**Decision**: Return neutral score (50) with "unverifiable" verdict
- More honest than treating lack of evidence as hallucination
- User can manually verify using other sources
- Alternative: Mark as risky (score 30), but this could be too aggressive

**Decision File**: `app/models/response.py`

### 2. Single vs. Per-Claim Scoring
**Option A**: Single score for entire answer (Current)
- Simpler UI/UX
- Easier to display to users
- Cons: Loses granularity (one false claim tanks whole answer)

**Option B**: Per-claim scores
- More precise assessment
- Can show which specific claims are risky
- Cons: Complex UI, harder to present to users

### 3. Evidence Budget
**Decision**: ~800 tokens max for judge input
- Keeps API costs low
- Prevents context window overflow
- Balances precision vs. cost

## Data Flow Through Full Pipeline

```
User Input (Extension/Postman)
        ↓
POST /verify {"question": "Q", "answer": "A"}
        ↓
[Layer 1] Input validation, route to pipeline
        ↓
[Layer 2] Extract claims, determine type
        ↓
[Layer 3A] Wikipedia search (if applicable)
[Layer 3B] SerpAPI search (if applicable)
[Layer 3C-D] Aggregate + trim evidence
        ↓
[Layer 4] Judge: "Q + A + Evidence → Score"
        ↓
[Layer 5] Format response
        ↓
Response to frontend/extension
        ↓
User sees: Score badge + Explanation
```

## Error Handling Strategy

### What Can Go Wrong?

1. **Input Validation Fails** → HTTP 422
2. **External API Down** (Wikipedia/SerpAPI)
   - Graceful degradation: Continue with partial evidence
   - Log the error, mark source as unavailable
3. **LLM API Timeout**
   - Return neutral score (50)
   - Log error with context
4. **Invalid JSON from Judge**
   - Parse error → Return generic response
   - Log raw response for debugging

### Implementation Pattern
```python
try:
    result = retrieve_evidence(claim)
except TimeoutError:
    logger.warning("Wikipedia timeout, continuing")
    result = {"found": False}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    result = {"found": False}

# Continue pipeline, handle empty results gracefully
```

## Performance Optimization Opportunities

### 1. Caching (Low Hanging Fruit)
- Cache evidence retrieval by claim hash
- TTL: 1 hour (might change if configured)
- Backend: In-memory for dev, Redis for prod

### 2. Batch Processing
- Accept multiple Q&A pairs in single request
- Process in parallel
- Return batch results

### 3. Async I/O
- Wikipedia API calls can be concurrent
- SerpAPI calls can be concurrent
- But don't exceed rate limits

### 4. Smart Routing
- If answer length > 500 chars, extract multiple claims
- If query type is "opinion", skip retrieval entirely
- If score confidence high, skip SerpAPI (save $)

## Testing Strategy

### Unit Tests
- Test each layer independently
- Mock external APIs (Wikipedia, SerpAPI, LLM)
- Test edge cases (empty evidence, invalid JSON)

### Integration Tests
- Test full pipeline with mock services
- Test error scenarios (API down, timeout)
- Test various query types

### End-to-End Tests
- Test with real APIs (limited, to avoid costs)
- Test with real LLM judge
- Monitor latency and success rates

### Test Data
- Simple claims (Paris is capital)
- Complex claims (historical events)
- Recent events (2024 news)
- Opinions/subjective claims
- Hallucinations (false claims)

## Security Considerations

### Input Validation
- Validate question/answer length
- Sanitize before passing to external APIs
- Reject potentially harmful inputs

### API Keys
- Load from environment only
- Never log API keys
- Rotate on schedule

### CORS
- Currently allows all origins (dev mode)
- Restrict to extension origin in production
- Add rate limiting per IP

### Evidence Provenance
- Track which source provided evidence
- Cite sources in response
- Allow users to verify sources

## Monitoring & Observability

### Logging
- Use consistent logger from `app.core.logging`
- Log at appropriate levels (info, warning, error)
- Include context (claim, source, score) in logs

### Metrics to Track
- Request latency by layer
- Evidence retrieval success rate
- Judge scoring distribution
- Cost per request (API calls)

### Debugging Helpers
- Log full pipeline path
- Track which retrievers were called
- Show evidence aggregation steps

## Future Enhancements

1. **More Retrieval Sources**
   - ArXiv for academic claims
   - Court records for legal facts
   - Company filings for financial data

2. **Fine-tuned Judge**
   - Train on labelled Q&A with hallucinations
   - Better accuracy than generic LLM

3. **Explainability**
   - Show which evidence supported which score
   - Highlight conflicting evidence
   - Confidence intervals, not just scores

4. **User Feedback Loop**
   - Users mark verdicts as correct/incorrect
   - Fine-tune judge based on feedback
   - Improve claim extraction

5. **Multilingual Support**
   - Extend to other languages
   - Handle translation of evidence

## References & Resources

- [Retrieval-Augmented Generation (RAG)](https://arxiv.org/abs/2005.11401)
- [Factuality in Language Models](https://arxiv.org/abs/2311.07700)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)
- [Pydantic Validation](https://docs.pydantic.dev/)
