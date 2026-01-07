// background.js - SAFE VERSION
let isSyncing = false;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'sync') {
    if (isSyncing) {
      sendResponse({ status: "busy" });
      return;
    }

    isSyncing = true;
    console.log("Background: Syncing safely...");

    // Get API key from storage
    chrome.storage.sync.get(['apiKey'], async (result) => {
      const apiKey = result.apiKey;
      if (!apiKey) {
        isSyncing = false;
        sendResponse({ status: "error", message: "API Key not set. Please enter your API Key in the extension popup." });
        return;
      }

      // Use a timeout to ensure we don't lock the thread
      setTimeout(async () => {
        try {
          const response = await fetch('http://localhost:9003/sync', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': apiKey
            },
            body: JSON.stringify(request.data)
          });

          isSyncing = false;
          sendResponse({ status: response.ok ? "success" : "failed" });
        } catch (error) {
          isSyncing = false;
          sendResponse({ status: "error", message: error.message });
        }
      }, 10);
    });

    return true; // Important for async sendResponse
  }
});