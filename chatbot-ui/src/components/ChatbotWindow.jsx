import React, { useState, useEffect, useRef } from "react";
import { Send, X, User, Bot, UserCheck, RefreshCw, Plus } from "lucide-react";

const API_URL = "http://localhost:8000"; // Update with your API URL

const ChatbotWindow = ({ onClose, clientId, chatbotKey, sessionId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showSessionPrompt, setShowSessionPrompt] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [followUpSuggestions, setFollowUpSuggestions] = useState([]);
  const [lastMessageId, setLastMessageId] = useState(null);
  const messagesEndRef = useRef(null);
  const pollingRef = useRef(null);

  // 🔥 FIX: Use session ID passed from parent (already created in Chatbot.jsx)
  useEffect(() => {
    console.log("📍 ChatbotWindow mounted with:", {
      clientId,
      sessionId,
      hasSessionId: !!sessionId
    });

    if (sessionId) {
      // Use the session ID from parent component
      setCurrentSessionId(sessionId);
      setShowSessionPrompt(false);
      
      // Load existing chat history
      console.log("📚 Loading chat history for session:", sessionId);
      loadHistory(sessionId);
    } else {
      console.warn("⚠️ No session ID provided to ChatbotWindow");
      setShowSessionPrompt(true);
    }
  }, [clientId, sessionId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, followUpSuggestions]);

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

        const formattedMessages = activeMessages.map((chat) => ({
          id: chat.id,
          sender: chat.role === "user" ? "user" : "bot",
          text: chat.message,
          timestamp: new Date(chat.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          admin_override: chat.admin_override === 1,
        }));

        setMessages(formattedMessages);
        
        // Track last message ID for efficient polling
        if (formattedMessages.length > 0) {
          setLastMessageId(formattedMessages[formattedMessages.length - 1].id);
        }
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  const handleNewSession = () => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setFollowUpSuggestions([]);
    setShowSessionPrompt(false);
    setLastMessageId(null);

    const storageKey = `chatbot_session_${clientId}`;
    const sessionData = {
      sessionId: newSessionId,
      timestamp: Date.now(),
    };
    localStorage.setItem(storageKey, JSON.stringify(sessionData));
  };

  // 🔥 IMPROVED POLLING - Detects admin messages and deletions
  useEffect(() => {
    if (showSessionPrompt || !currentSessionId) return;

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

          const formattedMessages = activeMessages.map((chat) => ({
            id: chat.id,
            sender: chat.role === "user" ? "user" : "bot",
            text: chat.message,
            timestamp: new Date(chat.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
            admin_override: chat.admin_override === 1,
          }));

          // 🔥 KEY FIX: Always update if message count or last ID changed
          const hasNewMessages = 
            formattedMessages.length !== messages.length ||
            (formattedMessages.length > 0 && 
             formattedMessages[formattedMessages.length - 1].id !== lastMessageId);

          if (hasNewMessages) {
            console.log("📩 New messages detected, updating...");
            setMessages(formattedMessages);
            
            if (formattedMessages.length > 0) {
              setLastMessageId(formattedMessages[formattedMessages.length - 1].id);
            }

            // Clear typing indicator if we received a new bot message
            const lastMsg = formattedMessages[formattedMessages.length - 1];
            if (lastMsg && lastMsg.sender === "bot") {
              setIsTyping(false);
            }
          }
        }
      } catch (err) {
        console.error("Failed to poll messages:", err);
      }
    };

    // Poll immediately on mount
    pollMessages();

    // Then poll every 2 seconds
    pollingRef.current = setInterval(pollMessages, 2000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [
    currentSessionId,
    chatbotKey,
    clientId,
    showSessionPrompt,
    messages.length,
    lastMessageId,
  ]);

  const handleSend = async (messageText = null) => {
    const textToSend = messageText || input.trim();
    if (!textToSend) return;

    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    const newMessage = {
      id: Date.now(), // Temporary ID
      sender: "user",
      text: textToSend,
      timestamp,
      admin_override: false,
    };

    setMessages((prev) => [...prev, newMessage]);
    setInput("");
    setIsTyping(true);
    setFollowUpSuggestions([]);

    try {
      const res = await fetch(`${API_URL}/client/chat/${clientId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Chatbot-Key": chatbotKey,
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          message: textToSend,
        }),
      });

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status}`);
      }

      const data = await res.json();

      // Update session_id if backend provides a new one
      if (data.session_id && data.session_id !== currentSessionId) {
        setCurrentSessionId(data.session_id);
        const storageKey = `chatbot_session_${clientId}`;
        const sessionData = {
          sessionId: data.session_id,
          timestamp: Date.now(),
        };
        localStorage.setItem(storageKey, JSON.stringify(sessionData));
      }

      // The polling will handle adding the bot response
      // But we can add it immediately for better UX
      setTimeout(() => {
        const botMessage = {
          id: Date.now() + 1,
          sender: "bot",
          text: data.reply,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          admin_override: false,
        };

        setMessages((prev) => [...prev, botMessage]);

        // Extract suggestions
        const suggestions = [];
        if (data.follow_up_question) {
          suggestions.push({
            type: "follow_up",
            text: data.follow_up_question,
          });
        }
        if (data.clarification_questions?.length > 0) {
          data.clarification_questions.forEach((q) => {
            suggestions.push({ type: "clarification", text: q });
          });
        }
        if (data.probing_questions?.length > 0) {
          data.probing_questions.slice(0, 2).forEach((q) => {
            suggestions.push({ type: "probing", text: q });
          });
        }

        setFollowUpSuggestions(suggestions);
        setIsTyping(false);
      }, 500);
    } catch (err) {
      console.error("Chat error:", err);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
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

  const handleSuggestionClick = (suggestionText) => {
    let processedText = suggestionText;

    if (suggestionText.toLowerCase().startsWith("would you like")) {
      processedText = suggestionText.replace(
        /would you like (to know about|to know|me to|about)/gi,
        "",
      );
      processedText = processedText.replace(/\?$/g, "").trim();
      processedText = `yes, ${processedText}`;
    } else if (suggestionText.toLowerCase().startsWith("do you need")) {
      processedText = suggestionText
        .replace(/do you need/gi, "")
        .replace(/\?$/g, "")
        .trim();
      processedText = `yes, ${processedText}`;
    } else if (suggestionText.endsWith("?")) {
      processedText = "yes";
    }

    handleSend(processedText);
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
            Welcome!
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
            Start a new conversation with our AI assistant
          </p>

          <button
            onClick={handleNewSession}
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
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "#4f46e5";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "#6366f1";
            }}
          >
            <Plus size={16} />
            Start Conversation
          </button>
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
        {messages.length === 0 && !showSessionPrompt && (
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
            key={`${msg.id}-${idx}`}
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
                flexShrink: 0,
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

        {/* Follow-up Suggestions */}
        {followUpSuggestions.length > 0 && !isTyping && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              marginTop: "8px",
              marginLeft: "36px",
            }}
          >
            {followUpSuggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(suggestion.text)}
                style={{
                  padding: "8px 12px",
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "12px",
                  fontSize: "13px",
                  color: "#6366f1",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.2s",
                  boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#f9fafb";
                  e.currentTarget.style.borderColor = "#6366f1";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "white";
                  e.currentTarget.style.borderColor = "#e5e7eb";
                }}
              >
                💬 {suggestion.text}
              </button>
            ))}
          </div>
        )}

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
            onClick={() => handleSend()}
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