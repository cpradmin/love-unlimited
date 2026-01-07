// xAI Sync Extension - Popup Script

// Load saved API key
chrome.storage.sync.get(['apiKey'], (result) => {
  if (result.apiKey) {
    document.getElementById('apiKey').value = result.apiKey;
  }
});

// Save API key on change
document.getElementById('apiKey').addEventListener('input', () => {
  const apiKey = document.getElementById('apiKey').value;
  chrome.storage.sync.set({ apiKey: apiKey });
});

document.getElementById('syncNow').addEventListener('click', () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, { action: 'extract' }, (response) => {
      if (response.error) {
        document.getElementById('status').textContent = 'Extraction failed: ' + response.error;
        return;
      }
      document.getElementById('status').textContent = 'Syncing...';
      // Send to background for sync
      chrome.runtime.sendMessage({ action: 'sync', data: { conversation: response.messages, url: response.url, title: response.title } }, (syncResponse) => {
        const status = syncResponse.status;
        if (status === 'success') {
          document.getElementById('status').textContent = 'Synced!';
        } else if (status === 'busy') {
          document.getElementById('status').textContent = 'Sync in progress...';
        } else {
          document.getElementById('status').textContent = 'Sync failed: ' + (syncResponse.message || status);
        }
      });
    });
  });
});

document.getElementById('syncAll').addEventListener('click', () => {
  document.getElementById('status').textContent = 'Batch sync requires additional development. Please sync each chat manually by opening it and clicking "Sync Current Chat". For full automation, API access to Grok conversations would be needed.';
});