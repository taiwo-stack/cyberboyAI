// Set to 'http://localhost:8000' for local development
const BACKEND_URL = 'http://98.94.189.162';

chrome.contextMenus.create({
  id: "analyze-with-gaudon",
  title: "Analyze with GaudOn",
  contexts: ["link", "selection"]
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "analyze-with-gaudon") {
    const target = info.linkUrl || info.selectionText || "";
    if (!target) return;

    // 1. Store the pending scan payload so the popup can pick it up on open.
    //    We store the raw text/URL, the tab URL (for context), and a timestamp
    //    so the popup can detect a fresh request vs. stale storage.
    chrome.storage.local.set({
      gaudOn_pending: {
        input:     target,
        tabUrl:    tab ? tab.url : "",
        source:    "context_menu",
        timestamp: Date.now()
      }
    });

    // 2. Open the popup so the user sees the results in the full GaudOn UI.
    //    chrome.action.openPopup() requires a user gesture — a context menu
    //    click qualifies. Falls back to a new window if the API is unavailable.
    if (chrome.action && chrome.action.openPopup) {
      chrome.action.openPopup().catch(() => {
        // Fallback: open popup.html as a standalone small window
        chrome.windows.create({
          url: chrome.runtime.getURL("popup.html"),
          type: "popup",
          width: 420,
          height: 680
        });
      });
    } else {
      chrome.windows.create({
        url: chrome.runtime.getURL("popup.html"),
        type: "popup",
        width: 420,
        height: 680
      });
    }
  }
});
