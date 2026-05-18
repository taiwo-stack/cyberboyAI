// Set to 'http://localhost:8000' for local development
const BACKEND_URL = 'https://cyberboyai.onrender.com';

chrome.contextMenus.create({
  id: "analyze-link",
  title: "Analyze Threat with CyberBoyAI",
  contexts: ["link", "selection"]
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "analyze-link") {
    const target = info.linkUrl || info.selectionText;
    
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "CyberBoyAI Analysis Started",
      message: "Analyzing: " + target
    });

    fetch(`${BACKEND_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: target, source: 'extension_context' })
    })
    .then(r => r.json())
    .then(data => {
      let title = "🛡️ " + data.verdict + " (" + Math.round((data.verdict === 'SAFE' ? (1-data.score) : data.score)*100) + "%)";
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon48.png",
        title: title,
        message: data.explanation
      });
    })
    .catch(err => {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon48.png",
        title: "Analysis Failed",
        message: "Ensure backend is running."
      });
    });
  }
});
