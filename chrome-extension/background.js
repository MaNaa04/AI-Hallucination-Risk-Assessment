chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "verifyClaimMenu",
    title: "Verify AI Claim: '%s'",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "verifyClaimMenu" && info.selectionText) {
    // Send message to open popup or handle it
    console.log("Selected text: ", info.selectionText);

    // Communicate with the popup or handle directly
    chrome.runtime.sendMessage({
      action: "VERIFY_TEXT",
      text: info.selectionText
    });
  }
});
