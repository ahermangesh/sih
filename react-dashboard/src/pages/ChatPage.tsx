import React from 'react';
import Chatbot from '../components/Chatbot/Chatbot';
import './ChatPage.css';

const ChatPage: React.FC = () => {
  return (
    <div className="chat-page">
      <div className="chat-page-container">
        <Chatbot />
      </div>
    </div>
  );
};

export default ChatPage;
