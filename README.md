# AI Hallucination Detection System

A complete system to detect AI hallucinations using evidence-grounded verification with Wikipedia and web search sources. **Uses FREE Google Gemini API!**

## Features

- **Evidence-Grounded Verification**: Uses Wikipedia and SerpAPI for fact-checking
- **Smart Query Routing**: Routes queries to appropriate sources based on content type
- **FREE LLM Judge**: Uses Google Gemini (completely free!) for evaluation
- **Chrome Extension**: Right-click to verify any AI-generated text
- **Production Ready**: Complete implementation with error handling

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────────────┐
│ Chrome Extension│     │              FastAPI Backend                 │
│   (popup.js)    │────▶│                                             │
│   (content.js)  │     │  ┌─────────┐   ┌───────────┐   ┌─────────┐ │
│   (background.js│  POST│  │ Layer 1 │──▶│  Layer 2  │──▶│ Layer 3 │ │
└─────────────────┘ /verify│  │  API    │   │Preprocessor│  │Retrieval│ │
                         │  └─────────┘   └───────────┘   └────┬────┘ │
                         │                                      │      │
                         │  ┌─────────┐   ┌───────────┐        ▼      │
                         │  │ Layer 5 │◀──│  Layer 4  │◀── Wikipedia  │
                         │  │Response │   │Gemini Judge│◀── SerpAPI   │
                         │  └─────────┘   └───────────┘               │
                         └─────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone & Install Dependencies

```bash
git clone <your-repo>
cd AI-Hallucination-Risk-Assessment

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Get FREE Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key

### 3. Configure Environment

```bash
# Copy example env file
copy .env.example .env  # On Mac/Linux: cp .env.example .env

# Edit .env and add your API keys:
# - GEMINI_API_KEY (required): Your FREE Gemini API key
# - SERPAPI_KEY (optional): For web search verification
```

### 4. Start the Backend

```bash
python main.py
```

Server starts at `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### 5. Install Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder

### 6. Test the System

**Via API:**

```bash
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the capital of France?",
    "answer": "The capital of France is Paris."
  }'
```

**Via Extension:**

1. Select any AI-generated text on a webpage
2. Right-click → "Check for Hallucination"
3. Or click the extension icon and paste text

## Project Structure

```
AI-Hallucination-Risk-Assessment/
├── app/
│   ├── api/routes/
│   │   └── verify.py              # API endpoint
│   ├── core/
│   │   ├── config.py              # Settings
│   │   └── logging.py             # Logger
│   ├── models/
│   │   ├── request.py             # Input validation
│   │   └── response.py            # Output formatting
│   └── services/
│       ├── preprocessing/
│       │   └── query_preprocessor.py   # Claim extraction
│       ├── retrieval/
│       │   ├── wikipedia_retriever.py  # Wikipedia API
│       │   ├── serp_retriever.py       # Google Search API
│       │   ├── source_router.py        # Query routing
│       │   └── evidence_aggregator.py  # Evidence processing
│       └── judge/
│           └── llm_judge.py            # Gemini verification
├── chrome-extension/
│   ├── manifest.json
│   ├── popup.html
│   ├── popup.js
│   ├── content.js
│   ├── background.js
│   └── icons/
├── main.py                        # FastAPI app
├── requirements.txt
├── .env.example
└── README.md
```

## API Reference

### POST /api/verify

Verify if an AI answer contains hallucinations.

**Request:**

```json
{
  "question": "What is the capital of France?",
  "answer": "The capital of France is Paris, located on the Seine River."
}
```

**Response:**

```json
{
  "score": 85,
  "verdict": "accurate",
  "explanation": "Verified against Wikipedia. Paris is confirmed as the capital of France.",
  "flag": false,
  "sources_used": ["wikipedia"]
}
```

**Score Interpretation:**
| Score Range | Verdict | Meaning |
|-------------|---------|---------|
| 75-100 | accurate | Verified by evidence |
| 40-74 | uncertain | Partially verified, manual check recommended |
| 0-39 | hallucination | Contradicted or unsupported by evidence |

### GET /api/health

Health check endpoint.

```json
{ "status": "ok", "service": "hallucination-detection" }
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key (FREE!) |
| `GEMINI_MODEL` | No | `gemini-1.5-flash` | Model for verification |
| `SERPAPI_KEY` | No | - | For web search (optional) |
| `DEBUG` | No | `false` | Enable debug mode |
| `PORT` | No | `8000` | Server port |

### Supported Gemini Models (All FREE!)

- `gemini-1.5-flash` (recommended - fast & free)
- `gemini-1.5-pro` (more capable, still free)
- `gemini-pro` (older version)

## How It Works

### Query Type Detection

The system automatically classifies queries:

| Type | Routes To | Example |
|------|-----------|---------|
| encyclopedic | Wikipedia | "When was Einstein born?" |
| recent_event | SerpAPI → Wikipedia | "What happened in 2024 elections?" |
| numeric_statistical | Both | "What is the population of Tokyo?" |
| opinion_subjective | Skip retrieval | "Is Python a good language?" |

### Verification Pipeline

1. **Preprocessing**: Extract key claims from the answer
2. **Routing**: Determine which sources to query
3. **Retrieval**: Fetch evidence from Wikipedia/SerpAPI
4. **Aggregation**: Deduplicate, rank, and trim evidence
5. **Judging**: Gemini evaluates answer against evidence
6. **Response**: Format user-friendly result

## Chrome Extension Usage

### Popup Mode

1. Click extension icon
2. Paste or select text
3. Click "Verify Facts"

### Context Menu Mode

1. Select text on any webpage
2. Right-click → "Check for Hallucination"
3. Result appears as overlay on page

### Keyboard Shortcut

- `Ctrl+Enter` in popup to verify

## Troubleshooting

### "Cannot connect to server"

- Ensure backend is running: `python main.py`
- Check port 8000 is not in use

### "Gemini API key not configured"

- Create `.env` file from `.env.example`
- Add your Gemini API key from [AI Studio](https://aistudio.google.com/app/apikey)

### Score always 50

- Gemini API key missing or invalid
- Check logs for API errors

### Wikipedia returns no results

- Try more specific search terms
- Check internet connection

## Cost Considerations

| Component | Cost |
|-----------|------|
| Wikipedia API | FREE |
| Google Gemini | FREE |
| SerpAPI | ~$0.01-0.05/search (100 free/month) |

**Total Cost: $0** (without SerpAPI)

## License

MIT License - see LICENSE file

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## Credits

Built with:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Wikipedia-API](https://pypi.org/project/wikipedia-api/)
- [Google Gemini](https://ai.google.dev/)
- [SerpAPI](https://serpapi.com/)
