// import React, { useState } from "react";

// const ChatbotWindow = ({ onClose }) => {
//   const [messages, setMessages] = useState([
//     { sender: "bot", text: "Hello! How can I help you today?" }
//   ]);
//   const [input, setInput] = useState("");

//   const handleSend = async () => {
//     if (!input.trim()) return;

//     const newMessage = { sender: "user", text: input };
//     setMessages((prev) => [...prev, newMessage]);
//     setInput("");

//     try {
//       const res = await fetch("http://localhost:8000/chat", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ message: input }),
//       });

//       const data = await res.json();
//       setMessages((prev) => [
//         ...prev,
//         { sender: "bot", text: data.reply }
//       ]);
//     } catch (err) {
//       setMessages((prev) => [
//         ...prev,
//         { sender: "bot", text: "⚠️ Error contacting backend." }
//       ]);
//     }
//   };

//   return (
//     <div className="chat-window">
//       <div className="chat-header">
//         <h4>Chatbot</h4>
//         <button onClick={onClose}>×</button>
//       </div>

//       <div className="chat-messages">
//         {messages.map((msg, idx) => (
//           <div
//             key={idx}
//             className={`message ${msg.sender === "user" ? "user" : "bot"}`}
//           >
//             {msg.text}
//           </div>
//         ))}
//       </div>

//       <div className="chat-input">
//         <input
//           type="text"
//           value={input}
//           placeholder="Type a message..."
//           onChange={(e) => setInput(e.target.value)}
//           onKeyDown={(e) => e.key === "Enter" && handleSend()}
//         />
//         <button onClick={handleSend}>Send</button>
//       </div>
//     </div>
//   );
// };

// export default ChatbotWindow;
// 
// 
// 
// 

// import React, { useState } from "react";

// const ChatbotWindow = ({ onClose, clientId }) => {
//   const [messages, setMessages] = useState([
//     { sender: "bot", text: "Hello! How can I help you today?" }
//   ]);
//   const [input, setInput] = useState("");

//   const handleSend = async () => {
//     if (!input.trim()) return;

//     const newMessage = { sender: "user", text: input };
//     setMessages((prev) => [...prev, newMessage]);
//     setInput("");

//     try {
//       const res = await fetch(`http://localhost:8000/client/chat/${clientId}`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ client_id: clientId, message: input }), // ✅ include clientId
//       });

//       const data = await res.json();
//       setMessages((prev) => [
//         ...prev,
//         { sender: "bot", text: data.reply }
//       ]);
//     } catch (err) {
//       setMessages((prev) => [
//         ...prev,
//         { sender: "bot", text: "⚠️ Error contacting backend." }
//       ]);
//     }
//   };

//   return (
//     <div className="chat-window">
//       <div className="chat-header">
//         <h4>Chatbot ({clientId})</h4> {/* ✅ show client id */}
//         <button onClick={onClose}>×</button>
//       </div>

//       <div className="chat-messages">
//         {messages.map((msg, idx) => (
//           <div
//             key={idx}
//             className={`message ${msg.sender === "user" ? "user" : "bot"}`}
//           >
//             {msg.text}
//           </div>
//         ))}
//       </div>

//       <div className="chat-input">
//         <input
//           type="text"
//           value={input}
//           placeholder="Type a message..."
//           onChange={(e) => setInput(e.target.value)}
//           onKeyDown={(e) => e.key === "Enter" && handleSend()}
//         />
//         <button onClick={handleSend}>Send</button>
//       </div>
//     </div>
//   );
// };

// export default ChatbotWindow;


import React, { useState, useEffect } from "react";

const ChatbotWindow = ({ onClose, clientId, chatbotKey }) => {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! How can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");

  // Generate a unique session_id per visitor
  useEffect(() => {
    if (!sessionId) {
      setSessionId(crypto.randomUUID());
    }
  }, [sessionId]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const newMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, newMessage]);
    const userInput = input;
    setInput("");

    try {
      const res = await fetch(`http://localhost:8000/client/chat/${clientId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-chatbot-key": chatbotKey, // ✅ required by backend
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
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: data.reply }
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Error contacting backend." }
      ]);
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <h4>Chatbot ({clientId})</h4>
        <button onClick={onClose}>×</button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`message ${msg.sender === "user" ? "user" : "bot"}`}
          >
            {msg.text}
          </div>
        ))}
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          placeholder="Type a message..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
};

export default ChatbotWindow;

