// Love-Unlimited Browser Share Extension
// Content script injected into web pages

// Optional: Add a floating button to share current page
function addShareButton() {
    const button = document.createElement('div');
    button.innerHTML = '💙 Share with Love-Unlimited';
    button.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #007bff;
        color: white;
        padding: 8px 12px;
        border-radius: 5px;
        cursor: pointer;
        z-index: 10000;
        font-size: 12px;
    `;

    button.addEventListener('click', () => {
        chrome.runtime.sendMessage({
            action: 'shareTab',
            url: window.location.href,
            title: document.title
        });
    });

    document.body.appendChild(button);
}

// Add button only if settings allow
chrome.storage.sync.get(['showShareButton'], (result) => {
    if (result.showShareButton !== false) { // Default true
        addShareButton();
    }
});