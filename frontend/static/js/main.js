/**
 * FloatChat - Main JavaScript Module
 * Core functionality for the FloatChat application
 */

class FloatChatApp {
    constructor() {
        this.apiBaseUrl = '/api/v1';
        this.currentLanguage = 'en';
        this.theme = 'light';
        this.voiceEnabled = false;
        
        this.init();
    }
    
    /**
     * Initialize the application
     */
    init() {
        this.setupEventListeners();
        this.setupTheme();
        this.setupLanguage();
        this.setupNotifications();
        this.checkAPIHealth();
        
        console.log('FloatChat application initialized');
    }
    
    /**
     * Set up global event listeners
     */
    setupEventListeners() {
        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        // Language selector
        const languageItems = document.querySelectorAll('[data-lang]');
        languageItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.setLanguage(item.dataset.lang);
            });
        });
        
        // Voice toggle
        const voiceToggle = document.getElementById('voice-toggle');
        if (voiceToggle) {
            voiceToggle.addEventListener('click', () => this.toggleVoice());
        }
        
        // Global error handling
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            this.showNotification('An unexpected error occurred', 'error');
        });
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.showNotification('A network error occurred', 'error');
        });
    }
    
    /**
     * Set up theme functionality
     */
    setupTheme() {
        // Get saved theme or default to light
        const savedTheme = localStorage.getItem('floatchat-theme') || 'light';
        this.setTheme(savedTheme);
    }
    
    /**
     * Toggle between light and dark themes
     */
    toggleTheme() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }
    
    /**
     * Set the application theme
     */
    setTheme(theme) {
        this.theme = theme;
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('floatchat-theme', theme);
        
        // Update theme toggle icon
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            if (icon) {
                icon.className = theme === 'light' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
            }
        }
        
        console.log(`Theme set to: ${theme}`);
    }
    
    /**
     * Set up language functionality
     */
    setupLanguage() {
        const savedLanguage = localStorage.getItem('floatchat-language') || 'en';
        this.setLanguage(savedLanguage);
    }
    
    /**
     * Set the application language
     */
    setLanguage(language) {
        this.currentLanguage = language;
        localStorage.setItem('floatchat-language', language);
        
        // Update current language display
        const currentLangElement = document.getElementById('current-language');
        if (currentLangElement) {
            const languageNames = {
                'en': 'English',
                'hi': 'हिन्दी',
                'bn': 'বাংলা',
                'te': 'తెలుగు',
                'ta': 'தமிழ்'
            };
            currentLangElement.textContent = languageNames[language] || 'English';
        }
        
        // Apply translations if i18n is available
        if (window.i18n && window.i18n.setLanguage) {
            window.i18n.setLanguage(language);
        }
        
        console.log(`Language set to: ${language}`);
    }
    
    /**
     * Toggle voice functionality
     */
    toggleVoice() {
        this.voiceEnabled = !this.voiceEnabled;
        
        const voiceToggle = document.getElementById('voice-toggle');
        if (voiceToggle) {
            const icon = voiceToggle.querySelector('i');
            if (icon) {
                icon.className = this.voiceEnabled ? 'bi bi-mic-fill' : 'bi bi-mic-mute';
            }
            voiceToggle.title = this.voiceEnabled ? 'Disable voice' : 'Enable voice';
        }
        
        // Notify other components about voice state change
        document.dispatchEvent(new CustomEvent('voiceToggled', {
            detail: { enabled: this.voiceEnabled }
        }));
        
        console.log(`Voice ${this.voiceEnabled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Set up notification system
     */
    setupNotifications() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
    }
    
    /**
     * Show a notification
     */
    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `toast align-items-center text-bg-${type} border-0 show`;
        notification.setAttribute('role', 'alert');
        
        notification.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${this.getNotificationIcon(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
    
    /**
     * Get icon for notification type
     */
    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle-fill',
            'error': 'exclamation-triangle-fill',
            'warning': 'exclamation-triangle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }
    
    /**
     * Check API health
     */
    async checkAPIHealth() {
        try {
            const response = await this.makeRequest('/health');
            if (response.status === 'healthy') {
                console.log('API is healthy');
            } else {
                this.showNotification('API health check failed', 'warning');
            }
        } catch (error) {
            console.warn('API health check failed:', error);
            this.showNotification('Unable to connect to server', 'error');
        }
    }
    
    /**
     * Make an API request
     */
    async makeRequest(endpoint, options = {}) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Language': this.currentLanguage
            }
        };
        
        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };
        
        try {
            const response = await fetch(url, mergedOptions);
            
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
    
    /**
     * Show loading overlay
     */
    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            const messageElement = overlay.querySelector('p');
            if (messageElement) {
                messageElement.textContent = message;
            }
            overlay.classList.remove('d-none');
        }
    }
    
    /**
     * Hide loading overlay
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('d-none');
        }
    }
    
    /**
     * Format date for display
     */
    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        return new Intl.DateTimeFormat(this.currentLanguage, mergedOptions).format(new Date(date));
    }
    
    /**
     * Format number for display
     */
    formatNumber(number, options = {}) {
        return new Intl.NumberFormat(this.currentLanguage, options).format(number);
    }
    
    /**
     * Debounce function calls
     */
    debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }
    
    /**
     * Throttle function calls
     */
    throttle(func, delay) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, delay);
            }
        };
    }
    
    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Copied to clipboard', 'success', 2000);
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            this.showNotification('Failed to copy to clipboard', 'error');
        }
    }
    
    /**
     * Download data as file
     */
    downloadFile(data, filename, type = 'application/json') {
        const blob = new Blob([data], { type });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        this.showNotification(`Downloaded ${filename}`, 'success', 2000);
    }
    
    /**
     * Get user's geolocation
     */
    async getUserLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                position => resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }),
                error => reject(error),
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000 // 5 minutes
                }
            );
        });
    }
    
    /**
     * Check if device is mobile
     */
    isMobile() {
        return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    /**
     * Check if device supports touch
     */
    isTouch() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    }
}

// Utility functions
const utils = {
    /**
     * Generate UUID
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },
    
    /**
     * Sanitize HTML
     */
    sanitizeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
    
    /**
     * Parse URL parameters
     */
    getUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        for (const [key, value] of params) {
            result[key] = value;
        }
        return result;
    },
    
    /**
     * Validate email
     */
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },
    
    /**
     * Format file size
     */
    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.floatChat = new FloatChatApp();
    window.utils = utils;
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FloatChatApp, utils };
}
