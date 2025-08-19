import React, { useState } from "react";
import { FaComments } from "react-icons/fa";
import ChatbotWindow from "./ChatbotWindow";
import "./Chatbot.css";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="chatbot-container">
      {isOpen && <ChatbotWindow onClose={() => setIsOpen(false)} />}
      <button className="chatbot-button" onClick={() => setIsOpen(!isOpen)}>
        <FaComments size={24} />
      </button>
    </div>
  );
};

export default Chatbot;
