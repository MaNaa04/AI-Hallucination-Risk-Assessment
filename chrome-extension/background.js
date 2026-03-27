/**
 * AI Hallucination Detector - Background Service Worker
 * Handles context menu and background verification
 */

const API_URL = "http://localhost:8000/api/verify";

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "verifyClaimMenu",
    title: "🔍 Check for Hallucination",
    contexts: ["selection"]
  });

  console.log("[AI Hallucination Detector] Extension installed");
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "verifyClaimMenu" && info.selectionText) {
    const selectedText = info.selectionText.trim();

    if (selectedText.length < 10) {
      console.log("Text too short to verify");
      return;
    }

    console.log("[AI Hallucination Detector] Verifying:", selectedText.substring(0, 50) + "...");

    try {
      const result = await verifyText(selectedText);

      // Send result to content script to display overlay
      chrome.tabs.sendMessage(tab.id, {
        action: "SHOW_RESULT",
        result: result
      });

    } catch (error) {
      console.error("[AI Hallucination Detector] Verification error:", error);

      // Send error to content script
      chrome.tabs.sendMessage(tab.id, {
        action: "SHOW_RESULT",
        result: {
          score: 0,
          verdict: "error",
          explanation: "Could not connect to verification server. Make sure the backend is running.",
          sources_used: []
        }
      });
    }
  }
});

/**
 * Call the verification API
 */
async function verifyText(text) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question: "Is this statement factually accurate?",
      answer: text
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return await response.json();
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "VERIFY_TEXT") {
    verifyText(message.text)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));

    return true; // Keep message channel open for async response
  }
});
