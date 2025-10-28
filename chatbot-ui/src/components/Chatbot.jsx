import React, { useState, useEffect, useRef } from "react";
import { MessageCircle } from "lucide-react";
import ChatbotWindow from "./ChatbotWindow";
import { API_URL } from "../config.js";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [clientId, setClientId] = useState("");
  const [chatbotKey, setChatbotKey] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [clientName, setClientName] = useState("");
  const [sessionId, setSessionId] = useState("");

  const heartbeatInterval = useRef(null);

  // Generate or retrieve session ID
  useEffect(() => {
    let storedSessionId = sessionStorage.getItem("chatbot_session_id");
    if (!storedSessionId) {
      storedSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem("chatbot_session_id", storedSessionId);
    }
    setSessionId(storedSessionId);
  }, []);

  // Auto-detect domain and fetch client credentials
  useEffect(() => {
    const fetchClientCredentials = async () => {
      try {
        setIsLoading(true);
        const params = new URLSearchParams(window.location.search);
        // const clientDomain = params.get("domain");
        const currentDomain = window.location.hostname;

        console.log("Detecting domain:", currentDomain);

        const response = await fetch(
          // `${API_URL}/client/lookup-by-domain?domain=${encodeURIComponent(clientDomain)}`,
          `${API_URL}/client/lookup-by-domain?domain=${encodeURIComponent(currentDomain)}`,
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
      } finally {
        setIsLoading(false);
      }
    };

    fetchClientCredentials();
  }, []);

  // Send heartbeat when chatbot is open
  useEffect(() => {
    if (!clientId || !chatbotKey || !sessionId) return;

    const sendHeartbeat = async (isOpen) => {
      try {
        await fetch(`${API_URL}/client/heartbeat/${clientId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Chatbot-Key": chatbotKey,
          },
          body: JSON.stringify({
            session_id: sessionId,
            is_chatbot_open: isOpen,
          }),
        });
      } catch (err) {
        console.error("Heartbeat failed:", err);
      }
    };

    if (isOpen) {
      // Send initial heartbeat
      sendHeartbeat(true);

      // Send heartbeat every 15 seconds while open
      heartbeatInterval.current = setInterval(() => {
        sendHeartbeat(true);
      }, 15000);
    } else {
      // Clear interval and send close signal
      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current);
        heartbeatInterval.current = null;
      }
      sendHeartbeat(false);
    }

    // Cleanup on unmount
    return () => {
      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current);
      }
      sendHeartbeat(false);
    };
  }, [isOpen, clientId, chatbotKey, sessionId]);

  // Handle visibility change (user switches tabs)
  useEffect(() => {
    if (!clientId || !chatbotKey || !sessionId || !isOpen) return;

    const handleVisibilityChange = async () => {
      if (document.hidden) {
        // User switched away - pause heartbeat but don't close
        if (heartbeatInterval.current) {
          clearInterval(heartbeatInterval.current);
        }
      } else {
        // User came back - resume heartbeat
        const sendHeartbeat = async () => {
          try {
            await fetch(`${API_URL}/client/heartbeat/${clientId}`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Chatbot-Key": chatbotKey,
              },
              body: JSON.stringify({
                session_id: sessionId,
                is_chatbot_open: true,
              }),
            });
          } catch (err) {
            console.error("Heartbeat failed:", err);
          }
        };

        sendHeartbeat();
        heartbeatInterval.current = setInterval(sendHeartbeat, 15000);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isOpen, clientId, chatbotKey, sessionId]);

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

  // Error state
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

        <button
          onMouseEnter={() => {
            const tooltip = document.getElementById("error-tooltip");
            if (tooltip) tooltip.style.display = "block";
          }}
          onMouseLeave={() => {
            const tooltip = document.getElementById("error-tooltip");
            if (tooltip) tooltip.style.display = "none";
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

  return (
    <div
      style={{ position: "fixed", bottom: "20px", right: "20px", zIndex: 1000 }}
    >
      {isOpen && (
        <ChatbotWindow
          clientId={clientId}
          chatbotKey={chatbotKey}
          sessionId={sessionId}
          onClose={() => setIsOpen(false)}
        />
      )}

      {!isOpen && (
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
            e.currentTarget.style.backgroundColor = "#5856f3";
            e.currentTarget.style.transform = "scale(1.05)";
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = "#6366f1";
            e.currentTarget.style.transform = "scale(1)";
          }}
          title={`Chat with ${clientName || "Support"}`}
        >
          <MessageCircle size={24} />
        </button>
      )}
    </div>
  );
};

export default Chatbot;
