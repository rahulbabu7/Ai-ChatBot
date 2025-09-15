import React, { useState } from "react";
import { FaComments } from "react-icons/fa";
import ChatbotWindow from "./ChatbotWindow";
import "./Chatbot.css";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [clientId, setClientId] = useState("kochidigital_d0aef1"); // default client
  const [chatbotKey, setChatbotKey] = useState("535e999373d547139f7ad4e6969738c3"); // 🔑 replace with real key from signup/login

  return (
    <div className="chatbot-container">
      {/* Dropdown to select client */}
      <div className="client-selector">
        <label htmlFor="client">Choose Client: </label>
        <select
          id="client"
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
        >
          <option value={chatbotKey}>Kochi Digital</option>
          <option value="sjcet">SJCET</option>
          <option value="client2">Client 2</option>
        </select>
      </div>

      {/* Chat window */}
      {isOpen && (
        <ChatbotWindow
          clientId={clientId}
          chatbotKey={chatbotKey}   // ✅ pass chatbot key
          onClose={() => setIsOpen(false)}
        />
      )}

      {/* Floating button */}
      <button className="chatbot-button" onClick={() => setIsOpen(!isOpen)}>
        <FaComments size={24} />
      </button>
    </div>
  );
};

export default Chatbot;
