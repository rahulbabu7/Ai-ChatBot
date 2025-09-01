// import React, { useState } from "react";
// import { FaComments } from "react-icons/fa";
// import ChatbotWindow from "./ChatbotWindow";
// import "./Chatbot.css";

// const Chatbot = () => {
//   const [isOpen, setIsOpen] = useState(false);

//   return (
//     <div className="chatbot-container">
//       {isOpen && <ChatbotWindow onClose={() => setIsOpen(false)} />}
//       <button className="chatbot-button" onClick={() => setIsOpen(!isOpen)}>
//         <FaComments size={24} />
//       </button>
//     </div>
//   );
// };

// export default Chatbot;



// import React, { useState } from "react";
// import { FaComments } from "react-icons/fa";
// import ChatbotWindow from "./ChatbotWindow";
// import "./Chatbot.css";

// const Chatbot = () => {
//   const [isOpen, setIsOpen] = useState(false);
//   const [clientId, setClientId] = useState("kochi_digital_d491a0"); // default client

//   return (
//     <div className="chatbot-container">
//       {/* Dropdown to select client */}
//       <div className="client-selector">
//         <label htmlFor="client">Choose Client: </label>
//         <select
//           id="client"
//           value={clientId}
//           onChange={(e) => setClientId(e.target.value)}
//         >
//           <option value="sjcet">SJCET</option>
//           <option value="client2">Client 2</option>
//           <option value="client3">Client 3</option>
//         </select>
//       </div>

//       {/* Chat window */}
//       {isOpen && (
//         <ChatbotWindow clientId={clientId} onClose={() => setIsOpen(false)} />
//       )}

//       {/* Floating button */}
//       <button className="chatbot-button" onClick={() => setIsOpen(!isOpen)}>
//         <FaComments size={24} />
//       </button>
//     </div>
//   );
// };

// export default Chatbot;


import React, { useState } from "react";
import { FaComments } from "react-icons/fa";
import ChatbotWindow from "./ChatbotWindow";
import "./Chatbot.css";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [clientId, setClientId] = useState("kochi_digital_d491a0"); // default client
  const [chatbotKey, setChatbotKey] = useState("e024cbbad9ab41e4a5a0c53f0450102d"); // 🔑 replace with real key from signup/login

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
          <option value="kochi_digital_d491a0">Kochi Digital</option>
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
