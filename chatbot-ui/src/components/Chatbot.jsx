import React, { useState, useEffect } from "react";
import { MessageCircle } from "lucide-react";
import ChatbotWindow from "./ChatbotWindow";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [clientId, setClientId] = useState("");
  const [chatbotKey, setChatbotKey] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [clientName, setClientName] = useState("");

  // Auto-detect domain and fetch client credentials
  useEffect(() => {
    const fetchClientCredentials = async () => {
      try {
        setIsLoading(true);

        // Get current domain
        const params = new URLSearchParams(window.location.search);
        const clientDomain = params.get("domain");
        // const currentDomain = window.location.hostname;
        // console.log("Detecting domain:", currentDomain);
        console.log("Detecting domain:", clientDomain);
        // Call backend to lookup client by domain
        const response = await fetch(
          `http://localhost:8000/client/lookup-by-domain?domain=${encodeURIComponent(clientDomain)}`,
        );

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(
              "This domain is not registered. Please contact support to register your domain.",
            );
          }
          throw new Error(`Failed to lookup domain: ${response.status}`);
        }

        const data = await response.json();

        setClientId(data.client_id);
        setChatbotKey(data.chatbot_key);
        setClientName(data.client_name);
        setError("");

        console.log("✅ Chatbot configured for:", data.client_name);
      } catch (err) {
        console.error("Failed to configure chatbot:", err);
        setError(err.message);

        // Optional: Fallback to manual configuration for development
        // if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        //   console.log("🔧 Development mode: Using fallback credentials");
        //   setClientId("kochidigital_d0aef1");
        //   setChatbotKey("535e999373d547139f7ad4e6969738c3");
        //   setClientName("Development Client");
        //   setError("");
        // }
      } finally {
        setIsLoading(false);
      }
    };

    fetchClientCredentials();
  }, []);

  const handleToggleChat = () => {
    if (!clientId || !chatbotKey) {
      alert(
        "Chatbot is not available for this domain. Please contact support.",
      );
      return;
    }
    setIsOpen(!isOpen);
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        style={{
          position: "fixed",
          bottom: "20px",
          right: "20px",
          zIndex: 1000,
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            backgroundColor: "#e5e7eb",
            border: "none",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: "pulse 2s infinite",
          }}
        >
          <MessageCircle size={24} color="#9ca3af" />
        </div>
        <style>
          {`
            @keyframes pulse {
              0%, 100% { opacity: 1; }
              50% { opacity: 0.5; }
            }
          `}
        </style>
      </div>
    );
  }

  // Error state (domain not registered)
  if (error && !clientId) {
    return (
      <div
        style={{
          position: "fixed",
          bottom: "20px",
          right: "20px",
          zIndex: 1000,
        }}
      >
        {/* Error message tooltip */}
        <div
          style={{
            backgroundColor: "white",
            padding: "12px 16px",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            marginBottom: "12px",
            maxWidth: "280px",
            fontSize: "13px",
            color: "#dc2626",
            border: "1px solid #fecaca",
            display: "none",
          }}
          id="error-tooltip"
        >
          ⚠️ {error}
        </div>

        {/* Disabled chat button */}
        <button
          onMouseEnter={() => {
            document.getElementById("error-tooltip").style.display = "block";
          }}
          onMouseLeave={() => {
            document.getElementById("error-tooltip").style.display = "none";
          }}
          style={{
            width: "56px",
            height: "56px",
            backgroundColor: "#dc2626",
            border: "none",
            borderRadius: "50%",
            color: "white",
            cursor: "not-allowed",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 12px rgba(220, 38, 38, 0.4)",
            opacity: 0.7,
          }}
          title="Chatbot not available"
        >
          <MessageCircle size={24} />
        </button>
      </div>
    );
  }

  // Active chatbot
  return (
    <div
      style={{ position: "fixed", bottom: "20px", right: "20px", zIndex: 1000 }}
    >
      {/* Client name badge (optional) */}
      {clientName && !isOpen && (
        <div
          style={{
            backgroundColor: "white",
            padding: "6px 12px",
            borderRadius: "20px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            marginBottom: "8px",
            fontSize: "12px",
            color: "#6b7280",
            textAlign: "center",
            border: "1px solid #e5e7eb",
          }}
        >
          💬 {clientName} Support
        </div>
      )}

      {/* Chat Window */}
      {isOpen && (
        <ChatbotWindow
          clientId={clientId}
          chatbotKey={chatbotKey}
          onClose={() => setIsOpen(false)}
        />
      )}

      {/* Chat Button */}
      <button
        onClick={handleToggleChat}
        style={{
          width: "56px",
          height: "56px",
          backgroundColor: "#6366f1",
          border: "none",
          borderRadius: "50%",
          color: "white",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 12px rgba(99, 102, 241, 0.4)",
          transition: "all 0.2s ease",
        }}
        onMouseOver={(e) => {
          e.target.style.backgroundColor = "#5856f3";
          e.target.style.transform = "scale(1.05)";
        }}
        onMouseOut={(e) => {
          e.target.style.backgroundColor = "#6366f1";
          e.target.style.transform = "scale(1)";
        }}
        title={`Chat with ${clientName || "Support"}`}
      >
        <MessageCircle size={24} />
      </button>
    </div>
  );
};

export default Chatbot;
