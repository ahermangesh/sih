import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const Chatbot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Hello! I\'m Dolphin, your AI assistant for oceanographic data. How can I help you today?',
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsTyping(true);

    // Simulate bot response
    setTimeout(() => {
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: generateBotResponse(inputText),
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const generateBotResponse = (userInput: string): string => {
    const input = userInput.toLowerCase();
    
    if (input.includes('temperature') || input.includes('temp')) {
      return 'The current sea surface temperature in the Indian Ocean ranges from 26°C to 30°C. Would you like specific data for a particular region?';
    } else if (input.includes('salinity')) {
      return 'Ocean salinity levels in our monitored areas range from 34.8 to 35.8 PSU. This data is collected by our Argo float network.';
    } else if (input.includes('float') || input.includes('argo')) {
      return 'We currently have 10 Argo floats deployed across the Indian Ocean. 7 are active and 3 are inactive. Each float collects temperature, salinity, and depth data.';
    } else if (input.includes('weather') || input.includes('storm')) {
      return 'Current weather conditions are calm with moderate wave heights. No major storms detected in the region. Would you like a detailed forecast?';
    } else if (input.includes('data') || input.includes('information')) {
      return 'I can provide oceanographic data including temperature, salinity, depth measurements, float locations, and weather conditions. What specific data are you looking for?';
    } else {
      return 'I\'m here to help with oceanographic data and analysis. You can ask me about water temperature, salinity levels, Argo float status, weather conditions, or any other ocean-related data.';
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="chatbot-avatar">
          <div className="robot-icon">
            <div className="robot-head">
              <div className="robot-eyes">
                <div className="robot-eye left"></div>
                <div className="robot-eye right"></div>
              </div>
            </div>
            <div className="robot-body"></div>
          </div>
        </div>
        <div className="chatbot-title">
          <h3>Dolphin</h3>
          <span className="status-indicator">● Online</span>
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            {message.sender === 'bot' && (
              <div className="message-avatar">
                <div className="mini-robot-icon">
                  <div className="mini-robot-head">
                    <div className="mini-robot-eyes">
                      <div className="mini-robot-eye"></div>
                      <div className="mini-robot-eye"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className="message-content">
              <div className="message-text">{message.text}</div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="message bot-message typing-message">
            <div className="message-avatar">
              <div className="mini-robot-icon">
                <div className="mini-robot-head">
                  <div className="mini-robot-eyes">
                    <div className="mini-robot-eye"></div>
                    <div className="mini-robot-eye"></div>
                  </div>
                </div>
              </div>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input">
        <div className="input-container">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about ocean data..."
            className="message-input"
            rows={1}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputText.trim()}
            className="send-button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;
