// Voice Trigger Module for SafeRoute
// Handles speech recognition and automatic emergency alerts

class VoiceTrigger {
    constructor() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = SpeechRecognition ? new SpeechRecognition() : null;
        this.isListening = false;
        this.distressWord = localStorage.getItem('distressWord') || 'help';
        this.sensitivity = parseFloat(localStorage.getItem('voiceSensitivity') || 0.7);
        this.voiceEnabled = localStorage.getItem('voiceEnabled') === 'true';
        
        if (this.recognition) {
            this.setupRecognition();
        }
    }

    setupRecognition() {
        // Language: English (can be changed)
        this.recognition.language = 'en-US';
        
        // Continuous recognition
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        
        // When speech is recognized
        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i].transcript;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            if (finalTranscript) {
                this.checkForDistressWord(finalTranscript);
            }
        };

        // Handle errors
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            // Restart listening if there's an error
            if (this.voiceEnabled) {
                setTimeout(() => this.start(), 2000);
            }
        };

        // When recognition ends
        this.recognition.onend = () => {
            this.isListening = false;
            // Restart if voice trigger is still enabled
            if (this.voiceEnabled) {
                setTimeout(() => this.start(), 1000);
            }
        };
    }

    checkForDistressWord(transcript) {
        console.log('Heard:', transcript);
        
        // Normalize: lowercase, trim
        const heard = transcript.toLowerCase().trim();
        const distress = this.distressWord.toLowerCase().trim();
        
        // Check with confidence based on sensitivity
        // Sensitivity affects how strict the match is
        const matchConfidence = this.calculateSimilarity(heard, distress);
        
        if (matchConfidence >= this.sensitivity) {
            console.log(`🚨 DISTRESS WORD DETECTED! Confidence: ${matchConfidence}`);
            this.triggerEmergency();
        }
    }

    // Similarity calculation (Levenshtein distance)
    calculateSimilarity(str1, str2) {
        const longer = str1.length > str2.length ? str1 : str2;
        const shorter = str1.length > str2.length ? str2 : str1;
        
        if (longer.length === 0) return 1.0;
        
        const editDistance = this.getEditDistance(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    }

    getEditDistance(s1, s2) {
        const costs = [];
        for (let i = 0; i <= s1.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= s2.length; j++) {
                if (i === 0) {
                    costs[j] = j;
                } else if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    }
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
            if (i > 0) costs[s2.length] = lastValue;
        }
        return costs[s2.length];
    }

    async triggerEmergency() {
        console.log('🚨 EMERGENCY TRIGGERED BY VOICE');
        
        // Stop listening to prevent multiple triggers
        this.stop();
        
        // Get current location
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;
                    
                    try {
                        // Send emergency alert to backend
                        const response = await fetch('/emergency', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                latitude: latitude,
                                longitude: longitude,
                                trigger_type: 'voice'
                            })
                        });

                        const data = await response.json();
                        
                        if (data.success) {
                            console.log('✅ Emergency alert sent!');
                            this.showEmergencyNotification(data.contacts_notified);
                            
                            // Vibrate phone if supported
                            if (navigator.vibrate) {
                                navigator.vibrate([200, 100, 200, 100, 200]);
                            }
                        } else {
                            console.error('Failed to send alert:', data.message);
                        }
                    } catch (error) {
                        console.error('Error sending emergency alert:', error);
                    }
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    // Send alert anyway without location
                    this.sendEmergencyWithoutLocation();
                }
            );
        } else {
            this.sendEmergencyWithoutLocation();
        }

        // Restart listening after a short delay
        setTimeout(() => this.start(), 3000);
    }

    async sendEmergencyWithoutLocation() {
        try {
            const response = await fetch('/emergency', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude: 0,
                    longitude: 0,
                    trigger_type: 'voice'
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showEmergencyNotification(data.contacts_notified);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    showEmergencyNotification(contactsCount) {
        // Create notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            z-index: 9999;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease-out;
        `;
        notification.textContent = `🚨 EMERGENCY ALERT SENT to ${contactsCount} contacts!`;
        document.body.appendChild(notification);

        // Remove after 5 seconds
        setTimeout(() => notification.remove(), 5000);
    }

    start() {
        if (this.recognition && !this.isListening) {
            try {
                this.recognition.start();
                this.isListening = true;
                console.log('🎤 Voice listener started');
            } catch (error) {
                console.log('Voice recognition already started');
            }
        }
    }

    stop() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
            console.log('🎤 Voice listener stopped');
        }
    }

    setDistressWord(word) {
        this.distressWord = word.toLowerCase().trim();
        localStorage.setItem('distressWord', this.distressWord);
    }

    setSensitivity(value) {
        this.sensitivity = parseFloat(value);
        localStorage.setItem('voiceSensitivity', this.sensitivity);
    }

    enable() {
        this.voiceEnabled = true;
        localStorage.setItem('voiceEnabled', 'true');
        this.start();
    }

    disable() {
        this.voiceEnabled = false;
        localStorage.setItem('voiceEnabled', 'false');
        this.stop();
    }
}

// Global instance
let voiceTrigger = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        voiceTrigger = new VoiceTrigger();
        
        // Auto-start if previously enabled
        if (voiceTrigger.voiceEnabled) {
            voiceTrigger.enable();
        }
    }
});

// ==================== SETTINGS PAGE FUNCTIONS ====================

function loadVoiceSettings() {
    const distressWord = localStorage.getItem('distressWord') || 'help';
    const sensitivity = localStorage.getItem('voiceSensitivity') || 0.7;
    const enabled = localStorage.getItem('voiceEnabled') === 'true';

    document.getElementById('distressWord').value = distressWord;
    document.getElementById('sensitivity').value = sensitivity;
    document.getElementById('sensitivityValue').textContent = sensitivity;
    document.getElementById('voiceTriggerToggle').checked = enabled;

    // Show settings if enabled
    if (enabled) {
        document.getElementById('settingsSection').style.display = 'block';
    }
}

function saveVoiceSettings() {
    const distressWord = document.getElementById('distressWord').value.trim();
    const sensitivity = document.getElementById('sensitivity').value;
    const enabled = document.getElementById('voiceTriggerToggle').checked;

    if (!distressWord) {
        showStatus('Please enter a distress word', 'error');
        return;
    }

    // Save to localStorage
    localStorage.setItem('distressWord', distressWord);
    localStorage.setItem('voiceSensitivity', sensitivity);
    localStorage.setItem('voiceEnabled', enabled.toString());

    // Update global instance
    if (voiceTrigger) {
        voiceTrigger.setDistressWord(distressWord);
        voiceTrigger.setSensitivity(sensitivity);
        
        if (enabled) {
            voiceTrigger.enable();
        } else {
            voiceTrigger.disable();
        }
    }

    showStatus('✅ Voice settings saved successfully!', 'success');
}

function resetSettings() {
    localStorage.removeItem('distressWord');
    localStorage.removeItem('voiceSensitivity');
    localStorage.removeItem('voiceEnabled');
    
    document.getElementById('distressWord').value = 'help';
    document.getElementById('sensitivity').value = 0.7;
    document.getElementById('sensitivityValue').textContent = 0.7;
    document.getElementById('voiceTriggerToggle').checked = false;
    
    if (voiceTrigger) {
        voiceTrigger.disable();
    }
    
    document.getElementById('settingsSection').style.display = 'none';
    showStatus('Settings reset to default', 'info');
}

function startVoiceListener() {
    if (voiceTrigger) {
        voiceTrigger.enable();
    }
}

function stopVoiceListener() {
    if (voiceTrigger) {
        voiceTrigger.disable();
    }
}

function testVoiceRecognition() {
    const testBtn = document.getElementById('testBtn');
    const listeningIndicator = document.getElementById('listeningIndicator');
    const testStatus = document.getElementById('testStatus');
    const distressWord = document.getElementById('distressWord').value.toLowerCase().trim();

    if (!distressWord) {
        testStatus.className = 'status error';
        testStatus.textContent = 'Please enter a distress word first';
        return;
    }

    testBtn.disabled = true;
    listeningIndicator.classList.add('active');
    testStatus.className = 'status';

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const testRecognition = new SpeechRecognition();
    testRecognition.language = 'en-US';
    testRecognition.continuous = false;
    testRecognition.interimResults = true;

    let heardText = '';

    testRecognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                heardText = event.results[i].transcript.toLowerCase().trim();
            }
        }
    };

    testRecognition.onend = () => {
        listeningIndicator.classList.remove('active');
        testBtn.disabled = false;

        if (heardText) {
            // Check if distress word was heard
            const matches = distressWord.includes(heardText) || heardText.includes(distressWord);
            
            if (matches) {
                testStatus.className = 'status success';
                testStatus.textContent = `✅ Success! Heard "${heardText}" - matched your distress word`;
            } else {
                testStatus.className = 'status warning';
                testStatus.textContent = `⚠️ Heard "${heardText}" - doesn't match "${distressWord}". Try again.`;
            }
        } else {
            testStatus.className = 'status error';
            testStatus.textContent = 'No speech detected. Please try again.';
        }
    };

    testRecognition.onerror = (event) => {
        listeningIndicator.classList.remove('active');
        testBtn.disabled = false;
        testStatus.className = 'status error';
        testStatus.textContent = `Error: ${event.error}`;
    };

    try {
        testRecognition.start();
    } catch (error) {
        testBtn.disabled = false;
        listeningIndicator.classList.remove('active');
    }
}

function showStatus(message, type) {
    const statusEl = document.getElementById('mainStatus');
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
}