import React, { useState, useEffect, useRef } from "react";
import { Send, X, User, Bot } from "lucide-react";

const ChatbotWindow = ({ onClose, clientId, chatbotKey }) => {
  const [messages, setMessages] = useState([
    { 
      sender: "bot", 
      text: "Hello! I'm your AI assistant. How can I help you today?",
      timestamp: "11:17 AM"
    }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  // Generate a unique session_id per visitor
  useEffect(() => {
    if (!sessionId) {
      setSessionId(crypto.randomUUID());
    }
  }, [sessionId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMessage = { 
      sender: "user", 
      text: input.trim(),
      timestamp 
    };
    
    setMessages((prev) => [...prev, newMessage]);
    const userInput = input;
    setInput("");
    setIsTyping(true);

    try {
      const res = await fetch(`http://localhost:8000/client/chat/${clientId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-chatbot-key": chatbotKey,
        },
        body: JSON.stringify({
          session_id: sessionId,
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
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
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
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
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
    <div style={{
      position: 'fixed',
      top: 150,
      left: 1000,
      right: 0,
      bottom: 0,
      backgroundColor: '#f0f2f5',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: 'white',
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #e1e5e9',
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            backgroundColor: '#6366f1',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Bot size={20} color="white" />
          </div>
          <div>
            <h3 style={{
              margin: 0,
              fontSize: '16px',
              fontWeight: '600',
              color: '#1f2937'
            }}>
              AI Assistant
            </h3>
            <p style={{
              margin: 0,
              fontSize: '13px',
              color: '#10b981'
            }}>
              Online now
            </p>
          </div>
        </div>
        
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#f3f4f6'}
            onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Messages Container */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: '8px',
              flexDirection: msg.sender === "user" ? 'row-reverse' : 'row'
            }}
          >
            {/* Avatar */}
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: msg.sender === "user" ? '#e5e7eb' : '#6366f1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {msg.sender === "user" ? (
                <User size={16} color="#6b7280" />
              ) : (
                <Bot size={16} color="white" />
              )}
            </div>

            {/* Message Bubble */}
            <div style={{
              maxWidth: '320px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: msg.sender === "user" ? 'flex-end' : 'flex-start'
            }}>
              <div style={{
                padding: '12px 16px',
                borderRadius: '18px',
                backgroundColor: msg.sender === "user" ? '#10b981' : 'white',
                color: msg.sender === "user" ? 'white' : '#1f2937',
                fontSize: '14px',
                lineHeight: '1.4',
                boxShadow: msg.sender === "bot" ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                border: msg.sender === "bot" ? '1px solid #e5e7eb' : 'none',
                borderBottomLeftRadius: msg.sender === "bot" ? '4px' : '18px',
                borderBottomRightRadius: msg.sender === "user" ? '4px' : '18px'
              }}>
                {msg.text}
              </div>
              <span style={{
                fontSize: '11px',
                color: '#6b7280',
                marginTop: '4px',
                textAlign: msg.sender === "user" ? 'right' : 'left'
              }}>
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: '8px'
          }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: '#6366f1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Bot size={16} color="white" />
            </div>
            <div style={{
              padding: '12px 16px',
              borderRadius: '18px',
              borderBottomLeftRadius: '4px',
              backgroundColor: 'white',
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
              border: '1px solid #e5e7eb',
              display: 'flex',
              gap: '4px'
            }}>
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: '#9ca3af',
                    animation: `bounce 1.4s ease-in-out ${i * 0.16}s infinite both`
                  }}
                ></div>
              ))}
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{
        backgroundColor: 'white',
        padding: '16px 20px',
        borderTop: '1px solid #e5e7eb'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '12px'
        }}>
          <div style={{ flex: 1 }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              style={{
                width: '100%',
                minHeight: '44px',
                maxHeight: '120px',
                padding: '12px 16px',
                border: '1px solid #d1d5db',
                borderRadius: '22px',
                backgroundColor: '#f9fafb',
                color: '#1f2937',
                fontSize: '14px',
                resize: 'none',
                outline: 'none',
                fontFamily: 'inherit',
                boxSizing: 'border-box'
              }}
              onFocus={(e) => e.target.style.borderColor = '#6366f1'}
              onBlur={(e) => e.target.style.borderColor = '#d1d5db'}
              rows="1"
            />
            <p style={{
              fontSize: '12px',
              color: '#6b7280',
              margin: '6px 0 0 0',
              textAlign: 'center'
            }}>
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            style={{
              width: '44px',
              height: '44px',
              backgroundColor: input.trim() && !isTyping ? '#6366f1' : '#e5e7eb',
              border: 'none',
              borderRadius: '50%',
              color: input.trim() && !isTyping ? 'white' : '#9ca3af',
              cursor: input.trim() && !isTyping ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
              opacity: isTyping ? 0.6 : 1
            }}
            onMouseOver={(e) => {
              if (input.trim() && !isTyping) {
                e.target.style.backgroundColor = '#5856f3';
              }
            }}
            onMouseOut={(e) => {
              if (input.trim() && !isTyping) {
                e.target.style.backgroundColor = '#6366f1';
              }
            }}
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* CSS for animations */}
      <style>
        {`
          @keyframes bounce {
            0%, 80%, 100% {
              transform: scale(0);
            }
            40% {
              transform: scale(1);
            }
          }
        `}
      </style>
    </div>
  );
};

export default ChatbotWindow;
