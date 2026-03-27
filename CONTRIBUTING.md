# Contributing Guide

## Development Setup

### 1. Clone Repository
```bash
git clone <repo-url>
cd ai-hallucination-detection
git checkout -b feature/your-feature
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment
```bash
cp .env.example .env
# Fill in your API keys in .env
```

## Code Organization

Each layer has its own directory with clear responsibilities:

- **Layer 1**: `app/api/routes/` - Request validation & orchestration
- **Layer 2**: `app/services/preprocessing/` - Query understanding
- **Layer 3**: `app/services/retrieval/` - Evidence retrieval & aggregation
- **Layer 4**: `app/services/judge/` - LLM-based verification
- **Layer 5**: `app/models/response.py` - Response formatting

## Adding a Feature

### Example: Implement Wikipedia Retriever

1. **Find the TODO**:
   ```bash
   grep -r "TODO" app/services/retrieval/wikipedia_retriever.py
   ```

2. **Read the requirements**: Each TODO comment explains what to implement

3. **Implement the function**:
   ```python
   def search(self, query: str, max_results: int = 2) -> dict:
       """Your implementation here"""
       pass
   ```

4. **Test locally**:
   ```python
   python -c "
   from app.services.retrieval.wikipedia_retriever import WikipediaRetriever
   retriever = WikipediaRetriever()
   result = retriever.search('Paris')
   print(result)
   "
   ```

5. **Commit with clear message**:
   ```bash
   git add app/services/retrieval/wikipedia_retriever.py
   git commit -m "feat(retrieval): implement Wikipedia search with paragraph extraction"
   ```

## Code Style Guidelines

### Type Hints
Always use type hints:
```python
def process_query(question: str, max_length: int = 100) -> dict:
    """Always include return type."""
    pass
```

### Docstrings
Use Google-style docstrings:
```python
def extract_claims(answer: str, max_claims: int = 3) -> list[str]:
    """
    Extract key factual claims from an answer.
    
    Args:
        answer: The AI-generated answer
        max_claims: Maximum number of claims to extract
        
    Returns:
        List of extracted claims
        
    Raises:
        ValueError: If answer is empty
    """
```

### Logging
Use the shared logger:
```python
from app.core.logging import get_logger
logger = get_logger(__name__)

logger.info("Processing claim")
logger.warning("No evidence found")
logger.error("API call failed", exc_info=True)
```

### Error Handling
Handle errors gracefully and log them:
```python
try:
    result = retrieve_evidence(claim)
except APIError as e:
    logger.error(f"Retrieval failed: {e}", exc_info=True)
    return {"found": False, "evidence": None}
```

## Testing

### Running Tests
```bash
pytest tests/
pytest tests/test_models.py -v  # Verbose
pytest -k "test_verify" --tb=short  # Specific tests
```

### Writing Tests
Create tests in `tests/` directory following the layer structure:
```python
# tests/test_preprocessing.py
import pytest
from app.services.preprocessing.query_preprocessor import QueryPreprocessor

def test_extract_claims():
    result = QueryPreprocessor.extract_claims("Paris is in France")
    assert len(result) > 0
    assert "Paris" in str(result)

def test_determine_query_type():
    query_type = QueryPreprocessor.determine_query_type("When was X born?")
    assert query_type == "encyclopedic"
```

## Git Workflow

### Branch Naming
```
feature/layer-number-feature-name
fix/layer-number-bug-description
docs/description
```

### Commit Messages
```
feat(layer2): implement claim extraction

Add heuristic-based claim extraction using spaCy.
Routes extracted claims to appropriate retrievers.

Fixes #123
```

### Pull Request Process
1. Create feature branch
2. Implement feature (see layer TODOs)
3. Test locally
4. Push and create PR with clear description
5. Link related issues
6. Request review from team members
7. Address feedback
8. Merge when approved

## Debugging

### Enable Debug Mode
```bash
# In .env
APP_DEBUG=true

# Run with reload
python main.py
```

### Check Logs
```bash
# Detailed logs from specific module
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from app.services.retrieval.wikipedia_retriever import WikipediaRetriever
retriever = WikipediaRetriever()
result = retriever.search('test')
print(result)
"
```

### Use FastAPI Debugger
Visit `http://localhost:8000/docs` for interactive API testing

## Common Tasks

### Implement a Retriever
1. Create file in `app/services/retrieval/`
2. Implement `search()` and `get_evidence()` methods
3. Update `SourceRouter.retrieve_evidence()` to call your retriever
4. Add configuration to `.env.example`

### Add LLM Provider Support
1. Install library: `pip install anthropic`
2. Update `app/services/judge/llm_judge.py`
3. Initialize client in `__init__()`
4. Implement `judge()` method
5. Update config with new API key and model

### Extend Evidence Aggregation
1. Edit `app/services/retrieval/evidence_aggregator.py`
2. Add new methods to aggregation pipeline
3. Test with various evidence inputs
4. Update README documentation

## Performance Tips

### Caching
- Enable in `.env`: `CACHE_ENABLED=true`
- Cache expensive API calls (Wikipedia, SerpAPI)
- Use Redis for multi-instance deployments

### Async Operations
- FastAPI is async-native
- Use `async def` for I/O-bound operations
- Use `await` for database/API calls

### Token Efficiency
- Trim evidence to ~800 tokens (config)
- Remove boilerplate before judge call
- Batch multiple queries when possible

## Troubleshooting

### "Module not found" error
```bash
python -m pip install -r requirements.txt --force-reinstall
```

### Port 8000 already in use
```bash
# Change port in .env or run on different port
python main.py --port 8001
```

### API key not working
- Check `.env` file has correct key
- Verify key has appropriate permissions
- Check API account isn't rate-limited

## Questions?

1. Check README.md for architecture overview
2. Look at existing implementations for patterns
3. Check TODO comments for implementation guides
4. Ask in team Slack/Discord
