const API_URL = "http://localhost:8000/api/verify";

document.addEventListener("DOMContentLoaded", () => {
  const textArea = document.getElementById("ai-text");
  const verifyBtn = document.getElementById("verify-btn");
  const loader = document.getElementById("loader");
  const resultDiv = document.getElementById("result");
  const errorMsg = document.getElementById("error-msg");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");

  const verdictEl = document.getElementById("verdict");
  const scoreEl = document.getElementById("score");
  const scoreBadge = document.getElementById("score-badge");
  const resultHeader = document.getElementById("result-header");
  const explanationEl = document.getElementById("explanation");
  const sourcesEl = document.getElementById("sources");

  // Check backend connectivity
  checkBackend();

  // Grab selected text from the active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) return;
    chrome.scripting.executeScript(
      {
        target: { tabId: tabs[0].id },
        function: getSelectionText,
      },
      (injectionResults) => {
        if (injectionResults && injectionResults[0]?.result) {
          textArea.value = injectionResults[0].result;
        }
      }
    );
  });

  // Listen for context menu verify requests
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === "VERIFY_TEXT" && message.text) {
      textArea.value = message.text;
      runVerification(message.text);
    }
  });

  // Verify button click
  verifyBtn.addEventListener("click", () => {
    const text = textArea.value.trim();
    if (!text) {
      showError("Please select or paste text to verify.");
      return;
    }
    runVerification(text);
  });

  async function runVerification(text) {
    // Show loading state
    verifyBtn.disabled = true;
    loader.style.display = "block";
    resultDiv.style.display = "none";
    errorMsg.style.display = "none";

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: "General Context",
          answer: text,
        }),
      });

      if (!res.ok) throw new Error("Backend returned an error");

      const data = await res.json();
      showResult(data);
    } catch (err) {
      showError("Cannot reach backend. Make sure the server is running at localhost:8000");
    } finally {
      verifyBtn.disabled = false;
      loader.style.display = "none";
    }
  }

  function showResult(data) {
    const { score, verdict, explanation, sources_used } = data;

    resultDiv.style.display = "block";

    // Verdict
    const verdictMap = {
      accurate: "✅ Likely Accurate",
      verified: "✅ Verified",
      uncertain: "⚠️ Uncertain",
      unverifiable: "❓ Unverifiable",
      hallucination: "🚩 Hallucination Detected",
      likely_hallucination: "🚩 Likely Hallucination",
    };
    verdictEl.textContent = verdictMap[verdict] || "❓ Unknown";

    // Score
    scoreEl.textContent = score;

    // Score styling
    resultHeader.className = "result-header";
    scoreBadge.className = "score-badge";

    if (verdict === "accurate" || verdict === "verified") {
      resultHeader.classList.add("accurate");
      scoreBadge.classList.add("high");
    } else if (verdict === "uncertain" || verdict === "unverifiable") {
      resultHeader.classList.add("uncertain");
      scoreBadge.classList.add("mid");
    } else {
      resultHeader.classList.add("hallucination");
      scoreBadge.classList.add("low");
    }

    // Explanation
    explanationEl.textContent = explanation;

    // Sources
    if (sources_used && sources_used.length > 0) {
      sourcesEl.innerHTML = sources_used
        .map((s) => `<span class="source-tag">${s}</span>`)
        .join("");
    } else {
      sourcesEl.innerHTML = '<span class="source-tag">None</span>';
    }
  }

  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
    setTimeout(() => {
      errorMsg.style.display = "none";
    }, 5000);
  }

  async function checkBackend() {
    try {
      const res = await fetch("http://localhost:8000/", { method: "GET" });
      if (res.ok) {
        statusDot.classList.remove("offline");
        statusText.textContent = "Backend connected";
      } else {
        throw new Error();
      }
    } catch {
      statusDot.classList.add("offline");
      statusText.textContent = "Backend offline — start the server";
    }
  }
});

// Runs in context of active web page
function getSelectionText() {
  return window.getSelection().toString();
}