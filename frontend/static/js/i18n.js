/**
 * FloatChat - Internationalization Module
 * Handles multi-language support for the UI
 */

class I18nManager {
    constructor() {
        this.currentLanguage = 'en';
        this.translations = {};
        this.fallbackLanguage = 'en';
        
        this.init();
    }
    
    /**
     * Initialize i18n system
     */
    init() {
        this.loadTranslations();
        this.setupEventListeners();
        
        console.log('I18n manager initialized');
    }
    
    /**
     * Load translations for all supported languages
     */
    loadTranslations() {
        this.translations = {
            en: {
                // Navigation
                'nav.dashboard': 'Dashboard',
                'nav.chat': 'Chat',
                'nav.explore': 'Explore',
                'nav.data': 'Data',
                'nav.help': 'Help',
                
                // Common actions
                'action.send': 'Send',
                'action.cancel': 'Cancel',
                'action.save': 'Save',
                'action.delete': 'Delete',
                'action.edit': 'Edit',
                'action.view': 'View',
                'action.download': 'Download',
                'action.copy': 'Copy',
                'action.share': 'Share',
                
                // Chat interface
                'chat.title': 'AI Ocean Explorer',
                'chat.placeholder': 'Ask about ocean data, ARGO floats, or marine conditions...',
                'chat.voice_start': 'Start voice input',
                'chat.voice_stop': 'Stop recording',
                'chat.listening': 'Listening...',
                'chat.processing': 'Processing your request...',
                'chat.typing': 'AI is typing...',
                
                // Dashboard
                'dashboard.title': 'Ocean Data Dashboard',
                'dashboard.subtitle': 'Real-time insights from ARGO float network',
                'dashboard.stats.floats': 'Active Floats',
                'dashboard.stats.profiles': 'Total Profiles',
                'dashboard.stats.queries': 'Queries Today',
                'dashboard.stats.languages': 'Languages Supported',
                
                // Data visualization
                'viz.temperature': 'Temperature',
                'viz.salinity': 'Salinity',
                'viz.pressure': 'Pressure',
                'viz.depth': 'Depth',
                'viz.location': 'Location',
                'viz.date': 'Date',
                'viz.loading': 'Loading data...',
                'viz.no_data': 'No data available',
                'viz.error': 'Error loading data',
                
                // Notifications
                'notify.success': 'Success',
                'notify.error': 'Error',
                'notify.warning': 'Warning',
                'notify.info': 'Information',
                'notify.voice_enabled': 'Voice input enabled',
                'notify.voice_disabled': 'Voice input disabled',
                'notify.copied': 'Copied to clipboard',
                'notify.download_complete': 'Download completed',
                
                // Errors
                'error.network': 'Network error. Please check your connection.',
                'error.server': 'Server error. Please try again later.',
                'error.voice_not_supported': 'Voice input not supported in this browser.',
                'error.mic_access_denied': 'Microphone access denied.',
                'error.no_data_found': 'No data found for your query.',
                
                // Quick actions
                'quick.show_temperature': 'Show temperature data',
                'quick.show_salinity': 'Show salinity profiles',
                'quick.find_floats': 'Find nearby floats',
                'quick.recent_data': 'Show recent data',
                'quick.help': 'How can I help you?'
            },
            
            hi: {
                // Navigation
                'nav.dashboard': 'डैशबोर्ड',
                'nav.chat': 'चैट',
                'nav.explore': 'अन्वेषण',
                'nav.data': 'डेटा',
                'nav.help': 'सहायता',
                
                // Common actions
                'action.send': 'भेजें',
                'action.cancel': 'रद्द करें',
                'action.save': 'सहेजें',
                'action.delete': 'हटाएं',
                'action.edit': 'संपादित करें',
                'action.view': 'देखें',
                'action.download': 'डाउनलोड',
                'action.copy': 'कॉपी',
                'action.share': 'साझा करें',
                
                // Chat interface
                'chat.title': 'AI समुद्री अन्वेषक',
                'chat.placeholder': 'समुद्री डेटा, ARGO फ्लोट्स, या समुद्री स्थितियों के बारे में पूछें...',
                'chat.voice_start': 'आवाज इनपुट शुरू करें',
                'chat.voice_stop': 'रिकॉर्डिंग बंद करें',
                'chat.listening': 'सुन रहा है...',
                'chat.processing': 'आपके अनुरोध को संसाधित कर रहा है...',
                'chat.typing': 'AI टाइप कर रहा है...',
                
                // Dashboard
                'dashboard.title': 'समुद्री डेटा डैशबोर्ड',
                'dashboard.subtitle': 'ARGO फ्लोट नेटवर्क से वास्तविक समय की अंतर्दृष्टि',
                'dashboard.stats.floats': 'सक्रिय फ्लोट्स',
                'dashboard.stats.profiles': 'कुल प्रोफाइल',
                'dashboard.stats.queries': 'आज के प्रश्न',
                'dashboard.stats.languages': 'समर्थित भाषाएं',
                
                // Data visualization
                'viz.temperature': 'तापमान',
                'viz.salinity': 'लवणता',
                'viz.pressure': 'दबाव',
                'viz.depth': 'गहराई',
                'viz.location': 'स्थान',
                'viz.date': 'दिनांक',
                'viz.loading': 'डेटा लोड हो रहा है...',
                'viz.no_data': 'कोई डेटा उपलब्ध नहीं',
                'viz.error': 'डेटा लोड करने में त्रुटि',
                
                // Notifications
                'notify.success': 'सफलता',
                'notify.error': 'त्रुटि',
                'notify.warning': 'चेतावनी',
                'notify.info': 'जानकारी',
                'notify.voice_enabled': 'आवाज इनपुट सक्षम',
                'notify.voice_disabled': 'आवाज इनपुट अक्षम',
                'notify.copied': 'क्लिपबोर्ड में कॉपी किया गया',
                'notify.download_complete': 'डाउनलोड पूरा हुआ',
                
                // Errors
                'error.network': 'नेटवर्क त्रुटि। कृपया अपना कनेक्शन जांचें।',
                'error.server': 'सर्वर त्रुटि। कृपया बाद में पुनः प्रयास करें।',
                'error.voice_not_supported': 'इस ब्राउज़र में आवाज इनपुट समर्थित नहीं है।',
                'error.mic_access_denied': 'माइक्रोफोन एक्सेस अस्वीकृत।',
                'error.no_data_found': 'आपके प्रश्न के लिए कोई डेटा नहीं मिला।',
                
                // Quick actions
                'quick.show_temperature': 'तापमान डेटा दिखाएं',
                'quick.show_salinity': 'लवणता प्रोफाइल दिखाएं',
                'quick.find_floats': 'निकटवर्ती फ्लोट्स खोजें',
                'quick.recent_data': 'हाल का डेटा दिखाएं',
                'quick.help': 'मैं आपकी कैसे सहायता कर सकता हूं?'
            },
            
            bn: {
                // Navigation
                'nav.dashboard': 'ড্যাশবোর্ড',
                'nav.chat': 'চ্যাট',
                'nav.explore': 'অন্বেষণ',
                'nav.data': 'ডেটা',
                'nav.help': 'সাহায্য',
                
                // Common actions
                'action.send': 'পাঠান',
                'action.cancel': 'বাতিল',
                'action.save': 'সংরক্ষণ',
                'action.delete': 'মুছুন',
                'action.edit': 'সম্পাদনা',
                'action.view': 'দেখুন',
                'action.download': 'ডাউনলোড',
                'action.copy': 'কপি',
                'action.share': 'শেয়ার',
                
                // Chat interface
                'chat.title': 'AI সমুদ্র অনুসন্ধানকারী',
                'chat.placeholder': 'সমুদ্রের ডেটা, ARGO ফ্লোট, বা সামুদ্রিক অবস্থা সম্পর্কে জিজ্ঞাসা করুন...',
                'chat.voice_start': 'ভয়েস ইনপুট শুরু করুন',
                'chat.voice_stop': 'রেকর্ডিং বন্ধ করুন',
                'chat.listening': 'শুনছে...',
                'chat.processing': 'আপনার অনুরোধ প্রক্রিয়া করছে...',
                'chat.typing': 'AI টাইপ করছে...',
                
                // Dashboard
                'dashboard.title': 'সমুদ্রের ডেটা ড্যাশবোর্ড',
                'dashboard.subtitle': 'ARGO ফ্লোট নেটওয়ার্ক থেকে রিয়েল-টাইম অন্তর্দৃষ্টি',
                'dashboard.stats.floats': 'সক্রিয় ফ্লোট',
                'dashboard.stats.profiles': 'মোট প্রোফাইল',
                'dashboard.stats.queries': 'আজকের প্রশ্ন',
                'dashboard.stats.languages': 'সমর্থিত ভাষা',
                
                // Data visualization  
                'viz.temperature': 'তাপমাত্রা',
                'viz.salinity': 'লবণাক্ততা',
                'viz.pressure': 'চাপ',
                'viz.depth': 'গভীরতা',
                'viz.location': 'অবস্থান',
                'viz.date': 'তারিখ',
                'viz.loading': 'ডেটা লোড হচ্ছে...',
                'viz.no_data': 'কোন ডেটা উপলব্ধ নেই',
                'viz.error': 'ডেটা লোড করতে ত্রুটি',
                
                // Quick actions
                'quick.show_temperature': 'তাপমাত্রার ডেটা দেখান',
                'quick.show_salinity': 'লবণাক্ততার প্রোফাইল দেখান',
                'quick.find_floats': 'কাছাকাছি ফ্লোট খুঁজুন',
                'quick.recent_data': 'সাম্প্রতিক ডেটা দেখান',
                'quick.help': 'আমি কিভাবে আপনাকে সাহায্য করতে পারি?'
            }
        };
    }
    
    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Listen for language change events
        document.addEventListener('click', (event) => {
            if (event.target.matches('[data-lang]')) {
                const language = event.target.dataset.lang;
                this.setLanguage(language);
            }
        });
    }
    
    /**
     * Set the current language
     */
    setLanguage(language) {
        if (!this.translations[language]) {
            console.warn(`Language '${language}' not supported, falling back to '${this.fallbackLanguage}'`);
            language = this.fallbackLanguage;
        }
        
        this.currentLanguage = language;
        this.applyTranslations();
        
        // Dispatch language change event
        document.dispatchEvent(new CustomEvent('languageChanged', {
            detail: { language: this.currentLanguage }
        }));
        
        console.log(`Language set to: ${language}`);
    }
    
    /**
     * Get translation for a key
     */
    t(key, params = {}) {
        const translation = this.translations[this.currentLanguage]?.[key] 
            || this.translations[this.fallbackLanguage]?.[key] 
            || key;
        
        // Replace parameters in translation
        return this.replaceParams(translation, params);
    }
    
    /**
     * Replace parameters in translation string
     */
    replaceParams(text, params) {
        return text.replace(/\{\{(\w+)\}\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }
    
    /**
     * Apply translations to the current page
     */
    applyTranslations() {
        // Translate elements with data-i18n attribute
        const elements = document.querySelectorAll('[data-i18n]');
        
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);
            
            // Apply translation based on element type
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                if (element.type === 'submit' || element.type === 'button') {
                    element.value = translation;
                } else {
                    element.placeholder = translation;
                }
            } else {
                element.textContent = translation;
            }
        });
        
        // Translate elements with data-i18n-title attribute
        const titleElements = document.querySelectorAll('[data-i18n-title]');
        titleElements.forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            element.title = this.t(key);
        });
        
        // Translate elements with data-i18n-placeholder attribute
        const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
        placeholderElements.forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });
        
        // Update document language attribute
        document.documentElement.lang = this.currentLanguage;
        
        // Update page direction for RTL languages
        const rtlLanguages = ['ar', 'he', 'fa', 'ur'];
        document.documentElement.dir = rtlLanguages.includes(this.currentLanguage) ? 'rtl' : 'ltr';
    }
    
    /**
     * Get current language
     */
    getCurrentLanguage() {
        return this.currentLanguage;
    }
    
    /**
     * Get supported languages
     */
    getSupportedLanguages() {
        return Object.keys(this.translations);
    }
    
    /**
     * Check if language is supported
     */
    isLanguageSupported(language) {
        return !!this.translations[language];
    }
    
    /**
     * Get language name in native script
     */
    getLanguageName(language) {
        const names = {
            'en': 'English',
            'hi': 'हिन्दी',
            'bn': 'বাংলা',
            'te': 'తెలుగు',
            'ta': 'தமிழ்',
            'mr': 'मराठी',
            'gu': 'ગુજરાતી',
            'kn': 'ಕನ್ನಡ',
            'ml': 'മലയാളം',
            'or': 'ଓଡ଼ିଆ',
            'pa': 'ਪੰਜਾਬੀ',
            'as': 'অসমীয়া'
        };
        
        return names[language] || language;
    }
    
    /**
     * Format number according to current locale
     */
    formatNumber(number, options = {}) {
        try {
            return new Intl.NumberFormat(this.currentLanguage, options).format(number);
        } catch (error) {
            console.warn('Number formatting failed:', error);
            return number.toString();
        }
    }
    
    /**
     * Format date according to current locale
     */
    formatDate(date, options = {}) {
        try {
            return new Intl.DateTimeFormat(this.currentLanguage, options).format(new Date(date));
        } catch (error) {
            console.warn('Date formatting failed:', error);
            return new Date(date).toLocaleDateString();
        }
    }
    
    /**
     * Format relative time (e.g., "2 hours ago")
     */
    formatRelativeTime(date) {
        try {
            const rtf = new Intl.RelativeTimeFormat(this.currentLanguage, { numeric: 'auto' });
            const now = new Date();
            const diff = new Date(date) - now;
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);
            
            if (Math.abs(days) > 0) return rtf.format(days, 'day');
            if (Math.abs(hours) > 0) return rtf.format(hours, 'hour');
            if (Math.abs(minutes) > 0) return rtf.format(minutes, 'minute');
            return rtf.format(seconds, 'second');
        } catch (error) {
            console.warn('Relative time formatting failed:', error);
            return new Date(date).toLocaleDateString();
        }
    }
    
    /**
     * Add new translations dynamically
     */
    addTranslations(language, translations) {
        if (!this.translations[language]) {
            this.translations[language] = {};
        }
        
        Object.assign(this.translations[language], translations);
        
        // Re-apply translations if this is the current language
        if (language === this.currentLanguage) {
            this.applyTranslations();
        }
    }
    
    /**
     * Load translations from external source
     */
    async loadTranslationsFromAPI(language) {
        try {
            const response = await fetch(`/api/v1/i18n/${language}`);
            if (response.ok) {
                const translations = await response.json();
                this.addTranslations(language, translations);
                return true;
            }
        } catch (error) {
            console.warn(`Failed to load translations for ${language}:`, error);
        }
        return false;
    }
}

// Initialize i18n manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.i18n = new I18nManager();
    
    // Set initial language from localStorage or browser
    const savedLanguage = localStorage.getItem('floatchat-language');
    const browserLanguage = navigator.language.split('-')[0];
    const initialLanguage = savedLanguage || browserLanguage || 'en';
    
    window.i18n.setLanguage(initialLanguage);
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = I18nManager;
}
