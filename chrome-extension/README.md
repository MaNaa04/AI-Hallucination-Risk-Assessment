# 🔍 AI Hallucination Detector - Chrome Extension

A professional Chrome extension that helps you verify AI-generated content in real-time. Works seamlessly with ChatGPT, Claude, Gemini, Perplexity, and more!

## ✨ Features

### 1. **Popup Verification**
- Select any AI-generated text on any webpage
- Click the extension icon
- Get instant fact verification with sources

### 2. **Inline Verification with Right-Side Panel** ⭐ NEW!
- Automatically adds "Verify Facts" buttons to AI chat responses
- Works on:
  - ✅ ChatGPT (chatgpt.com, chat.openai.com)
  - ✅ Claude (claude.ai)
  - ✅ Gemini (gemini.google.com)
  - ✅ Perplexity (perplexity.ai)
- Click the button next to any AI response
- **Professional right-side panel appears** (like Google Gemini!)
  - 📊 Score circle (0-100) with gradient colors
  - ✅/⚠️/🚩 Verdict with icon
  - 📝 Complete explanation
  - 🔗 Source attribution (Wikipedia, SerpAPI)
  - 📖 Score interpretation guide
  - Smooth slide-in animation

### 3. **Smart Verification**
- Uses Wikipedia + Web Search (SerpAPI) for evidence
- Powered by Groq LLM for intelligent fact-checking
- Shows confidence scores (0-100)
- Displays sources used for verification

## 🚀 Installation

### Step 1: Start the Backend Server

Make sure your backend is running:

```bash
# Navigate to project root
cd AI-Hallucination-Risk-Assessment

# Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder from this project
5. The extension icon should appear in your toolbar!

### Step 3: Pin the Extension (Optional)

1. Click the puzzle piece icon in Chrome toolbar
2. Find "AI Hallucination Detector"
3. Click the pin icon to keep it visible

## 📖 How to Use

### Method 1: Popup Verification

1. Go to any AI chat (ChatGPT, Gemini, etc.)
2. Select the AI's response text
3. Click the extension icon
4. The selected text will appear in the popup
5. Click **Verify Facts**
6. View results with score and explanation

### Method 2: Right-Side Panel Verification (Recommended!)

1. Go to ChatGPT, Claude, Gemini, or Perplexity
2. Start a conversation with the AI
3. Look for the **"Verify Facts"** button that appears below AI responses
4. Click it
5. Watch the **professional right-side panel slide in from the right**
6. See results with:
   - 📊 Score (0-100) in a gradient circle
     - 🟢 Green (75-100) = Verified
     - 🟡 Orange (40-74) = Uncertain
     - 🔴 Red (0-39) = Hallucination
   - Clear verdict (✅ Verified, ⚠️ Uncertain, 🚩 Hallucination)
   - Full explanation
   - Source badges
   - Score interpretation guide
7. Close with the X button or reload page

## 🎨 UI Design

### Right-Side Panel Features
- **Modern gradient styling** - Clean, professional appearance
- **Slide-in animation** - Smooth entrance from right (0.3s)
- **Gradient score circles** - Color-coded by confidence level
- **Responsive layout** - Works on all screen sizes
- **Professional typography** - System fonts, proper spacing
- **Source badges** - Shows Wikipedia, SerpAPI, or both

### Popup Design
- **Purple gradient header** (#667eea to #764ba2)
- **Color-coded results** - Green/Yellow/Red by verdict
- **Clean card layout** - Professional, not AI-generated
- **Smooth animations**

## 🔧 Configuration

The extension connects to `http://localhost:8000/api/verify` by default.

If you need to change the API URL, edit:
- `popup.js` - Line 5: `const API_URL = "..."`
- `ai-chat-injector.js` - Line 7: `const API_URL = "..."`

## 🐛 Troubleshooting

### "Cannot connect to server" error

**Problem**: Backend is not running

**Solution**:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Verify button not appearing on AI chats

**Problem**: Content script not loading

**Solutions**:
1. Reload the extension: Go to `chrome://extensions/` → Click reload icon
2. Refresh the AI chat webpage (F5)
3. Make sure you're on a supported platform (ChatGPT, Claude, Gemini, Perplexity)
4. Check console (F12) for errors

### Right panel not appearing when clicking button

**Problem**: Content script not injected

**Solutions**:
1. Go to `chrome://extensions/`
2. Find "AI Hallucination Detector" and click reload
3. Refresh ChatGPT/Gemini page
4. Ask AI a new question and try again
5. Check F12 console for "[Hallucination Detector] Detected platform: ..."

### Extension icon not appearing

**Problem**: Extension not loaded properly

**Solutions**:
1. Check `chrome://extensions/` - Extension should be enabled
2. Try removing and re-adding the extension
3. Check developer console (F12) for errors

### Results show only Wikipedia sources

**Problem**: SerpAPI key not configured

**Solution**: See [SERPAPI_SETUP.md](../SERPAPI_SETUP.md) in project root
- Get free SerpAPI key: https://serpapi.com/users/sign_up
- Add to `.env`: `SERPAPI_KEY=your_key`
- Restart backend

## 📊 Understanding Results

### Verdict Types

| Verdict | Icon | Score Range | Meaning |
|---------|------|-------------|---------|
| Verified | ✅ | 75-100 | Fully supported by evidence |
| Likely Accurate | ✅ | 70-84 | Mostly verified |
| Uncertain | ⚠️ | 40-69 | Partially verified, needs review |
| Unverifiable | ❓ | 40-69 | No evidence found |
| Likely Hallucination | 🚩 | 30-49 | Poorly supported |
| Hallucination | 🚩 | 0-29 | Contradicted by evidence |

### Score Interpretation

- **85-100**: Highly reliable, backed by strong evidence
- **70-84**: Generally reliable, minor gaps
- **50-69**: Mixed reliability, verify manually
- **30-49**: Low reliability, likely incorrect
- **0-29**: Not reliable, contradicts evidence

## 🧪 Testing

### Test Case 1: Recent Event (Should Verify ✅)
```
Question: Who won FIFA World Cup 2022?
AI Answer: Argentina won FIFA World Cup 2022.
Expected: Right panel shows 90-95 score, ✅ Verified
```

### Test Case 2: Hallucination (Should Flag 🚩)
```
Question: What year did Albert Einstein invent the telephone?
AI Answer: Albert Einstein invented the telephone in 1876.
Expected: Right panel shows 0-20 score, 🚩 Hallucination Detected
```

### Test Case 3: Unverifiable (Should Show ⚠️)
```
Question: What is the best programming language?
AI Answer: Python is the best programming language.
Expected: Right panel shows 40-60 score, ⚠️ Uncertain
```

## 🔐 Privacy

- Extension only sends text you explicitly verify
- No data is stored or logged
- All processing happens via your local backend
- No third-party tracking

## 📝 Files

```
chrome-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Popup UI
├── popup.js              # Popup functionality
├── content.js            # General content script
├── ai-chat-injector.js   # AI chat injector (right-side panel)
├── background.js         # Background service worker
├── icons/                # Extension icons
│   └── icon.svg
└── README.md             # This file
```

## 🚀 Next Steps

1. **Test current setup** (works without SerpAPI)
   - Backend functional with Wikipedia
   - Extension fully ready
   - Right-side panel works perfectly

2. **Get SerpAPI key** (optional but recommended)
   - Improves accuracy for recent events
   - 100 free searches/month
   - Takes 2 minutes to set up

3. **Test on different AI platforms**
   - Try ChatGPT, Claude, Gemini, Perplexity
   - Verify different claim types
   - See right panel in action!

4. **Customize if needed**
   - Change UI colors in `popup.html`
   - Adjust button styles in `ai-chat-injector.js`
   - Modify panel width (currently 420px, responsive)
   - Tweak animation timing (currently 0.3s)

## 💡 Tips

- Right-side panel appears on the right edge of your browser
- Panel closes smoothly with X button
- Keyboard shortcut: Use Ctrl+Enter in popup to verify
- Results are fresh for each query
- Reload extension to fix any loading issues

---

**Fact-check AI responses with professional style!** 🎯
