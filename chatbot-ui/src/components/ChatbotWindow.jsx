// import React, { useState, useEffect, useRef } from "react";
// import ReactMarkdown from 'react-markdown';
// import remarkGfm from 'remark-gfm';
// import { Send, X, User, Bot, UserCheck, Plus } from "lucide-react";
// import { API_URL } from "../config.js";
//
// const ChatbotWindow = ({ onClose, clientId, chatbotKey, sessionId }) => {
//   const [messages, setMessages] = useState([]);
//   const [input, setInput] = useState("");
//   const [isTyping, setIsTyping] = useState(false);
//   const [showSessionPrompt, setShowSessionPrompt] = useState(true);
//   const [currentSessionId, setCurrentSessionId] = useState(null);
//   const [isAdminTyping, setIsAdminTyping] = useState(false);
//   const [wsConnected, setWsConnected] = useState(false);
//
//   const messagesEndRef = useRef(null);
//   const wsRef = useRef(null);
//   const reconnectTimeoutRef = useRef(null);
//   const typingTimeoutRef = useRef(null);
//
//   // WebSocket URL
//   const WS_URL = API_URL.replace('http', 'ws').replace('https', 'wss');
//
//   useEffect(() => {
//     console.log("📍 ChatbotWindow mounted with:", {
//       clientId,
//       sessionId,
//       hasSessionId: !!sessionId
//     });
//
//     if (sessionId) {
//       setCurrentSessionId(sessionId);
//       setShowSessionPrompt(false);
//       console.log("📚 Loading chat history for session:", sessionId);
//       loadHistory(sessionId);
//       connectWebSocket(sessionId);
//     } else {
//       console.warn("⚠️ No session ID provided to ChatbotWindow");
//       setShowSessionPrompt(true);
//     }
//
//     return () => {
//       disconnectWebSocket();
//     };
//   }, [clientId, sessionId]);
//
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
//   }, [messages, isTyping, isAdminTyping]);
//
//   // Connect to WebSocket
//   const connectWebSocket = (sessId) => {
//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       console.log("✅ WebSocket already connected");
//       return;
//     }
//
//     try {
//       const wsUrl = `${WS_URL}/ws/client/${sessId}?chatbot_key=${chatbotKey}`;
//       console.log("🔌 Connecting to WebSocket:", wsUrl);
//
//       const ws = new WebSocket(wsUrl);
//
//       ws.onopen = () => {
//         console.log("✅ WebSocket connected");
//         setWsConnected(true);
//
//         // Send ping every 30 seconds to keep connection alive
//         const pingInterval = setInterval(() => {
//           if (ws.readyState === WebSocket.OPEN) {
//             ws.send(JSON.stringify({ type: "ping" }));
//           }
//         }, 30000);
//
//         ws.pingInterval = pingInterval;
//       };
//
//       ws.onmessage = (event) => {
//         try {
//           const data = JSON.parse(event.data);
//           console.log("📨 WebSocket message received:", data);
//
//           handleWebSocketMessage(data);
//         } catch (error) {
//           console.error("❌ Error parsing WebSocket message:", error);
//         }
//       };
//
//       ws.onerror = (error) => {
//         console.error("❌ WebSocket error:", error);
//         setWsConnected(false);
//       };
//
//       ws.onclose = () => {
//         console.log("📴 WebSocket disconnected");
//         setWsConnected(false);
//
//         if (ws.pingInterval) {
//           clearInterval(ws.pingInterval);
//         }
//
//         // Auto-reconnect after 3 seconds
//         reconnectTimeoutRef.current = setTimeout(() => {
//           console.log("🔄 Attempting to reconnect WebSocket...");
//           connectWebSocket(sessId);
//         }, 3000);
//       };
//
//       wsRef.current = ws;
//     } catch (error) {
//       console.error("❌ Failed to create WebSocket:", error);
//     }
//   };
//
//   // Disconnect WebSocket
//   const disconnectWebSocket = () => {
//     if (reconnectTimeoutRef.current) {
//       clearTimeout(reconnectTimeoutRef.current);
//     }
//
//     if (wsRef.current) {
//       if (wsRef.current.pingInterval) {
//         clearInterval(wsRef.current.pingInterval);
//       }
//       wsRef.current.close();
//       wsRef.current = null;
//     }
//
//     setWsConnected(false);
//   };
//
//   // Handle incoming WebSocket messages
//   const handleWebSocketMessage = (data) => {
//     switch (data.type) {
//       case "admin_message":
//         // Admin sent a reply
//         const adminMsg = {
//           id: data.id || `ws_${Date.now()}`,
//           sender: "bot",
//           text: data.message,
//           timestamp: new Date(data.timestamp).toLocaleTimeString('en-IN', {
//             hour: "2-digit",
//             minute: "2-digit",
//             timeZone: "Asia/Kolkata",
//           }),
//           admin_override: true,
//         };
//
//         setMessages(prev => [...prev, adminMsg]);
//         setIsTyping(false);
//         setIsAdminTyping(false);
//         break;
//
//       case "admin_typing":
//         setIsAdminTyping(data.is_typing);
//         break;
//
//       case "message_deleted":
//         setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
//         break;
//
//       case "pong":
//         // Keep-alive response
//         break;
//
//       default:
//         console.log("Unknown WebSocket message type:", data.type);
//     }
//   };
//
//   // Send typing indicator
//   const sendTypingIndicator = (isTyping) => {
//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       wsRef.current.send(JSON.stringify({
//         type: "typing",
//         is_typing: isTyping
//       }));
//     }
//   };
//
//   // Handle input change with typing indicator
//   const handleInputChange = (e) => {
//     const value = e.target.value;
//     setInput(value);
//
//     // Send typing indicator
//     if (value.trim()) {
//       sendTypingIndicator(true);
//
//       // Clear previous timeout
//       if (typingTimeoutRef.current) {
//         clearTimeout(typingTimeoutRef.current);
//       }
//
//       // Stop typing after 2 seconds of no input
//       typingTimeoutRef.current = setTimeout(() => {
//         sendTypingIndicator(false);
//       }, 2000);
//     } else {
//       sendTypingIndicator(false);
//     }
//   };
//
//   const loadHistory = async (sessId) => {
//     try {
//       const response = await fetch(
//         `${API_URL}/client/chat-history/${clientId}/${sessId}`,
//         {
//           headers: {
//             "Content-Type": "application/json",
//             "X-Chatbot-Key": chatbotKey,
//           },
//         },
//       );
//
//       if (response.ok) {
//         const data = await response.json();
//         const activeMessages = (data.chats || []).filter(
//           (chat) => chat.is_active !== 0,
//         );
//
//         const formattedMessages = activeMessages.map((chat) => ({
//           id: chat.id,
//           sender: chat.role === "user" ? "user" : "bot",
//           text: chat.message,
//           timestamp: new Date(chat.created_at).toLocaleTimeString('en-IN', {
//             hour: "2-digit",
//             minute: "2-digit",
//             timeZone: "Asia/Kolkata",
//           }),
//           admin_override: chat.admin_override === 1,
//         }));
//
//         setMessages(formattedMessages);
//       }
//     } catch (err) {
//       console.error("Failed to load history:", err);
//     }
//   };
//
//   const handleNewSession = () => {
//     const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
//     setCurrentSessionId(newSessionId);
//     setMessages([]);
//     setShowSessionPrompt(false);
//
//     const storageKey = `chatbot_session_${clientId}`;
//     const sessionData = {
//       sessionId: newSessionId,
//       timestamp: Date.now(),
//     };
//     localStorage.setItem(storageKey, JSON.stringify(sessionData));
//
//     // Connect WebSocket for new session
//     connectWebSocket(newSessionId);
//   };
//
//   const handleSend = async (messageText = null) => {
//     const textToSend = messageText || input.trim();
//     if (!textToSend) return;
//
//     sendTypingIndicator(false);
//
//     const timestamp = new Date().toLocaleTimeString('en-IN', {
//       hour: "2-digit",
//       minute: "2-digit",
//       timeZone: "Asia/Kolkata",
//     });
//
//     const newMessage = {
//       id: `temp_${Date.now()}`,
//       sender: "user",
//       text: textToSend,
//       timestamp,
//       admin_override: false,
//     };
//
//     setMessages((prev) => [...prev, newMessage]);
//     setInput("");
//     setIsTyping(true);
//
//     // Send via WebSocket if connected
//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       wsRef.current.send(JSON.stringify({
//         type: "user_message",
//         message: textToSend
//       }));
//     }
//
//     try {
//       const res = await fetch(`${API_URL}/client/chat/${clientId}`, {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json",
//           "X-Chatbot-Key": chatbotKey,
//         },
//         body: JSON.stringify({
//           session_id: currentSessionId,
//           message: textToSend,
//         }),
//       });
//
//       if (!res.ok) {
//         throw new Error(`Backend error: ${res.status}`);
//       }
//
//       const data = await res.json();
//
//       if (data.session_id && data.session_id !== currentSessionId) {
//         setCurrentSessionId(data.session_id);
//         const storageKey = `chatbot_session_${clientId}`;
//         const sessionData = {
//           sessionId: data.session_id,
//           timestamp: Date.now(),
//         };
//         localStorage.setItem(storageKey, JSON.stringify(sessionData));
//       }
//
//       // Only add bot message if not from admin (admin messages come via WebSocket)
//       if (!data.admin_override) {
//         const botMessage = {
//           id: `temp_bot_${Date.now()}`,
//           sender: "bot",
//           text: data.reply,
//           timestamp: new Date().toLocaleTimeString('en-IN', {
//             hour: "2-digit",
//             minute: "2-digit",
//             timeZone: "Asia/Kolkata",
//           }),
//           admin_override: false,
//         };
//
//         setMessages((prev) => [...prev, botMessage]);
//       }
//
//       setIsTyping(false);
//
//     } catch (err) {
//       console.error("Chat error:", err);
//       setMessages((prev) => [
//         ...prev,
//         {
//           id: Date.now() + 1,
//           sender: "bot",
//           text: "⚠️ Error contacting backend.",
//           timestamp: new Date().toLocaleTimeString('en-IN', {
//             hour: "2-digit",
//             minute: "2-digit",
//             timeZone: "Asia/Kolkata",
//           }),
//           admin_override: false,
//         },
//       ]);
//       setIsTyping(false);
//     }
//   };
//
//   const handleKeyPress = (e) => {
//     if (e.key === "Enter" && !e.shiftKey) {
//       e.preventDefault();
//       handleSend();
//     }
//   };
//
//   return (
//     <div
//       style={{
//         position: "fixed",
//         bottom: "80px",
//         right: "20px",
//         width: "350px",
//         height: "500px",
//         backgroundColor: "#f0f2f5",
//         display: "flex",
//         flexDirection: "column",
//         fontFamily:
//           '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
//         borderRadius: "12px",
//         overflow: "hidden",
//         boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
//         zIndex: 2000,
//       }}
//     >
//       <div
//         style={{
//           backgroundColor: "white",
//           padding: "12px 16px",
//           display: "flex",
//           alignItems: "center",
//           justifyContent: "space-between",
//           borderBottom: "1px solid #e1e5e9",
//         }}
//       >
//         <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
//           <div
//             style={{
//               width: "36px",
//               height: "36px",
//               backgroundColor: "#6366f1",
//               borderRadius: "50%",
//               display: "flex",
//               alignItems: "center",
//               justifyContent: "center",
//               position: "relative"
//             }}
//           >
//             <Bot size={18} color="white" />
//             {/* WebSocket connection indicator */}
//             <div
//               style={{
//                 position: "absolute",
//                 bottom: "-2px",
//                 right: "-2px",
//                 width: "12px",
//                 height: "12px",
//                 borderRadius: "50%",
//                 backgroundColor: wsConnected ? "#10b981" : "#ef4444",
//                 border: "2px solid white"
//               }}
//               title={wsConnected ? "Connected" : "Disconnected"}
//             />
//           </div>
//           <div>
//             <h3
//               style={{
//                 margin: 0,
//                 fontSize: "15px",
//                 fontWeight: "600",
//                 color: "#1f2937",
//               }}
//             >
//               AI Assistant
//             </h3>
//             <p
//               style={{
//                 margin: 0,
//                 fontSize: "12px",
//                 color: wsConnected ? "#10b981" : "#6b7280",
//               }}
//             >
//               {wsConnected ? "● Online now" : "○ Connecting..."}
//             </p>
//           </div>
//         </div>
//
//         <button
//           onClick={onClose}
//           style={{
//             background: "none",
//             border: "none",
//             color: "#6b7280",
//             cursor: "pointer",
//             padding: "6px",
//             borderRadius: "6px",
//           }}
//         >
//           <X size={18} />
//         </button>
//       </div>
//
//       {showSessionPrompt && (
//         <div
//           style={{
//             position: "absolute",
//             top: "60px",
//             left: 0,
//             right: 0,
//             bottom: 0,
//             backgroundColor: "rgba(255, 255, 255, 0.98)",
//             display: "flex",
//             flexDirection: "column",
//             alignItems: "center",
//             justifyContent: "center",
//             padding: "32px",
//             zIndex: 10,
//           }}
//         >
//           <div
//             style={{
//               width: "80px",
//               height: "80px",
//               backgroundColor: "#f0f2f5",
//               borderRadius: "50%",
//               display: "flex",
//               alignItems: "center",
//               justifyContent: "center",
//               marginBottom: "24px",
//             }}
//           >
//             <Bot size={40} color="#6366f1" />
//           </div>
//
//           <h3
//             style={{
//               fontSize: "18px",
//               fontWeight: "600",
//               color: "#1f2937",
//               margin: "0 0 8px 0",
//               textAlign: "center",
//             }}
//           >
//             Welcome!
//           </h3>
//
//           <p
//             style={{
//               fontSize: "14px",
//               color: "#6b7280",
//               margin: "0 0 32px 0",
//               textAlign: "center",
//               lineHeight: "1.5",
//             }}
//           >
//             Start a new conversation with our AI assistant
//           </p>
//
//           <button
//             onClick={handleNewSession}
//             style={{
//               display: "flex",
//               alignItems: "center",
//               justifyContent: "center",
//               gap: "10px",
//               padding: "14px 24px",
//               backgroundColor: "#6366f1",
//               color: "white",
//               border: "none",
//               borderRadius: "10px",
//               fontSize: "14px",
//               fontWeight: "600",
//               cursor: "pointer",
//               transition: "all 0.2s",
//             }}
//           >
//             <Plus size={16} />
//             Start Conversation
//           </button>
//         </div>
//       )}
//
//       <div
//         style={{
//           flex: 1,
//           overflowY: "auto",
//           padding: "16px",
//           display: "flex",
//           flexDirection: "column",
//           gap: "12px",
//           opacity: showSessionPrompt ? 0.3 : 1,
//           pointerEvents: showSessionPrompt ? "none" : "auto",
//         }}
//       >
//         {messages.length === 0 && !showSessionPrompt && (
//           <div
//             style={{
//               textAlign: "center",
//               color: "#6b7280",
//               marginTop: "40px",
//               fontSize: "14px",
//             }}
//           >
//             <p>👋 Hello! How can we help you today?</p>
//           </div>
//         )}
//
//         {messages.map((msg, idx) => (
//           <div
//             key={`${msg.id}-${idx}`}
//             style={{
//               display: "flex",
//               alignItems: "flex-end",
//               gap: "8px",
//               flexDirection: msg.sender === "user" ? "row-reverse" : "row",
//             }}
//           >
//             <div
//               style={{
//                 width: "28px",
//                 height: "28px",
//                 borderRadius: "50%",
//                 backgroundColor:
//                   msg.sender === "user"
//                     ? "#e5e7eb"
//                     : msg.admin_override
//                       ? "#10b981"
//                       : "#6366f1",
//                 display: "flex",
//                 alignItems: "center",
//                 justifyContent: "center",
//                 flexShrink: 0,
//               }}
//             >
//               {msg.sender === "user" ? (
//                 <User size={14} color="#6b7280" />
//               ) : msg.admin_override ? (
//                 <UserCheck size={14} color="white" />
//               ) : (
//                 <Bot size={14} color="white" />
//               )}
//             </div>
//
//             <div
//               style={{
//                 maxWidth: "250px",
//                 display: "flex",
//                 flexDirection: "column",
//                 alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
//               }}
//             >
//               {msg.admin_override && (
//                 <div
//                   style={{
//                     fontSize: "10px",
//                     fontWeight: "600",
//                     color: "#10b981",
//                     marginBottom: "4px",
//                     display: "flex",
//                     alignItems: "center",
//                     gap: "4px",
//                   }}
//                 >
//                   <UserCheck size={10} />
//                   Support Team
//                 </div>
//               )}
//               <div
//                 style={{
//                   padding: "10px 14px",
//                   borderRadius: "16px",
//                   backgroundColor:
//                     msg.sender === "user"
//                       ? "#6366f1"
//                       : msg.admin_override
//                         ? "#10b981"
//                         : "white",
//                   color:
//                     msg.sender === "user" || msg.admin_override
//                       ? "white"
//                       : "#1f2937",
//                   fontSize: "14px",
//                   lineHeight: "1.4",
//                   boxShadow:
//                     msg.sender === "bot" && !msg.admin_override
//                       ? "0 1px 2px rgba(0,0,0,0.1)"
//                       : "none",
//                   border:
//                     msg.sender === "bot" && !msg.admin_override
//                       ? "1px solid #e5e7eb"
//                       : msg.admin_override
//                         ? "2px solid #059669"
//                         : "none",
//                   whiteSpace: "pre-wrap",
//                 }}
//               >
//                 {msg.sender === "bot" ? (
//                   <ReactMarkdown remarkPlugins={[remarkGfm]}>
//                     {msg.text}
//                   </ReactMarkdown>
//                 ) : (
//                   msg.text
//                 )}
//               </div>
//               <span
//                 style={{
//                   fontSize: "10px",
//                   color: "#6b7280",
//                   marginTop: "4px",
//                 }}
//               >
//                 {msg.timestamp}
//               </span>
//             </div>
//           </div>
//         ))}
//
//         {(isTyping || isAdminTyping) && (
//           <div style={{ display: "flex", gap: "8px" }}>
//             <div
//               style={{
//                 width: "28px",
//                 height: "28px",
//                 borderRadius: "50%",
//                 backgroundColor: isAdminTyping ? "#10b981" : "#6366f1",
//                 display: "flex",
//                 alignItems: "center",
//                 justifyContent: "center",
//               }}
//             >
//               {isAdminTyping ? (
//                 <UserCheck size={14} color="white" />
//               ) : (
//                 <Bot size={14} color="white" />
//               )}
//             </div>
//             <div
//               style={{
//                 padding: "10px 14px",
//                 borderRadius: "16px",
//                 backgroundColor: "white",
//                 border: "1px solid #e5e7eb",
//                 display: "flex",
//                 gap: "4px",
//               }}
//             >
//               {[0, 1, 2].map((i) => (
//                 <div
//                   key={i}
//                   style={{
//                     width: "6px",
//                     height: "6px",
//                     borderRadius: "50%",
//                     backgroundColor: "#9ca3af",
//                     animation: `bounce 1.4s ease-in-out ${i * 0.16}s infinite both`,
//                   }}
//                 ></div>
//               ))}
//             </div>
//           </div>
//         )}
//         <div ref={messagesEndRef} />
//       </div>
//
//       <div
//         style={{
//           backgroundColor: "white",
//           padding: "12px",
//           borderTop: "1px solid #e5e7eb",
//           opacity: showSessionPrompt ? 0.3 : 1,
//           pointerEvents: showSessionPrompt ? "none" : "auto",
//         }}
//       >
//         <div
//           style={{
//             display: "flex",
//             alignItems: "center",
//             gap: "8px",
//           }}
//         >
//           <textarea
//             value={input}
//             onChange={handleInputChange}
//             onKeyPress={handleKeyPress}
//             placeholder="Type your message..."
//             style={{
//               flex: 1,
//               minHeight: "20px",
//               maxHeight: "100px",
//               padding: "10px 14px",
//               border: "1px solid #d1d5db",
//               borderRadius: "20px",
//               backgroundColor: "#f9fafb",
//               fontSize: "14px",
//               resize: "none",
//               outline: "none",
//               fontFamily: "inherit",
//             }}
//             rows="1"
//           />
//           <button
//             onClick={() => handleSend()}
//             disabled={!input.trim() || isTyping}
//             style={{
//               display: "flex",
//               alignItems: "center",
//               gap: "6px",
//               padding: "0 14px",
//               height: "40px",
//               backgroundColor:
//                 input.trim() && !isTyping ? "#6366f1" : "#e5e7eb",
//               border: "none",
//               borderRadius: "20px",
//               color: input.trim() && !isTyping ? "white" : "#9ca3af",
//               cursor: input.trim() && !isTyping ? "pointer" : "not-allowed",
//             }}
//           >
//             <Send size={14} />
//             <span style={{ fontSize: "12px", fontWeight: 500 }}>Send</span>
//           </button>
//         </div>
//         <p
//           style={{
//             fontSize: "12px",
//             color: "#6b7280",
//             margin: "6px 0 0 0",
//             textAlign: "center",
//           }}
//         >
//           Press Enter to send, Shift+Enter for new line
//         </p>
//       </div>
//
//       <style>
//         {`
//           @keyframes bounce {
//             0%, 80%, 100% { transform: scale(0); }
//             40% { transform: scale(1); }
//           }
//         `}
//       </style>
//     </div>
//   );
// };
//
// export default ChatbotWindow;


import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, X, User, Bot, UserCheck, Plus } from "lucide-react";
import { API_URL } from "../config.js";

const ChatbotWindow = ({ onClose, clientId, chatbotKey, sessionId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showSessionPrompt, setShowSessionPrompt] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isAdminTyping, setIsAdminTyping] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // WebSocket URL
  const WS_URL = API_URL.replace('http', 'ws').replace('https', 'wss');

  useEffect(() => {
    console.log("📍 ChatbotWindow mounted with:", {
      clientId,
      sessionId,
      hasSessionId: !!sessionId
    });

    if (sessionId) {
      setCurrentSessionId(sessionId);
      setShowSessionPrompt(false);
      console.log("📚 Loading chat history for session:", sessionId);
      loadHistory(sessionId);
      connectWebSocket(sessionId);
    } else {
      console.warn("⚠️ No session ID provided to ChatbotWindow");
      setShowSessionPrompt(true);
    }

    return () => {
      disconnectWebSocket();
    };
  }, [clientId, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, isAdminTyping]);

  // Connect to WebSocket
  const connectWebSocket = (sessId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log("✅ WebSocket already connected");
      return;
    }

    try {
      const wsUrl = `${WS_URL}/ws/client/${sessId}?chatbot_key=${chatbotKey}`;
      console.log("🔌 Connecting to WebSocket:", wsUrl);

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("✅ WebSocket connected");
        setWsConnected(true);

        // Send ping every 30 seconds to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 30000);

        ws.pingInterval = pingInterval;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📨 WebSocket message received:", data);

          handleWebSocketMessage(data);
        } catch (error) {
          console.error("❌ Error parsing WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setWsConnected(false);
      };

      ws.onclose = () => {
        console.log("📴 WebSocket disconnected");
        setWsConnected(false);

        if (ws.pingInterval) {
          clearInterval(ws.pingInterval);
        }

        // Auto-reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("🔄 Attempting to reconnect WebSocket...");
          connectWebSocket(sessId);
        }, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("❌ Failed to create WebSocket:", error);
    }
  };

  // Disconnect WebSocket
  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      if (wsRef.current.pingInterval) {
        clearInterval(wsRef.current.pingInterval);
      }
      wsRef.current.close();
      wsRef.current = null;
    }

    setWsConnected(false);
  };

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case "admin_message":
        console.log("👨‍💼 Received admin message via WebSocket:", data);

        // Admin sent a reply
        const adminMsg = {
          id: data.id || `ws_admin_${Date.now()}`,
          sender: "bot",
          text: data.message,
          timestamp: new Date(data.timestamp).toLocaleTimeString('en-IN', {
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "Asia/Kolkata",
          }),
          admin_override: true,
        };

        // Prevent duplicates - check if this exact message already exists
        setMessages(prev => {
          // Check by ID or by content + admin_override flag
          const isDuplicate = prev.some(msg =>
          msg.id === adminMsg.id ||
          (msg.text === adminMsg.text && msg.admin_override === true && msg.sender === "bot")
          );

          if (isDuplicate) {
            console.log("⚠️ Duplicate admin message detected, skipping:", adminMsg);
            return prev;
          }

          console.log("✅ Adding new admin message to chat:", adminMsg);
          return [...prev, adminMsg];
        });

        setIsTyping(false);
        setIsAdminTyping(false);
        break;

      case "admin_typing":
        setIsAdminTyping(data.is_typing);
        break;

      case "message_deleted":
        setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
        break;

      case "pong":
        // Keep-alive response
        break;

      default:
        console.log("Unknown WebSocket message type:", data.type);
    }
  };

  // Send typing indicator
  const sendTypingIndicator = (isTyping) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "typing",
        is_typing: isTyping
      }));
    }
  };

  // Handle input change with typing indicator
  const handleInputChange = (e) => {
    const value = e.target.value;
    setInput(value);

    // Send typing indicator
    if (value.trim()) {
      sendTypingIndicator(true);

      // Clear previous timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      // Stop typing after 2 seconds of no input
      typingTimeoutRef.current = setTimeout(() => {
        sendTypingIndicator(false);
      }, 2000);
    } else {
      sendTypingIndicator(false);
    }
  };

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
          timestamp: new Date(chat.created_at).toLocaleTimeString('en-IN', {
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "Asia/Kolkata",
          }),
          admin_override: chat.admin_override === 1,
        }));

        console.log("📚 Loaded chat history:", formattedMessages);
        setMessages(formattedMessages);
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  const handleNewSession = () => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setShowSessionPrompt(false);

    const storageKey = `chatbot_session_${clientId}`;
    const sessionData = {
      sessionId: newSessionId,
      timestamp: Date.now(),
    };
    localStorage.setItem(storageKey, JSON.stringify(sessionData));

    // Connect WebSocket for new session
    connectWebSocket(newSessionId);
  };

  const handleSend = async (messageText = null) => {
    const textToSend = messageText || input.trim();
    if (!textToSend) return;

    sendTypingIndicator(false);

    const timestamp = new Date().toLocaleTimeString('en-IN', {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Kolkata",
    });

    const newMessage = {
      id: `temp_${Date.now()}`,
      sender: "user",
      text: textToSend,
      timestamp,
      admin_override: false,
    };

    setMessages((prev) => [...prev, newMessage]);
    setInput("");
    setIsTyping(true);

    // Send via WebSocket if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "user_message",
        message: textToSend
      }));
    }

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
      console.log("📤 Received response from backend:", data);

      if (data.session_id && data.session_id !== currentSessionId) {
        setCurrentSessionId(data.session_id);
        const storageKey = `chatbot_session_${clientId}`;
        const sessionData = {
          sessionId: data.session_id,
          timestamp: Date.now(),
        };
        localStorage.setItem(storageKey, JSON.stringify(sessionData));
      }

      // IMPORTANT: Only add bot message if it's NOT from admin
      // Admin messages will come via WebSocket, so we skip them here
      if (!data.admin_override && data.reply) {
        console.log("🤖 Adding bot reply (not admin):", data.reply);

        const botMessage = {
          id: data.message_id || `bot_${Date.now()}`,
          sender: "bot",
          text: data.reply,
          timestamp: new Date().toLocaleTimeString('en-IN', {
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "Asia/Kolkata",
          }),
          admin_override: false,
        };

        setMessages((prev) => {
          // Check for duplicates
          const isDuplicate = prev.some(msg => msg.id === botMessage.id);
          if (isDuplicate) {
            console.log("⚠️ Duplicate bot message, skipping");
            return prev;
          }
          return [...prev, botMessage];
        });
      } else if (data.admin_override) {
        console.log("👨‍💼 Admin reply detected in HTTP response - will be handled by WebSocket");
        // Don't add admin messages from HTTP response
        // They will arrive via WebSocket
      }

      setIsTyping(false);

    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
                  sender: "bot",
                  text: "⚠️ Error contacting backend.",
                  timestamp: new Date().toLocaleTimeString('en-IN', {
                    hour: "2-digit",
                    minute: "2-digit",
                    timeZone: "Asia/Kolkata",
                  }),
                  admin_override: false,
        },
      ]);
      setIsTyping(false);
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
      position: "relative"
    }}
    >
    <Bot size={18} color="white" />
    {/* WebSocket connection indicator */}
    <div
    style={{
      position: "absolute",
      bottom: "-2px",
      right: "-2px",
      width: "12px",
      height: "12px",
      borderRadius: "50%",
      backgroundColor: wsConnected ? "#10b981" : "#ef4444",
      border: "2px solid white"
    }}
    title={wsConnected ? "Connected" : "Disconnected"}
    />
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
      color: wsConnected ? "#10b981" : "#6b7280",
    }}
    >
    {wsConnected ? "● Online now" : "○ Connecting..."}
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
      >
      <Plus size={16} />
      Start Conversation
      </button>
      </div>
    )}

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
      {msg.sender === "bot" ? (
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {msg.text}
        </ReactMarkdown>
      ) : (
        msg.text
      )}
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

    {(isTyping || isAdminTyping) && (
      <div style={{ display: "flex", gap: "8px" }}>
      <div
      style={{
        width: "28px",
        height: "28px",
        borderRadius: "50%",
        backgroundColor: isAdminTyping ? "#10b981" : "#6366f1",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      >
      {isAdminTyping ? (
        <UserCheck size={14} color="white" />
      ) : (
        <Bot size={14} color="white" />
      )}
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
    onChange={handleInputChange}
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
