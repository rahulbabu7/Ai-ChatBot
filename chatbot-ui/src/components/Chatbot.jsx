import React, { useState } from "react";
import { MessageCircle } from "lucide-react";
import ChatbotWindow from "./ChatbotWindow";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [clientId, setClientId] = useState("kochidigital_d0aef1");
  const [chatbotKey, setChatbotKey] = useState("535e999373d547139f7ad4e6969738c3");

  // Client options
  // const clientOptions = [
  //   { 
  //     id: "kochidigital_d0aef1", 
  //     name: "Kochi Digital",
  //     key: "535e999373d547139f7ad4e6969738c3"
  //   },
  //   { 
  //     id: "sjcet", 
  //     name: "SJCET",
  //     key: "your_sjcet_key_here"
  //   },
  //   { 
  //     id: "client2", 
  //     name: "Client 2",
  //     key: "your_client2_key_here"
  //   }
  // ];

  // Update chatbot key when client changes
  // const handleClientChange = (newClientId) => {
  //   const selectedClient = clientOptions.find(client => client.id === newClientId);
  //   if (selectedClient) {
  //     setClientId(newClientId);
  //     setChatbotKey(selectedClient.key);
  //   }
  // };

  const handleToggleChat = () => {
    setIsOpen(!isOpen);
  };

  const handleCloseChat = () => {
    setIsOpen(false);
  };

  return (
    <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 1000 }}>
      {/* Client Selector */}
      {/* <div style={{
        marginBottom: '10px',
        backgroundColor: 'white',
        padding: '10px',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        display: isOpen ? 'none' : 'block'
      }}>
        <label style={{
          fontSize: '12px',
          fontWeight: '500',
          color: '#6b7280',
          marginBottom: '5px',
          display: 'block'
        }}>
          Choose Client:
        </label>
        <select
          value={clientId}
          onChange={(e) => handleClientChange(e.target.value)}
          style={{
            width: '200px',
            padding: '6px 8px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '13px',
            backgroundColor: 'white',
            color: '#374151'
          }}
        >
          {clientOptions.map((client) => (
            <option key={client.id} value={client.id}>
              {client.name}
            </option>
          ))}
        </select>
      </div>*/}

      {/* Chat Window */}
      {isOpen && (
        <ChatbotWindow
          clientId={clientId}
          chatbotKey={chatbotKey}
          onClose={handleCloseChat}
        />
      )}

      {/* Floating Chat Button */}
      <button
        onClick={handleToggleChat}
        style={{
          width: '56px',
          height: '56px',
          backgroundColor: '#6366f1',
          border: 'none',
          borderRadius: '50%',
          color: 'white',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
          transition: 'all 0.2s ease',
          fontSize: 0 // Hide text, show only icon
        }}
        onMouseOver={(e) => {
          e.target.style.backgroundColor = '#5856f3';
          e.target.style.transform = 'scale(1.05)';
        }}
        onMouseOut={(e) => {
          e.target.style.backgroundColor = '#6366f1';
          e.target.style.transform = 'scale(1)';
        }}
      >
        <MessageCircle size={24} />
      </button>
    </div>
  );
};

export default Chatbot;