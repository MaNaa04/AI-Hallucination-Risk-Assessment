document.addEventListener("DOMContentLoaded", () => {
  const textArea = document.getElementById("ai-text");
  const verifyBtn = document.getElementById("verify-btn");
  const loader = document.getElementById("loader");
  const resultDiv = document.getElementById("result");

  const verdictEl = document.getElementById("verdict");
  const scoreEl = document.getElementById("score");
  const explanationEl = document.getElementById("explanation");
  const sourcesEl = document.getElementById("sources");

  // On open, get the highlighted text from the active tab and fill textarea
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.scripting.executeScript(
      {
        target: { tabId: tabs[0].id },
        function: getSelectionText,
      },
      (injectionResults) => {
        if (injectionResults && injectionResults[0].result) {
          textArea.value = injectionResults[0].result;
        } else {
          textArea.placeholder = "Highlight text on any site, or paste the text here...";
        }
      }
    );
  });

  // Verify button click handler
  verifyBtn.addEventListener("click", async () => {
    const textToVerify = textArea.value.trim();

    if (!textToVerify) {
      alert("Please highlight or paste text to verify.");
      return;
    }

    // Toggle Loading UI
    verifyBtn.disabled = true;
    loader.style.display = "block";
    resultDiv.style.display = "none";
    resultDiv.className = ""; // clear classes

    try {
      // NOTE: We're calling the FastAPI backend here! (running on localhost:8000)
      const res = await fetch("http://localhost:8000/api/verify", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: "General Context", // You could grab this if you have context
          answer: textToVerify
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to connect to backend Server");
      }

      const data = await res.json();

      // Assuming verifying matches our verifyResponse schema
      const { score, verdict, explanation, sources_used } = data;

      // Unhide response div
      resultDiv.style.display = "block";
      
      scoreEl.textContent = score;
      explanationEl.textContent = explanation;
      sourcesEl.textContent = (sources_used && sources_used.length > 0) ? sources_used.join(", ") : "None";
      
      // Update UI Based on Verdict
      if (verdict === "accurate") {
        verdictEl.textContent = "✅ Accurate";
        resultDiv.className = "accurate";
      } else if (verdict === "uncertain") {
        verdictEl.textContent = "⚠️ Uncertain";
        resultDiv.className = "uncertain";
      } else {
        verdictEl.textContent = "🚩 Hallucination";
        resultDiv.className = "hallucination";
      }

    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      verifyBtn.disabled = false;
      loader.style.display = "none";
    }
  });
});

// Runs in context of active web page
function getSelectionText() {
  return window.getSelection().toString();
}