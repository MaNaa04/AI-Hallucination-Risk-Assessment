# 🛡️ TruthLens — AI Hallucination Detection System

> **Real-time, plug-and-play AI fact-checking.** Chrome extension + backend pipeline + analytics dashboard.  
> Verify AI-generated claims against Wikipedia and SerpAPI in seconds.

---

## 🚀 What is TruthLens?

TruthLens is a complete AI hallucination detection system that:

1. **Chrome Extension** — Detects AI chat interfaces (ChatGPT, Gemini, Claude) and adds inline fact-checking, or verify any selected text via the popup
2. **Backend API** — 5-layer pipeline that extracts claims, retrieves evidence from multiple sources, and judges accuracy with an LLM
3. **Analytics Dashboard** — Two dashboards for monitoring verification stats, preprocessing insights, and pipeline performance

---

## 📁 Project Structure

```
TruthLens/
│
├── chrome-extension/           # 🧩 Chrome Extension (frontend)
│   ├── manifest.json           #    Extension manifest
│   ├── popup.html / popup.js   #    Extension popup UI
│   ├── content.js              #    Page content script
│   ├── ai-chat-injector.js     #    Auto-inject into AI chat UIs
│   └── background.js           #    Service worker
│
├── app/                        # ⚙️ Backend (FastAPI)
│   ├── api/routes/
│   │   ├── verify.py           #    POST /api/verify — main endpoint
│   │   └── analytics.py        #    GET /api/analytics/* — dashboard data
│   ├── services/
│   │   ├── preprocessing/
│   │   │   └── query_preprocessor.py  # Claim extraction & query typing
│   │   ├── retrieval/
│   │   │   ├── wikipedia_retriever.py # Wikipedia evidence
│   │   │   ├── serp_retriever.py      # SerpAPI web search
│   │   │   ├── source_router.py       # Smart routing
│   │   │   └── evidence_aggregator.py # Dedup, rank, trim evidence
│   │   ├── judge/
│   │   │   └── llm_judge.py           # LLM-based verdict (Groq/Gemini)
│   │   └── analytics/
│   │       └── tracker.py             # Event storage & stats
│   ├── models/
│   │   ├── request.py          #    VerifyRequest model
│   │   └── response.py         #    VerifyResponse model
│   └── core/
│       ├── config.py           #    Settings & environment
│       └── logging.py          #    Shared logger
│
├── dashboard/                  # 📊 Basic Dashboard
│   ├── index.html              #    Overview, history, live verify
│   ├── styles.css
│   └── app.js
│
├── analytics-dashboard/        # 📈 Advanced Analytics Dashboard
│   ├── index.html              #    5 tabs with Chart.js visuals
│   ├── styles.css              #    Premium dark glassmorphism theme
│   └── app.js                  #    Charts, pipeline breakdown
│
├── tests/                      # 🧪 Tests
│   ├── test_preprocessor.py
│   └── test_retrievers.py
│
├── data/                       # 💾 Analytics data (auto-created)
│   └── verification_events.json
│
├── main.py                     # 🏁 FastAPI entrypoint
├── requirements.txt            # 📦 Python dependencies
├── .env.example                # 🔑 Environment template
└── README.md                   # 📄 This file
```

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd AI-Hallucination-Risk-Assessment

# Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | ✅ | `gemini` (free) or `openai` |
| `LLM_API_KEY` | ✅ | Your LLM API key |
| `LLM_MODEL` | ✅ | Model name (e.g. `gemini-2.0-flash`) |
| `SERPAPI_KEY` | ✅ | SerpAPI key for web search |
| `WIKIPEDIA_API_ENABLED` | — | `true` (default) |
| `MAX_CLAIMS_PER_REQUEST` | — | `3` (default) |
| `MAX_EVIDENCE_TOKENS` | — | `800` (default) |

### 3. Start the Backend

```bash
python main.py
```

Server starts at **http://localhost:8000**

### 4. Access Everything

| What | URL | Description |
|------|-----|-------------|
| 🔗 **API Docs** | http://localhost:8000/docs | Swagger UI — test endpoints |
| 📊 **Basic Dashboard** | http://localhost:8000/dashboard | Overview + history + live verify |
| 📈 **Analytics Dashboard** | http://localhost:8000/analytics | Deep pipeline insights (5 tabs) |
| ❤️ **Health Check** | http://localhost:8000/api/health | Backend status |

### 5. Install Chrome Extension

1. Open **chrome://extensions/** in Chrome
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `chrome-extension/` folder
4. The TruthLens icon appears in your toolbar

---

## 🧩 Chrome Extension

The extension works in two modes:

### Manual Mode (Popup)
- Click the TruthLens icon in the toolbar
- Paste any AI-generated text → click **Verify Claims**
- Or **select text on any page** → the popup auto-fills it

### Auto-Inject Mode
- Works on supported AI platforms: **ChatGPT**, **Google Gemini**, **Claude**
- Automatically adds a "Verify" button to AI responses
- Inline fact-checking without leaving the page

### Dashboard Links
- The extension footer has links to both the **Analytics Dashboard** and **Basic Dashboard**

---

## 📈 Analytics Dashboard

The advanced analytics dashboard at `/analytics` has **5 tabs**:

| Tab | What it shows |
|-----|---------------|
| **Overview** | KPI cards, verdict donut chart, score histogram, sources pie, score trend line |
| **Preprocessing** | Query type distribution, sentence→claim funnel, preprocessing timeline |
| **Pipeline** | Per-stage waterfall chart (preprocessing/retrieval/judging), stage share, latency percentiles |
| **History** | Searchable/filterable table with query type badges, verdict badges, source tags |
| **Live Verify** | Verify text with full pipeline breakdown — see extracted claims, query type, per-stage timing |

---

## 🔌 API Reference

### `POST /api/verify`

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
  "explanation": "Verified against Wikipedia. Paris is indeed the capital of France.",
  "flag": false,
  "sources_used": ["Wikipedia"],
  "request_id": "a1b2c3d4-...",
  "processing_time_ms": 1250
}
```

**Score Ranges:**
- `75–100` → ✅ **Accurate** — verified against sources
- `40–74` → ⚠️ **Uncertain** — partially verified or mixed evidence
- `0–39` → 🚩 **Hallucination** — contradicted by sources

### `GET /api/analytics/stats`
Aggregate verification statistics (totals, averages, distributions).

### `GET /api/analytics/history?limit=50`
Recent verification history (newest first).

### `GET /api/analytics/preprocessing`
Preprocessing-specific stats (query types, claim extraction metrics).

### `GET /api/analytics/pipeline`
Per-stage pipeline performance (preprocessing, retrieval, judging timing).

### `GET /api/health`
Health check — returns `{"status": "ok"}`.

---

## 🏗️ Architecture

TruthLens uses a **5-layer pipeline**:

```
User Input → [Layer 1: API Gateway]
                    ↓
             [Layer 2: Query Preprocessor]
                - Split into sentences
                - Filter factual claims
                - Classify query type (encyclopedic / recent_event / numeric / opinion)
                    ↓
             [Layer 3: Evidence Retrieval]
                - Wikipedia (encyclopedic facts)
                - SerpAPI (recent events, web search)
                - Aggregate & deduplicate evidence
                    ↓
             [Layer 4: LLM Judge]
                - Evidence-grounded evaluation
                - Score 0–100 with explanation
                    ↓
             [Layer 5: Response Builder]
                - Map score to verdict
                - Format for frontend
```

### Why Evidence-Grounded Judging?
- Pure "LLM-as-judge" has its own hallucination risk
- Grounding the judge in retrieved evidence dramatically reduces false positives
- Wikipedia + SerpAPI provide diverse, reliable sources

---

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/ -v

# Manual test with curl
curl -X POST "http://localhost:8000/api/verify" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who invented the telephone?", "answer": "Alexander Graham Bell invented the telephone in 1876."}'
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| **Backend won't start** | Check `.env` exists and has valid API keys |
| **"Backend offline" in extension** | Make sure `python main.py` is running on port 8000 |
| **Port 8000 in use** | Run `lsof -ti:8000 \| xargs kill -9` then restart |
| **Score always 50** | LLM API key may be invalid or quota exceeded |
| **No sources found** | Check `SERPAPI_KEY` is valid; verify `WIKIPEDIA_API_ENABLED=true` |
| **Extension not loading** | Reload extension at `chrome://extensions/`, check Developer mode is ON |

---

## 📚 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| LLM | Gemini (default) / OpenAI / Groq |
| Evidence | Wikipedia API, SerpAPI |
| Extension | Chrome Manifest V3, vanilla JS |
| Dashboards | HTML/CSS/JS, Chart.js |
| Data | JSON file storage (no external DB) |

---

## 📄 License

MIT License
