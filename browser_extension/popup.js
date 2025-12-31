// Love-Unlimited Browser Share Extension
// Popup script

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'shareTab') {
        shareToHub({
            type: 'tab_share',
            url: request.url,
            title: request.title,
            content: `Jon shared tab: ${request.title} - ${request.url}`
        }).then(() => {
            // Could show notification, but since popup may not be open, maybe not
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const status = document.getElementById('status');

    // Load settings
    chrome.storage.sync.get(['apiKey', 'being'], (result) => {
        document.getElementById('apiKey').value = result.apiKey || '';
        document.getElementById('being').value = result.being || 'jon';
    });

    // Show/hide settings
    document.getElementById('showSettings').addEventListener('click', () => {
        document.getElementById('settings').style.display = 'block';
        document.getElementById('showSettings').style.display = 'none';
    });

    document.getElementById('hideSettings').addEventListener('click', () => {
        document.getElementById('settings').style.display = 'none';
        document.getElementById('showSettings').style.display = 'block';
    });

    // Save settings
    document.getElementById('saveSettings').addEventListener('click', () => {
        const apiKey = document.getElementById('apiKey').value.trim();
        const being = document.getElementById('being').value;
        chrome.storage.sync.set({ apiKey, being }, () => {
            status.textContent = 'Settings saved!';
            setTimeout(() => status.textContent = 'Ready to share...', 2000);
        });
    });

    // Share current tab URL
    document.getElementById('shareTab').addEventListener('click', async () => {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            const url = tab.url;
            const title = tab.title;

            status.textContent = 'Sharing tab...';
            const result = await shareToHub({
                type: 'tab_share',
                url: url,
                title: title,
                content: `Jon shared tab: ${title} - ${url}`
            });

            status.textContent = 'Tab shared successfully!';
        } catch (error) {
            status.textContent = 'Error: ' + error.message;
        }
    });

    // Share screen
    document.getElementById('shareScreen').addEventListener('click', async () => {
        try {
            status.textContent = 'Starting screen share...';
            const stream = await startScreenShare();
            await shareStream(stream, 'screen');
            status.textContent = 'Screen sharing active!';
        } catch (error) {
            status.textContent = 'Error: ' + error.message;
        }
    });

    // Share camera/mic
    document.getElementById('shareCam').addEventListener('click', async () => {
        try {
            status.textContent = 'Starting camera share...';
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            await shareStream(stream, 'camera');
            status.textContent = 'Camera/mic sharing active!';
        } catch (error) {
            status.textContent = 'Error: ' + error.message;
        }
    });

    // Open media room
    document.getElementById('openMedia').addEventListener('click', async () => {
        const url = 'http://localhost:9003/media';
        await chrome.tabs.create({ url: url });
        status.textContent = 'Opened media room';
    });

    // Execute command
    document.getElementById('execute').addEventListener('click', async () => {
        const command = document.getElementById('command').value.trim();
        if (!command) {
            status.textContent = 'Please enter a command';
            return;
        }
        try {
            status.textContent = 'Executing...';
            const result = await executeCommand(command);
            if (result.status === 'confirmation_required') {
                status.textContent = result.message;
            } else {
                status.textContent = `Executed (code: ${result.returncode})`;
                console.log('STDOUT:', result.stdout);
                console.log('STDERR:', result.stderr);
            }
        } catch (error) {
            status.textContent = 'Error: ' + error.message;
        }
    });
});

// Share data to Love-Unlimited hub
async function shareToHub(data) {
    // Get API key from storage
    const { apiKey, being } = await chrome.storage.sync.get(['apiKey', 'being']);
    if (!apiKey) {
        throw new Error('Please set your API key in extension settings');
    }

    const response = await fetch('http://localhost:9003/remember', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
        },
        body: JSON.stringify({
            content: data.content,
            type: 'experience',
            significance: 'medium',
            tags: ['browser_share', data.type],
            private: false
        })
    });

    if (!response.ok) {
        throw new Error('Failed to share to hub');
    }

    return await response.json();
}

// Start screen sharing
async function startScreenShare() {
    return new Promise((resolve, reject) => {
        chrome.desktopCapture.chooseDesktopMedia(['screen', 'window'], (streamId) => {
            if (streamId) {
                navigator.mediaDevices.getUserMedia({
                    audio: false,
                    video: {
                        mandatory: {
                            chromeMediaSource: 'desktop',
                            chromeMediaSourceId: streamId
                        }
                    }
                }).then(resolve).catch(reject);
            } else {
                reject(new Error('Screen sharing cancelled'));
            }
        });
    });
}

// Share media stream via WebRTC
async function shareStream(stream, type) {
    const { apiKey } = await chrome.storage.sync.get(['apiKey']);
    if (!apiKey) {
        throw new Error('Please set your API key in extension settings');
    }

    const pc = new RTCPeerConnection();

    // Add tracks to peer connection
    stream.getTracks().forEach(track => pc.addTrack(track, stream));

    // Create offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    // Send offer to hub
    const response = await fetch('http://localhost:9003/webrtc/offer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
        },
        body: JSON.stringify({
            sdp: offer.sdp,
            type: offer.type
        })
    });

    if (!response.ok) {
        throw new Error('Failed to start WebRTC');
    }

    const answer = await response.json();

    // Set remote answer
    await pc.setRemoteDescription(new RTCSessionDescription({
        sdp: answer.sdp,
        type: answer.type
    }));

    // Remember the stream and PC for cleanup
    window.currentStream = stream;
    window.currentPC = pc;
}

// Execute command on laptop
async function executeCommand(command) {
    const { apiKey } = await chrome.storage.sync.get(['apiKey']);
    if (!apiKey) {
        throw new Error('Please set your API key in extension settings');
    }

    const response = await fetch('http://localhost:9003/execute', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
        },
        body: JSON.stringify({
            command: command
        })
    });

    if (!response.ok) {
        throw new Error('Failed to execute command');
    }

    return await response.json();
}