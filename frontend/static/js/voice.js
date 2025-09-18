/**
 * FloatChat - Voice Processing Module
 * Handles speech recognition and synthesis using Web Speech API
 */

class VoiceManager {
    constructor() {
        this.isRecording = false;
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.currentUtterance = null;
        this.isEnabled = false;
        
        this.init();
    }
    
    /**
     * Initialize voice functionality
     */
    init() {
        this.setupSpeechRecognition();
        this.setupEventListeners();
        this.loadVoiceSettings();
        
        console.log('Voice manager initialized');
    }
    
    /**
     * Set up speech recognition
     */
    setupSpeechRecognition() {
        // Check for browser support
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('Speech recognition not supported in this browser');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;
        this.recognition.lang = this.getCurrentLanguageCode();
        
        // Event handlers
        this.recognition.onstart = () => {
            this.isRecording = true;
            this.updateRecordingUI(true);
            console.log('Speech recognition started');
        };
        
        this.recognition.onend = () => {
            this.isRecording = false;
            this.updateRecordingUI(false);
            console.log('Speech recognition ended');
        };
        
        this.recognition.onresult = (event) => {
            this.handleSpeechResult(event);
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.handleSpeechError(event);
        };
        
        this.recognition.onnomatch = () => {
            console.warn('No speech match found');
            this.showVoiceNotification('No speech detected. Please try again.', 'warning');
        };
    }
    
    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Listen for voice toggle events
        document.addEventListener('voiceToggled', (event) => {
            this.isEnabled = event.detail.enabled;
            this.updateVoiceUI();
        });
        
        // Listen for language changes
        document.addEventListener('languageChanged', (event) => {
            if (this.recognition) {
                this.recognition.lang = this.getCurrentLanguageCode();
            }
        });
        
        // Handle voice button clicks
        document.addEventListener('click', (event) => {
            if (event.target.matches('.voice-btn, .voice-btn *')) {
                event.preventDefault();
                this.toggleRecording();
            }
        });
        
        // Handle voice shortcuts
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + Shift + V to toggle voice
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'V') {
                event.preventDefault();
                this.toggleRecording();
            }
        });
    }
    
    /**
     * Load voice settings from localStorage
     */
    loadVoiceSettings() {
        const settings = JSON.parse(localStorage.getItem('floatchat-voice-settings') || '{}');
        
        this.settings = {
            autoSpeak: settings.autoSpeak || false,
            speechRate: settings.speechRate || 1.0,
            speechPitch: settings.speechPitch || 1.0,
            speechVolume: settings.speechVolume || 1.0,
            preferredVoice: settings.preferredVoice || null,
            ...settings
        };
    }
    
    /**
     * Save voice settings to localStorage
     */
    saveVoiceSettings() {
        localStorage.setItem('floatchat-voice-settings', JSON.stringify(this.settings));
    }
    
    /**
     * Get current language code for speech recognition
     */
    getCurrentLanguageCode() {
        const language = window.floatChat ? window.floatChat.currentLanguage : 'en';
        
        const languageCodes = {
            'en': 'en-US',
            'hi': 'hi-IN',
            'bn': 'bn-IN',
            'te': 'te-IN',
            'ta': 'ta-IN',
            'mr': 'mr-IN',
            'gu': 'gu-IN',
            'kn': 'kn-IN',
            'ml': 'ml-IN',
            'or': 'or-IN',
            'pa': 'pa-IN',
            'as': 'as-IN'
        };
        
        return languageCodes[language] || 'en-US';
    }
    
    /**
     * Toggle voice recording
     */
    toggleRecording() {
        if (!this.isEnabled) {
            this.showVoiceNotification('Voice is disabled. Enable it first.', 'warning');
            return;
        }
        
        if (!this.recognition) {
            this.showVoiceNotification('Speech recognition not supported', 'error');
            return;
        }
        
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }
    
    /**
     * Start voice recording
     */
    startRecording() {
        if (this.isRecording || !this.recognition) return;
        
        try {
            // Update language before starting
            this.recognition.lang = this.getCurrentLanguageCode();
            this.recognition.start();
            
            this.showVoiceVisualization(true);
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showVoiceNotification('Failed to start recording', 'error');
        }
    }
    
    /**
     * Stop voice recording
     */
    stopRecording() {
        if (!this.isRecording || !this.recognition) return;
        
        try {
            this.recognition.stop();
            this.showVoiceVisualization(false);
        } catch (error) {
            console.error('Failed to stop recording:', error);
        }
    }
    
    /**
     * Handle speech recognition results
     */
    handleSpeechResult(event) {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Update interim results in UI
        if (interimTranscript) {
            this.updateInterimTranscript(interimTranscript);
        }
        
        // Handle final result
        if (finalTranscript) {
            this.handleFinalTranscript(finalTranscript);
        }
    }
    
    /**
     * Handle speech recognition errors
     */
    handleSpeechError(event) {
        const errorMessages = {
            'no-speech': 'No speech was detected. Please try again.',
            'audio-capture': 'Audio capture failed. Check your microphone.',
            'not-allowed': 'Microphone access denied. Please allow microphone access.',
            'network': 'Network error occurred during speech recognition.',
            'aborted': 'Speech recognition was aborted.',
            'bad-grammar': 'Speech recognition grammar error.'
        };
        
        const message = errorMessages[event.error] || `Speech recognition error: ${event.error}`;
        this.showVoiceNotification(message, 'error');
        
        this.isRecording = false;
        this.updateRecordingUI(false);
        this.showVoiceVisualization(false);
    }
    
    /**
     * Update interim transcript in UI
     */
    updateInterimTranscript(transcript) {
        // Find active chat input or other text input
        const chatInput = document.querySelector('.chat-input');
        if (chatInput) {
            const currentValue = chatInput.value;
            const cursorPosition = chatInput.selectionStart;
            
            // Show interim transcript as placeholder or in a temporary element
            this.showInterimTranscript(transcript);
        }
    }
    
    /**
     * Handle final transcript
     */
    handleFinalTranscript(transcript) {
        console.log('Final transcript:', transcript);
        
        // Clear interim transcript
        this.clearInterimTranscript();
        
        // Insert transcript into active input
        this.insertTranscriptIntoInput(transcript);
        
        // Dispatch custom event for other components
        document.dispatchEvent(new CustomEvent('voiceTranscript', {
            detail: { transcript, language: this.getCurrentLanguageCode() }
        }));
        
        this.showVoiceNotification('Speech recognized successfully', 'success', 2000);
    }
    
    /**
     * Insert transcript into active input field
     */
    insertTranscriptIntoInput(transcript) {
        const activeElement = document.activeElement;
        
        // Check if active element is a text input
        if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
            const start = activeElement.selectionStart;
            const end = activeElement.selectionEnd;
            const currentValue = activeElement.value;
            
            // Insert transcript at cursor position
            const newValue = currentValue.substring(0, start) + transcript + currentValue.substring(end);
            activeElement.value = newValue;
            
            // Set cursor position after inserted text
            const newCursorPosition = start + transcript.length;
            activeElement.setSelectionRange(newCursorPosition, newCursorPosition);
            
            // Trigger input event
            activeElement.dispatchEvent(new Event('input', { bubbles: true }));
        } else {
            // Find chat input as fallback
            const chatInput = document.querySelector('.chat-input');
            if (chatInput) {
                chatInput.value += (chatInput.value ? ' ' : '') + transcript;
                chatInput.focus();
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    }
    
    /**
     * Speak text using text-to-speech
     */
    speak(text, options = {}) {
        if (!this.synthesis) {
            console.warn('Speech synthesis not supported');
            return Promise.reject(new Error('Speech synthesis not supported'));
        }
        
        // Stop any current speech
        this.stopSpeaking();
        
        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            
            // Configure utterance
            utterance.lang = this.getCurrentLanguageCode();
            utterance.rate = options.rate || this.settings.speechRate;
            utterance.pitch = options.pitch || this.settings.speechPitch;
            utterance.volume = options.volume || this.settings.speechVolume;
            
            // Set voice if preferred voice is available
            if (this.settings.preferredVoice) {
                const voices = this.synthesis.getVoices();
                const preferredVoice = voices.find(voice => voice.name === this.settings.preferredVoice);
                if (preferredVoice) {
                    utterance.voice = preferredVoice;
                }
            }
            
            // Event handlers
            utterance.onstart = () => {
                console.log('Speech synthesis started');
                this.updateSpeakingUI(true);
            };
            
            utterance.onend = () => {
                console.log('Speech synthesis ended');
                this.updateSpeakingUI(false);
                this.currentUtterance = null;
                resolve();
            };
            
            utterance.onerror = (event) => {
                console.error('Speech synthesis error:', event.error);
                this.updateSpeakingUI(false);
                this.currentUtterance = null;
                reject(new Error(`Speech synthesis error: ${event.error}`));
            };
            
            // Start speaking
            this.currentUtterance = utterance;
            this.synthesis.speak(utterance);
        });
    }
    
    /**
     * Stop current speech
     */
    stopSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
        }
        this.currentUtterance = null;
        this.updateSpeakingUI(false);
    }
    
    /**
     * Get available voices
     */
    getAvailableVoices() {
        if (!this.synthesis) return [];
        
        return this.synthesis.getVoices().filter(voice => {
            const currentLang = this.getCurrentLanguageCode();
            return voice.lang.startsWith(currentLang.split('-')[0]);
        });
    }
    
    /**
     * Update recording UI
     */
    updateRecordingUI(isRecording) {
        const voiceButtons = document.querySelectorAll('.voice-btn');
        
        voiceButtons.forEach(button => {
            if (isRecording) {
                button.classList.add('recording');
                button.setAttribute('title', 'Stop recording');
                
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-stop-fill';
                }
            } else {
                button.classList.remove('recording');
                button.setAttribute('title', 'Start voice input');
                
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-mic-fill';
                }
            }
        });
    }
    
    /**
     * Update speaking UI
     */
    updateSpeakingUI(isSpeaking) {
        const speakButtons = document.querySelectorAll('.speak-btn');
        
        speakButtons.forEach(button => {
            if (isSpeaking) {
                button.classList.add('speaking');
                
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-volume-up-fill';
                }
            } else {
                button.classList.remove('speaking');
                
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-volume-up';
                }
            }
        });
    }
    
    /**
     * Update voice UI based on enabled state
     */
    updateVoiceUI() {
        const voiceButtons = document.querySelectorAll('.voice-btn');
        
        voiceButtons.forEach(button => {
            if (this.isEnabled) {
                button.classList.remove('disabled');
                button.removeAttribute('disabled');
            } else {
                button.classList.add('disabled');
                button.setAttribute('disabled', 'true');
            }
        });
    }
    
    /**
     * Show voice visualization
     */
    showVoiceVisualization(show) {
        const visualization = document.querySelector('.voice-visualization');
        
        if (visualization) {
            if (show) {
                visualization.classList.add('active');
            } else {
                visualization.classList.remove('active');
            }
        }
    }
    
    /**
     * Show interim transcript
     */
    showInterimTranscript(transcript) {
        let interimElement = document.querySelector('.interim-transcript');
        
        if (!interimElement) {
            interimElement = document.createElement('div');
            interimElement.className = 'interim-transcript';
            interimElement.style.cssText = `
                position: fixed;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 119, 190, 0.9);
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 0.5rem;
                font-size: 0.875rem;
                z-index: 9999;
                max-width: 80%;
                text-align: center;
            `;
            document.body.appendChild(interimElement);
        }
        
        interimElement.textContent = `Listening: "${transcript}"`;
        interimElement.style.display = 'block';
    }
    
    /**
     * Clear interim transcript
     */
    clearInterimTranscript() {
        const interimElement = document.querySelector('.interim-transcript');
        if (interimElement) {
            interimElement.style.display = 'none';
        }
    }
    
    /**
     * Show voice notification
     */
    showVoiceNotification(message, type = 'info', duration = 3000) {
        if (window.floatChat && window.floatChat.showNotification) {
            window.floatChat.showNotification(message, type, duration);
        } else {
            console.log(`Voice: ${message}`);
        }
    }
    
    /**
     * Check if voice is supported
     */
    isVoiceSupported() {
        return !!(window.SpeechRecognition || window.webkitSpeechRecognition) && !!window.speechSynthesis;
    }
    
    /**
     * Get voice status
     */
    getStatus() {
        return {
            supported: this.isVoiceSupported(),
            enabled: this.isEnabled,
            recording: this.isRecording,
            speaking: this.synthesis && this.synthesis.speaking,
            language: this.getCurrentLanguageCode()
        };
    }
}

// Initialize voice manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.voiceManager = new VoiceManager();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceManager;
}
