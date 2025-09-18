import React from 'react';
import './Sidebar.css';
import Chatbot from '../Chatbot/Chatbot';

const Sidebar: React.FC = () => {
  return (
    <div className="sidebar">
      <Chatbot />
    </div>
  );
};

export default Sidebar;
