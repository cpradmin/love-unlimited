// xAI Sync Extension - Content Script
// Runs on https://grok.com/* to extract and sync conversations

console.log("xAI Sync Extension loaded on Grok page");

// content.js - PERFORMANCE VERSION
function extractConversation() {
  // 1. Narrow the search area immediately. Grok uses 'main' or 'article'
  const chatArea = document.querySelector('main') || document.querySelector('article');
  if (!chatArea) return { error: "Chat container not found" };

  // 2. Target only specific text-bearing elements (Markdown blocks/Chat text)
  // Avoid generic 'div' or 'span' as they exist by the thousands.
  const selectors = [
    'div[dir="auto"]',
    '.prose',
    'pre code'
  ];

  const elements = chatArea.querySelectorAll(selectors.join(', '));
  const messages = [];

  // 3. Limit to the last 50 elements to prevent memory overflow
  const startIdx = Math.max(0, elements.length - 50);

  for (let i = startIdx; i < elements.length; i++) {
    const text = elements[i].innerText.trim();
    if (text.length > 5) {
      messages.push(text);
    }
  }

  return {
    messages: [...new Set(messages)],
    url: window.location.href,
    title: document.title
  };
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extract') {
    const result = extractConversation();
    sendResponse(result);
  }
  return true;
});