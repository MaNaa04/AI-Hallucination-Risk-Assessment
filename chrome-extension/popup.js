/**
 * AI Hallucination Detector - Popup Script
 * Handles text verification via FastAPI backend
 */

const API_URL = "http://localhost:8000/api/verify";

document.addEventListener("DOMContentLoaded", () => {
  const textArea = document.getElementById("ai-text");
  const verifyBtn = document.getElementById("verify-btn");
  const loader = document.getElementById("loader");
  const resultDiv = document.getElementById("result");

  const verdictEl = document.getElementById("verdict");
  const scoreEl = document.getElementById("score");
  const explanationEl = document.getElementById("explanation");
  const sourcesEl = document.getElementById("sources");

  // On open, get the highlighted text from the active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]?.id) {
      textArea.placeholder = "Paste AI-generated text here to verify...";
      return;
    }

    chrome.scripting.executeScript(
      {
        target: { tabId: tabs[0].id },
        function: getSelectionText,
      },
      (injectionResults) => {
        if (chrome.runtime.lastError) {
          console.log("Cannot access this page:", chrome.runtime.lastError.message);
          textArea.placeholder = "Paste AI-generated text here to verify...";
          return;
        }

        if (injectionResults && injectionResults[0]?.result) {
          textArea.value = injectionResults[0].result;
          textArea.placeholder = "Text loaded from selection. Click Verify Facts.";
        } else {
          textArea.placeholder = "Highlight text on any site, or paste here...";
        }
      }
    );
  });

  // Verify button click handler
  verifyBtn.addEventListener("click", async () => {
    const textToVerify = textArea.value.trim();

    if (!textToVerify) {
      showError("Please highlight or paste text to verify.");
      return;
    }

    if (textToVerify.length < 10) {
      showError("Text is too short. Please provide more content.");
      return;
    }

    // Show loading state
    setLoading(true);
    resultDiv.style.display = "none";
    resultDiv.className = "";

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: "Is this statement factually accurate?",
          answer: textToVerify
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      displayResult(data);

    } catch (err) {
      console.error("Verification error:", err);

      if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
        showError("Cannot connect to server. Make sure the backend is running: python main.py");
      } else {
        showError(err.message);
      }
    } finally {
      setLoading(false);
    }
  });

  // Handle Ctrl+Enter to verify
  textArea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.ctrlKey) {
      verifyBtn.click();
    }
  });

  function displayResult(data) {
    const { score, verdict, explanation, sources_used, flag } = data;

    resultDiv.style.display = "block";
    scoreEl.textContent = score;
    explanationEl.textContent = explanation;
    sourcesEl.textContent = sources_used?.length > 0
      ? sources_used.join(", ")
      : "No external sources";

    // Update UI based on verdict
    const verdictMap = {
      "accurate": { text: "✅ Likely Accurate", class: "accurate" },
      "uncertain": { text: "⚠️ Uncertain - Verify Manually", class: "uncertain" },
      "hallucination": { text: "🚩 High Hallucination Risk", class: "hallucination" }
    };

    const verdictInfo = verdictMap[verdict] || verdictMap["uncertain"];
    verdictEl.textContent = verdictInfo.text;
    resultDiv.className = verdictInfo.class;

    // Add flag indicator
    if (flag) {
      verdictEl.textContent += " ⚠️";
    }
  }

  function showError(message) {
    resultDiv.style.display = "block";
    resultDiv.className = "hallucination";
    verdictEl.textContent = "❌ Error";
    scoreEl.textContent = "-";
    explanationEl.textContent = message;
    sourcesEl.textContent = "N/A";
  }

  function setLoading(isLoading) {
    verifyBtn.disabled = isLoading;
    verifyBtn.textContent = isLoading ? "Checking..." : "Verify Facts";
    loader.style.display = isLoading ? "block" : "none";
  }
});

// Runs in context of the active web page
function getSelectionText() {
  return window.getSelection()?.toString() || "";
}