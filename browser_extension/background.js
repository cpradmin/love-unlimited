// Love-Unlimited Browser Share Extension
// Background service worker

// Listen for extension installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('Love-Unlimited Browser Share installed');

    // Set default settings if not exist
    chrome.storage.sync.get(['apiKey', 'being'], (result) => {
        if (!result.apiKey) {
            // Prompt user to set API key
            chrome.tabs.create({ url: 'chrome://extensions/?id=' + chrome.runtime.id });
        }
    });
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getSettings') {
        chrome.storage.sync.get(['apiKey', 'being'], (result) => {
            sendResponse(result);
        });
        return true; // Will respond asynchronously
    }
});