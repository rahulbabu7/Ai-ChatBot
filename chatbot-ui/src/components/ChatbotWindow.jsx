import React, { useState, useEffect, useRef } from "react";
import { Send, X, User, Bot } from "lucide-react";

const ChatbotWindow = ({ onClose, clientId, chatbotKey }) => {
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Hello! I'm your AI assistant. How can I help you today?",
      timestamp: "11:17 AM",
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  // Generate a unique session_id
  useEffect(() => {
    if (!sessionId) {
      setSessionId(crypto.randomUUID());
    }
  }, [sessionId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    const newMessage = {
      sender: "user",
      text: input.trim(),
      timestamp,
    };

    setMessages((prev) => [...prev, newMessage]);
    const userInput = input;
    setInput("");
    setIsTyping(true);

    try {
      const res = await fetch(
        `http://localhost:8000/client/chat/${clientId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-chatbot-key": chatbotKey,
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: userInput,
          }),
        }
      );

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status}`);
      }

      const data = await res.json();

      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: data.reply,
            timestamp: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          },
        ]);
        setIsTyping(false);
      }, 500);
    } catch (err) {
      console.error("Chat error:", err);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: "⚠️ Error contacting backend.",
            timestamp: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          },
        ]);
        setIsTyping(false);
      }, 500);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: "80px",
        right: "20px",
        width: "350px",
        height: "500px",
        backgroundColor: "#f0f2f5",
        display: "flex",
        flexDirection: "column",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        borderRadius: "12px",
        overflow: "hidden",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        zIndex: 2000,
      }}
    >
      {/* Header */}
      <div
        style={{
          backgroundColor: "white",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #e1e5e9",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              backgroundColor: "#6366f1",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Bot size={18} color="white" />
          </div>
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: "15px",
                fontWeight: "600",
                color: "#1f2937",
              }}
            >
              AI Assistant
            </h3>
            <p
              style={{
                margin: 0,
                fontSize: "12px",
                color: "#10b981",
              }}
            >
              Online now
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#6b7280",
            cursor: "pointer",
            padding: "6px",
            borderRadius: "6px",
          }}
        >
          <X size={18} />
        </button>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: "8px",
              flexDirection: msg.sender === "user" ? "row-reverse" : "row",
            }}
          >
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                backgroundColor:
                  msg.sender === "user" ? "#e5e7eb" : "#6366f1",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {msg.sender === "user" ? (
                <User size={14} color="#6b7280" />
              ) : (
                <Bot size={14} color="white" />
              )}
            </div>

            <div
              style={{
                maxWidth: "250px",
                display: "flex",
                flexDirection: "column",
                alignItems:
                  msg.sender === "user" ? "flex-end" : "flex-start",
              }}
            >
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "16px",
                  backgroundColor:
                    msg.sender === "user" ? "#10b981" : "white",
                  color: msg.sender === "user" ? "white" : "#1f2937",
                  fontSize: "14px",
                  lineHeight: "1.4",
                  boxShadow:
                    msg.sender === "bot"
                      ? "0 1px 2px rgba(0,0,0,0.1)"
                      : "none",
                  border:
                    msg.sender === "bot"
                      ? "1px solid #e5e7eb"
                      : "none",
                }}
              >
                {msg.text}
              </div>
              <span
                style={{
                  fontSize: "10px",
                  color: "#6b7280",
                  marginTop: "4px",
                }}
              >
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {isTyping && (
          <div style={{ display: "flex", gap: "8px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                backgroundColor: "#6366f1",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Bot size={14} color="white" />
            </div>
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "16px",
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                display: "flex",
                gap: "4px",
              }}
            >
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    backgroundColor: "#9ca3af",
                    animation: `bounce 1.4s ease-in-out ${i * 0.16}s infinite both`,
                  }}
                ></div>
              ))}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div
        style={{
          backgroundColor: "white",
          padding: "12px",
          borderTop: "1px solid #e5e7eb",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            style={{
              flex: 1,
              minHeight: "20px",
              maxHeight: "100px",
              padding: "10px 14px",
              border: "1px solid #d1d5db",
              borderRadius: "20px",
              backgroundColor: "#f9fafb",
              fontSize: "14px",
              resize: "none",
              outline: "none",
              fontFamily: "inherit",
            }}
            rows="1"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "0 14px",
              height: "40px",
              backgroundColor:
                input.trim() && !isTyping ? "#6366f1" : "#e5e7eb",
              border: "none",
              borderRadius: "20px",
              color: input.trim() && !isTyping ? "white" : "#9ca3af",
              cursor:
                input.trim() && !isTyping ? "pointer" : "not-allowed",
            }}
          >
            <Send size={14} />
            <span style={{ fontSize: "12px", fontWeight: 500 }}>Send</span>
          </button>
        </div>
        <p style={{ 
          fontSize: '12px', 
          color: '#6b7280', 
          margin: '6px 0 0 0', 
          textAlign: 'center' 
          }}> 
          Press Enter to send, Shift+Enter for new line </p>
      </div>

      <style>
        {`
          @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
          }
        `}
      </style>
    </div>
  );
};

export default ChatbotWindow;
