/**
 * AI Hallucination Detector - Content Script
 * Runs on all pages to enable text selection and context menu verification
 */

// Listen for messages from background script or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "GET_SELECTION") {
    const selectedText = window.getSelection()?.toString() || "";
    sendResponse({ text: selectedText });
  }

  if (message.action === "SHOW_RESULT") {
    showResultOverlay(message.result);
  }

  return true; // Keep message channel open for async response
});

/**
 * Create and show a floating result overlay on the page
 */
function showResultOverlay(result) {
  // Remove existing overlay if present
  const existing = document.getElementById("hallucination-detector-overlay");
  if (existing) {
    existing.remove();
  }

  const { score, verdict, explanation, sources_used } = result;

  // Create overlay container
  const overlay = document.createElement("div");
  overlay.id = "hallucination-detector-overlay";
  overlay.innerHTML = `
    <div class="hd-header">
      <span class="hd-title">🔍 AI Hallucination Check</span>
      <button class="hd-close">&times;</button>
    </div>
    <div class="hd-content">
      <div class="hd-verdict ${verdict}">${getVerdictDisplay(verdict)}</div>
      <div class="hd-score">Score: <strong>${score}</strong>/100</div>
      <div class="hd-explanation">${explanation}</div>
      <div class="hd-sources">Sources: ${sources_used?.join(", ") || "None"}</div>
    </div>
  `;

  // Add styles
  const styles = document.createElement("style");
  styles.textContent = `
    #hallucination-detector-overlay {
      position: fixed;
      top: 20px;
      right: 20px;
      width: 320px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      animation: hd-slide-in 0.3s ease-out;
    }

    @keyframes hd-slide-in {
      from {
        opacity: 0;
        transform: translateX(20px);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }

    .hd-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid #eee;
      background: #f8f9fa;
      border-radius: 12px 12px 0 0;
    }

    .hd-title {
      font-weight: 600;
      color: #333;
    }

    .hd-close {
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      color: #666;
      padding: 0;
      line-height: 1;
    }

    .hd-close:hover {
      color: #333;
    }

    .hd-content {
      padding: 16px;
    }

    .hd-verdict {
      font-size: 16px;
      font-weight: 600;
      padding: 8px 12px;
      border-radius: 6px;
      margin-bottom: 12px;
    }

    .hd-verdict.accurate {
      background: #d4edda;
      color: #155724;
    }

    .hd-verdict.uncertain {
      background: #fff3cd;
      color: #856404;
    }

    .hd-verdict.hallucination {
      background: #f8d7da;
      color: #721c24;
    }

    .hd-score {
      margin-bottom: 8px;
      color: #555;
    }

    .hd-explanation {
      margin-bottom: 12px;
      color: #333;
      line-height: 1.5;
    }

    .hd-sources {
      font-size: 12px;
      color: #888;
      border-top: 1px solid #eee;
      padding-top: 8px;
    }
  `;

  document.head.appendChild(styles);
  document.body.appendChild(overlay);

  // Close button handler
  overlay.querySelector(".hd-close").addEventListener("click", () => {
    overlay.remove();
  });

  // Auto-close after 15 seconds
  setTimeout(() => {
    if (document.getElementById("hallucination-detector-overlay")) {
      overlay.remove();
    }
  }, 15000);
}

/**
 * Get display text for verdict
 */
function getVerdictDisplay(verdict) {
  const verdictMap = {
    "accurate": "✅ Likely Accurate",
    "uncertain": "⚠️ Uncertain",
    "hallucination": "🚩 Potential Hallucination"
  };
  return verdictMap[verdict] || verdict;
}

// Log that content script is loaded (for debugging)
console.log("[AI Hallucination Detector] Content script loaded");
