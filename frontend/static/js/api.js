/**
 * FloatChat - API Integration Module
 * Handles all backend API communications and WebSocket connections
 */

class FloatChatAPI {
    constructor() {
        this.baseURL = '/api/v1';
        this.websockets = new Map();
        this.connectionId = this.generateConnectionId();
        
        this.init();
    }
    
    /**
     * Initialize API client
     */
    init() {
        this.setupInterceptors();
        console.log('FloatChat API client initialized');
    }
    
    /**
     * Set up request/response interceptors
     */
    setupInterceptors() {
        // Add correlation ID to requests
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'X-Correlation-ID': this.generateCorrelationId()
        };
    }
    
    /**
     * Generate unique connection ID
     */
    generateConnectionId() {
        return 'conn_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Generate correlation ID for request tracking
     */
    generateCorrelationId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Make HTTP request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                ...this.defaultHeaders,
                ...options.headers
            },
            ...options
        };
        
        // Add language header if available
        if (window.floatChat && window.floatChat.currentLanguage) {
            config.headers['X-Language'] = window.floatChat.currentLanguage;
        }
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    // ============= DASHBOARD API =============
    
    /**
     * Get dashboard statistics
     */
    async getDashboardStats() {
        return await this.request('/dashboard/stats');
    }
    
    /**
     * Get activity feed
     */
    async getActivityFeed(limit = 20) {
        return await this.request(`/dashboard/activity?limit=${limit}`);
    }
    
    /**
     * Get float locations for map
     */
    async getFloatLocations(statusFilter = null, limit = 1000) {
        let url = `/dashboard/floats/locations?limit=${limit}`;
        if (statusFilter) {
            url += `&status_filter=${statusFilter}`;
        }
        return await this.request(url);
    }
    
    // ============= CHAT API =============
    
    /**
     * Send chat query
     */
    async sendChatQuery(message, conversationId, options = {}) {
        const payload = {
            message,
            conversation_id: conversationId,
            language: window.floatChat?.currentLanguage || 'en',
            include_visualization: true,
            voice_input: options.voiceInput || false,
            voice_output: options.voiceOutput || false,
            ...options
        };
        
        return await this.request('/chat/query', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
    
    /**
     * Get conversation history
     */
    async getConversationHistory(conversationId) {
        return await this.request(`/chat/conversations/${conversationId}`);
    }
    
    /**
     * Upload file for chat
     */
    async uploadChatFile(file, description, conversationId) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('description', description);
        formData.append('conversation_id', conversationId);
        
        return await this.request('/chat/upload', {
            method: 'POST',
            headers: {
                'X-Correlation-ID': this.generateCorrelationId()
                // Don't set Content-Type for FormData
            },
            body: formData
        });
    }
    
    // ============= VOICE API =============
    
    /**
     * Transcribe audio to text
     */
    async transcribeAudio(audioBase64, language = 'en', engine = 'google') {
        const payload = {
            audio_base64: audioBase64,
            language,
            engine
        };
        
        return await this.request('/voice/transcribe', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
    
    /**
     * Upload audio file for transcription
     */
    async transcribeAudioFile(file, language = 'en', engine = 'google') {
        const formData = new FormData();
        formData.append('file', file);
        
        return await this.request(`/voice/transcribe-file?language=${language}&engine=${engine}`, {
            method: 'POST',
            headers: {
                'X-Correlation-ID': this.generateCorrelationId()
            },
            body: formData
        });
    }
    
    /**
     * Synthesize text to speech
     */
    async synthesizeText(text, language = 'en', speed = 'normal') {
        const payload = {
            text,
            language,
            speed
        };
        
        return await this.request('/voice/synthesize', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
    
    /**
     * Get supported languages
     */
    async getSupportedLanguages() {
        return await this.request('/voice/languages');
    }
    
    /**
     * Detect language of text
     */
    async detectLanguage(text) {
        return await this.request(`/voice/detect-language?text=${encodeURIComponent(text)}`, {
            method: 'POST'
        });
    }
    
    // ============= FLOATS API =============
    
    /**
     * List ARGO floats
     */
    async listFloats(limit = 100, offset = 0) {
        return await this.request(`/floats/?limit=${limit}&offset=${offset}`);
    }
    
    /**
     * Get float by ID
     */
    async getFloat(floatId) {
        return await this.request(`/floats/${floatId}`);
    }
    
    /**
     * Get float profiles
     */
    async getFloatProfiles(floatId, limit = 100) {
        return await this.request(`/floats/${floatId}/profiles?limit=${limit}`);
    }
    
    /**
     * Search floats by region
     */
    async searchFloats(query) {
        return await this.request('/floats/search', {
            method: 'POST',
            body: JSON.stringify(query)
        });
    }
    
    // ============= WEBSOCKET CONNECTIONS =============
    
    /**
     * Connect to chat WebSocket
     */
    connectChatWebSocket(onMessage, onError = null, onClose = null) {
        const wsUrl = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/v1/ws/chat/${this.connectionId}`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('Chat WebSocket connected');
            this.websockets.set('chat', ws);
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        ws.onerror = (error) => {
            console.error('Chat WebSocket error:', error);
            if (onError) onError(error);
        };
        
        ws.onclose = () => {
            console.log('Chat WebSocket disconnected');
            this.websockets.delete('chat');
            if (onClose) onClose();
        };
        
        return ws;
    }
    
    /**
     * Connect to dashboard WebSocket
     */
    connectDashboardWebSocket(onMessage, onError = null, onClose = null) {
        const wsUrl = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/v1/ws/dashboard/${this.connectionId}`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('Dashboard WebSocket connected');
            this.websockets.set('dashboard', ws);
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        ws.onerror = (error) => {
            console.error('Dashboard WebSocket error:', error);
            if (onError) onError(error);
        };
        
        ws.onclose = () => {
            console.log('Dashboard WebSocket disconnected');
            this.websockets.delete('dashboard');
            if (onClose) onClose();
        };
        
        return ws;
    }
    
    /**
     * Send WebSocket message
     */
    sendWebSocketMessage(type, message) {
        const ws = this.websockets.get(type);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
            return true;
        }
        return false;
    }
    
    /**
     * Join chat conversation via WebSocket
     */
    joinChatConversation(conversationId) {
        return this.sendWebSocketMessage('chat', {
            type: 'join_conversation',
            conversation_id: conversationId
        });
    }
    
    /**
     * Leave chat conversation via WebSocket
     */
    leaveChatConversation(conversationId) {
        return this.sendWebSocketMessage('chat', {
            type: 'leave_conversation',
            conversation_id: conversationId
        });
    }
    
    /**
     * Send typing indicator
     */
    sendTypingIndicator(conversationId, isTyping) {
        return this.sendWebSocketMessage('chat', {
            type: isTyping ? 'typing_start' : 'typing_stop',
            conversation_id: conversationId
        });
    }
    
    /**
     * Send chat message via WebSocket
     */
    sendWebSocketChatMessage(message, conversationId, language = 'en') {
        return this.sendWebSocketMessage('chat', {
            type: 'chat_message',
            message,
            conversation_id: conversationId,
            language
        });
    }
    
    /**
     * Send voice message via WebSocket
     */
    sendWebSocketVoiceMessage(audioData, conversationId, language = 'en') {
        return this.sendWebSocketMessage('chat', {
            type: 'voice_message',
            audio_data: audioData,
            conversation_id: conversationId,
            language
        });
    }
    
    /**
     * Request dashboard stats update via WebSocket
     */
    requestDashboardUpdate() {
        return this.sendWebSocketMessage('dashboard', {
            type: 'request_stats_update'
        });
    }
    
    /**
     * Subscribe to dashboard updates
     */
    subscribeToDashboardUpdates(updateTypes = ['stats', 'activity']) {
        return this.sendWebSocketMessage('dashboard', {
            type: 'subscribe_to_updates',
            update_types: updateTypes
        });
    }
    
    /**
     * Close WebSocket connection
     */
    closeWebSocket(type) {
        const ws = this.websockets.get(type);
        if (ws) {
            ws.close();
            this.websockets.delete(type);
        }
    }
    
    /**
     * Close all WebSocket connections
     */
    closeAllWebSockets() {
        for (const [type, ws] of this.websockets) {
            ws.close();
        }
        this.websockets.clear();
    }
    
    // ============= HEALTH CHECKS =============
    
    /**
     * Check API health
     */
    async checkHealth() {
        return await this.request('/dashboard/health');
    }
    
    /**
     * Check voice service health
     */
    async checkVoiceHealth() {
        return await this.request('/voice/health');
    }
    
    /**
     * Get WebSocket connection stats
     */
    async getWebSocketStats() {
        return await this.request('/ws/connections/stats');
    }
    
    // ============= UTILITY METHODS =============
    
    /**
     * Convert file to base64
     */
    async fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
    
    /**
     * Convert audio blob to base64
     */
    async audioToBase64(audioBlob) {
        return await this.fileToBase64(audioBlob);
    }
    
    /**
     * Check if API is available
     */
    async isAPIAvailable() {
        try {
            await fetch('/health');
            return true;
        } catch {
            return false;
        }
    }
    
    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connectionId: this.connectionId,
            websockets: Array.from(this.websockets.keys()),
            isOnline: navigator.onLine
        };
    }
}

// Initialize API client when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.floatChatAPI = new FloatChatAPI();
    
    // Handle online/offline events
    window.addEventListener('online', () => {
        console.log('Connection restored');
        if (window.floatChat) {
            window.floatChat.showNotification('Connection restored', 'success', 2000);
        }
    });
    
    window.addEventListener('offline', () => {
        console.log('Connection lost');
        if (window.floatChat) {
            window.floatChat.showNotification('Connection lost', 'warning');
        }
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FloatChatAPI;
}
