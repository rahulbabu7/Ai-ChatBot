import React, { useState, useEffect, useRef } from "react";
import { Send, X, User, Bot, UserCheck, RefreshCw, Plus } from "lucide-react";

import { API_URL } from "../config";

const ChatbotWindow = ({ onClose, clientId, chatbotKey, sessionId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showSessionPrompt, setShowSessionPrompt] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [hasExistingSession, setHasExistingSession] = useState(false);
  const messagesEndRef = useRef(null);

  // Check for existing session on mount
  useEffect(() => {
    const storageKey = `chatbot_session_${clientId}`;
    const savedData = localStorage.getItem(storageKey);

    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        const sessionAge = Date.now() - parsed.timestamp;
        const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

        // Clear session if older than 7 days
        if (sessionAge > SEVEN_DAYS) {
          localStorage.removeItem(storageKey);
          setHasExistingSession(false);
        } else {
          setCurrentSessionId(parsed.sessionId);
          setHasExistingSession(true);
        }
      } catch (e) {
        // Handle old format (plain string)
        setCurrentSessionId(savedData);
        setHasExistingSession(true);
      }
    } else if (sessionId) {
      const sessionData = {
        sessionId: sessionId,
        timestamp: Date.now(),
      };
      setCurrentSessionId(sessionId);
      setHasExistingSession(true);
      localStorage.setItem(storageKey, JSON.stringify(sessionData));
    }
  }, [clientId, sessionId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Load chat history
  const loadHistory = async (sessId) => {
    try {
      const response = await fetch(
        `${API_URL}/client/chat-history/${clientId}/${sessId}`,
        {
          headers: {
            "Content-Type": "application/json",
            "X-Chatbot-Key": chatbotKey,
          },
        },
      );

      if (response.ok) {
        const data = await response.json();
        const activeMessages = (data.chats || []).filter(
          (chat) => chat.is_active !== 0,
        );

        setMessages(
          activeMessages.map((chat) => ({
            sender: chat.role === "user" ? "user" : "bot",
            text: chat.message,
            timestamp: new Date(chat.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
            admin_override: chat.admin_override === 1,
          })),
        );
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  // Handle session selection
  // const handleLoadSession = () => {
  //   setShowSessionPrompt(false);
  //   if (currentSessionId) {
  //     loadHistory(currentSessionId);
  //     // Update timestamp when session is accessed
  //     const storageKey = `chatbot_session_${clientId}`;
  //     const sessionData = {
  //       sessionId: currentSessionId,
  //       timestamp: Date.now(),
  //     };
  //     localStorage.setItem(storageKey, JSON.stringify(sessionData));
  //   }
  // };

  const handleNewSession = () => {
    // Generate a new session ID
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setShowSessionPrompt(false);

    // Save new session to localStorage with timestamp
    const storageKey = `chatbot_session_${clientId}`;
    const sessionData = {
      sessionId: newSessionId,
      timestamp: Date.now(),
    };
    localStorage.setItem(storageKey, JSON.stringify(sessionData));
    setHasExistingSession(true);
  };

  // Poll for new messages every 3 seconds (to catch admin replies)
  useEffect(() => {
    if (showSessionPrompt) return; // Don't poll if session prompt is showing

    const pollMessages = async () => {
      try {
        const response = await fetch(
          `${API_URL}/client/chat-history/${clientId}/${currentSessionId}`,
          {
            headers: {
              "Content-Type": "application/json",
              "X-Chatbot-Key": chatbotKey,
            },
          },
        );

        if (response.ok) {
          const data = await response.json();
          const activeMessages = (data.chats || []).filter(
            (chat) => chat.is_active !== 0,
          );

          // Only update if message count changed
          if (activeMessages.length !== messages.length) {
            setMessages(
              activeMessages.map((chat) => ({
                sender: chat.role === "user" ? "user" : "bot",
                text: chat.message,
                timestamp: new Date(chat.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
                admin_override: chat.admin_override === 1,
              })),
            );
          }
        }
      } catch (err) {
        console.error("Failed to poll messages:", err);
      }
    };

    if (clientId && chatbotKey && currentSessionId) {
      const interval = setInterval(pollMessages, 3000);
      return () => clearInterval(interval);
    }
  }, [
    currentSessionId,
    chatbotKey,
    clientId,
    messages.length,
    showSessionPrompt,
  ]);

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
      const res = await fetch(`${API_URL}/client/chat/${clientId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Chatbot-Key": chatbotKey,
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: userInput,
        }),
      });

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
            admin_override: false,
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
            admin_override: false,
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

      {/* Session Prompt Overlay */}
      {showSessionPrompt && (
        <div
          style={{
            position: "absolute",
            top: "60px",
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(255, 255, 255, 0.98)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "32px",
            zIndex: 10,
          }}
        >
          <div
            style={{
              width: "80px",
              height: "80px",
              backgroundColor: "#f0f2f5",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "24px",
            }}
          >
            <Bot size={40} color="#6366f1" />
          </div>

          <h3
            style={{
              fontSize: "18px",
              fontWeight: "600",
              color: "#1f2937",
              margin: "0 0 8px 0",
              textAlign: "center",
            }}
          >
            Welcome back!
          </h3>

          <p
            style={{
              fontSize: "14px",
              color: "#6b7280",
              margin: "0 0 32px 0",
              textAlign: "center",
              lineHeight: "1.5",
            }}
          >
            Would you like to continue your previous conversation or start
            fresh?
          </p>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              width: "100%",
            }}
          >
            {/* {hasExistingSession && (
              <button
                onClick={handleLoadSession}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "10px",
                  padding: "14px 24px",
                  backgroundColor: "#6366f1",
                  color: "white",
                  border: "none",
                  borderRadius: "10px",
                  fontSize: "14px",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "background-color 0.2s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.backgroundColor = "#4f46e5")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.backgroundColor = "#6366f1")
                }
              >
                <RefreshCw size={16} />
                Continue Previous Session
              </button>
            )}*/}

            <button
              onClick={handleNewSession}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "10px",
                padding: "14px 24px",
                backgroundColor: "white",
                color: "#6366f1",
                border: "2px solid #6366f1",
                borderRadius: "10px",
                fontSize: "14px",
                fontWeight: "600",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#f0f2f5";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "white";
              }}
            >
              <Plus size={16} />
              Start New Conversation
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          opacity: showSessionPrompt ? 0.3 : 1,
          pointerEvents: showSessionPrompt ? "none" : "auto",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: "#6b7280",
              marginTop: "40px",
              fontSize: "14px",
            }}
          >
            <p>👋 Hello! How can we help you today?</p>
          </div>
        )}

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
                  msg.sender === "user"
                    ? "#e5e7eb"
                    : msg.admin_override
                      ? "#10b981"
                      : "#6366f1",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {msg.sender === "user" ? (
                <User size={14} color="#6b7280" />
              ) : msg.admin_override ? (
                <UserCheck size={14} color="white" />
              ) : (
                <Bot size={14} color="white" />
              )}
            </div>

            <div
              style={{
                maxWidth: "250px",
                display: "flex",
                flexDirection: "column",
                alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
              }}
            >
              {msg.admin_override && (
                <div
                  style={{
                    fontSize: "10px",
                    fontWeight: "600",
                    color: "#10b981",
                    marginBottom: "4px",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <UserCheck size={10} />
                  Support Team
                </div>
              )}
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "16px",
                  backgroundColor:
                    msg.sender === "user"
                      ? "#6366f1"
                      : msg.admin_override
                        ? "#10b981"
                        : "white",
                  color:
                    msg.sender === "user" || msg.admin_override
                      ? "white"
                      : "#1f2937",
                  fontSize: "14px",
                  lineHeight: "1.4",
                  boxShadow:
                    msg.sender === "bot" && !msg.admin_override
                      ? "0 1px 2px rgba(0,0,0,0.1)"
                      : "none",
                  border:
                    msg.sender === "bot" && !msg.admin_override
                      ? "1px solid #e5e7eb"
                      : msg.admin_override
                        ? "2px solid #059669"
                        : "none",
                  whiteSpace: "pre-wrap",
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
          opacity: showSessionPrompt ? 0.3 : 1,
          pointerEvents: showSessionPrompt ? "none" : "auto",
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
              cursor: input.trim() && !isTyping ? "pointer" : "not-allowed",
            }}
          >
            <Send size={14} />
            <span style={{ fontSize: "12px", fontWeight: 500 }}>Send</span>
          </button>
        </div>
        <p
          style={{
            fontSize: "12px",
            color: "#6b7280",
            margin: "6px 0 0 0",
            textAlign: "center",
          }}
        >
          Press Enter to send, Shift+Enter for new line
        </p>
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
