/**
 * AI Chat Injector - Adds "Verify" buttons to AI chat interfaces
 * Works with: ChatGPT, Claude, Gemini, Perplexity, etc.
 * Displays results in a right-side panel (like Gemini)
 */

const API_URL = "http://localhost:8000/api/verify";
let isInjecting = false;

// Create and manage right-side panel
let rightPanel = null;

function createRightPanel() {
  if (rightPanel && document.body.contains(rightPanel)) {
    return rightPanel;
  }

  const panel = document.createElement("div");
  panel.id = "hd-right-panel";
  panel.innerHTML = `
    <div id="hd-panel-header">
      <h3 id="hd-panel-title">Fact Check Results</h3>
      <button id="hd-panel-close" aria-label="Close">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
    <div id="hd-panel-content"></div>
  `;

  // Panel styles
  const styles = `
    #hd-right-panel {
      position: fixed;
      right: 0;
      top: 0;
      width: 420px;
      height: 100vh;
      background: white;
      box-shadow: -2px 0 12px rgba(0, 0, 0, 0.15);
      display: flex;
      flex-direction: column;
      z-index: 9999;
      animation: hd-slide-in 0.3s ease-out;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    }

    @keyframes hd-slide-in {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }

    @keyframes hd-slide-out {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(100%);
        opacity: 0;
      }
    }

    #hd-panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid #e5e5e5;
      background: #f8f9fa;
    }

    #hd-panel-title {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #202124;
    }

    #hd-panel-close {
      background: none;
      border: none;
      padding: 4px;
      cursor: pointer;
      color: #5f6368;
      transition: color 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    #hd-panel-close:hover {
      color: #202124;
    }

    #hd-panel-content {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .hd-panel-result {
      background: white;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      border: 1px solid #e5e5e5;
    }

    .hd-result-score {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }

    .hd-result-verdict {
      font-size: 16px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #202124;
    }

    .hd-score-circle {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 20px;
      color: white;
    }

    .hd-score-verified {
      background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    }

    .hd-score-uncertain {
      background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
    }

    .hd-score-hallucination {
      background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
    }

    .hd-result-explanation {
      font-size: 13px;
      color: #5f6368;
      line-height: 1.6;
      margin-bottom: 12px;
    }

    .hd-result-sources {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .hd-source-badge {
      display: inline-block;
      background: #f1f3f4;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 12px;
      color: #5f6368;
      border: 1px solid #dadce0;
    }

    .hd-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 16px;
      color: #5f6368;
    }

    .hd-spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #dadce0;
      border-top: 3px solid #667eea;
      border-radius: 50%;
      animation: hd-spin 1s linear infinite;
      margin-bottom: 12px;
    }

    @keyframes hd-spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .hd-error {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #ffebee;
      padding: 16px;
      border-radius: 8px;
      border: 1px solid #ef5350;
    }

    .hd-error-icon {
      color: #dc3545;
      font-size: 20px;
    }

    .hd-error-text {
      color: #5f6368;
      font-size: 13px;
    }

    /* Responsive for smaller screens */
    @media (max-width: 1024px) {
      #hd-right-panel {
        width: 360px;
      }
    }

    @media (max-width: 768px) {
      #hd-right-panel {
        width: 100%;
      }
    }
  `;

  const styleSheet = document.createElement("style");
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);

  document.body.appendChild(panel);

  // Close button handler
  panel.querySelector("#hd-panel-close").addEventListener("click", closeRightPanel);

  rightPanel = panel;
  return panel;
}

function closeRightPanel() {
  if (rightPanel) {
    rightPanel.style.animation = "hd-slide-out 0.3s ease-out";
    setTimeout(() => {
      if (rightPanel && document.body.contains(rightPanel)) {
        rightPanel.remove();
      }
      rightPanel = null;
    }, 300);
  }
}

// Detect which AI platform we're on
const AI_PLATFORMS = {
  chatgpt: {
    match: () => window.location.hostname.includes("chatgpt.com") || window.location.hostname.includes("chat.openai.com"),
    messageSelector: 'div[data-message-author-role="assistant"] .markdown',
    containerSelector: 'div[data-message-author-role="assistant"]',
  },
  claude: {
    match: () => window.location.hostname.includes("claude.ai"),
    messageSelector: 'div[data-is-streaming="false"] .font-claude-message',
    containerSelector: 'div[data-is-streaming="false"]',
  },
  gemini: {
    match: () => window.location.hostname.includes("gemini.google.com"),
    messageSelector: '.model-response-text',
    containerSelector: '.model-response',
  },
  perplexity: {
    match: () => window.location.hostname.includes("perplexity.ai"),
    messageSelector: '.prose',
    containerSelector: '.answer-container',
  },
};

// Get current platform
function getCurrentPlatform() {
  for (const [name, config] of Object.entries(AI_PLATFORMS)) {
    if (config.match()) {
      return { name, ...config };
    }
  }
  return null;
}

// Initialize injector
function init() {
  const platform = getCurrentPlatform();
  if (!platform) {
    console.log("[Hallucination Detector] Not on a supported AI platform");
    return;
  }

  console.log(`[Hallucination Detector] Detected platform: ${platform.name}`);

  // Watch for new messages
  const observer = new MutationObserver(() => {
    if (!isInjecting) {
      isInjecting = true;
      setTimeout(() => {
        injectButtons(platform);
        isInjecting = false;
      }, 500);
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  // Initial injection
  setTimeout(() => injectButtons(platform), 1000);
}

// Inject verify buttons
function injectButtons(platform) {
  const messages = document.querySelectorAll(platform.messageSelector);

  messages.forEach((message) => {
    const container = message.closest(platform.containerSelector);
    if (!container || container.querySelector(".hd-verify-btn")) {
      return; // Already has button
    }

    const text = message.textContent.trim();
    if (text.length < 20) return; // Too short to verify

    const button = createVerifyButton(text);
    insertButton(container, button, platform.name);
  });
}

// Create styled verify button
function createVerifyButton(text) {
  const button = document.createElement("button");
  button.className = "hd-verify-btn";
  button.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M9 11l3 3L22 4"></path>
      <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"></path>
    </svg>
    Verify Facts
  `;

  // Add styles
  Object.assign(button.style, {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    fontSize: "13px",
    fontWeight: "500",
    color: "#667eea",
    background: "transparent",
    border: "1px solid #667eea",
    borderRadius: "6px",
    cursor: "pointer",
    transition: "all 0.2s",
    marginTop: "8px",
    fontFamily: "inherit",
  });

  button.addEventListener("mouseenter", () => {
    button.style.background = "#667eea";
    button.style.color = "white";
  });

  button.addEventListener("mouseleave", () => {
    button.style.background = "transparent";
    button.style.color = "#667eea";
  });

  button.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    verifyText(text, button);
  });

  return button;
}

// Insert button into container
function insertButton(container, button, platform) {
  // Different insertion logic per platform
  if (platform === "chatgpt") {
    container.appendChild(button);
  } else if (platform === "claude") {
    container.appendChild(button);
  } else if (platform === "gemini") {
    container.appendChild(button);
  } else {
    container.appendChild(button);
  }
}

// Verify text via API
async function verifyText(text, button) {
  // Open right panel with loading state
  const panel = createRightPanel();
  const content = panel.querySelector("#hd-panel-content");

  content.innerHTML = `
    <div class="hd-loading">
      <div class="hd-spinner"></div>
      <div>Checking facts...</div>
    </div>
  `;

  button.disabled = true;
  button.style.opacity = "0.6";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: "Is this statement factually accurate?",
        answer: text,
      }),
    });

    if (!response.ok) {
      throw new Error("Server error");
    }

    const data = await response.json();
    showResultInPanel(data);
    button.disabled = false;
    button.style.opacity = "1";
  } catch (err) {
    console.error("[Hallucination Detector] Error:", err);

    content.innerHTML = `
      <div class="hd-error">
        <div class="hd-error-icon">⚠️</div>
        <div class="hd-error-text">
          Cannot connect to server. Make sure the backend is running at http://localhost:8000
        </div>
      </div>
    `;

    button.disabled = false;
    button.style.opacity = "1";
  }
}

// Show verification result in right panel
function showResultInPanel(data) {
  const { score, verdict, explanation, sources_used } = data;
  const panel = createRightPanel();
  const content = panel.querySelector("#hd-panel-content");

  // Determine score category for styling
  let scoreClass = "hd-score-uncertain";
  if (score >= 75) scoreClass = "hd-score-verified";
  else if (score < 40) scoreClass = "hd-score-hallucination";

  // Verdict display
  const verdictText = {
    verified: "✅ Verified",
    accurate: "✅ Likely Accurate",
    uncertain: "⚠️ Uncertain",
    unverifiable: "❓ Unverifiable",
    hallucination: "🚩 Hallucination Detected",
    likely_hallucination: "🚩 Likely Hallucination",
  }[verdict] || "❓ Uncertain";

  // Build sources HTML
  let sourcesHTML = "";
  if (sources_used && sources_used.length > 0) {
    const sourceBadges = sources_used
      .map((source) => `<span class="hd-source-badge">${source}</span>`)
      .join("");
    sourcesHTML = `
      <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e5e5;">
        <div style="font-size: 12px; color: #5f6368; font-weight: 500; margin-bottom: 8px;">Sources Used:</div>
        <div class="hd-result-sources">
          ${sourceBadges}
        </div>
      </div>
    `;
  }

  content.innerHTML = `
    <div class="hd-panel-result">
      <div class="hd-result-score">
        <div class="hd-result-verdict">${verdictText}</div>
        <div class="hd-score-circle ${scoreClass}">${score}</div>
      </div>
      <div class="hd-result-explanation">
        ${explanation}
      </div>
      ${sourcesHTML}
    </div>

    <div style="padding: 0 16px; margin-top: 24px;">
      <div style="font-size: 13px; color: #5f6368; line-height: 1.6;">
        <strong>Score Interpretation:</strong><br>
        75-100: Highly reliable<br>
        50-74: Mixed reliability<br>
        0-49: Low reliability
      </div>
    </div>
  `;
}

// Initialize when page loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

console.log("[Hallucination Detector] Content script loaded");
