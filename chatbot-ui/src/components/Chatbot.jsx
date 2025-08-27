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



import React, { useState } from "react";
import { FaComments } from "react-icons/fa";
import ChatbotWindow from "./ChatbotWindow";
import "./Chatbot.css";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [clientId, setClientId] = useState("pydantic"); // default client

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
          <option value="sjcet">SJCET</option>
          <option value="client2">Client 2</option>
          <option value="client3">Client 3</option>
        </select>
      </div>

      {/* Chat window */}
      {isOpen && (
        <ChatbotWindow clientId={clientId} onClose={() => setIsOpen(false)} />
      )}

      {/* Floating button */}
      <button className="chatbot-button" onClick={() => setIsOpen(!isOpen)}>
        <FaComments size={24} />
      </button>
    </div>
  );
};

export default Chatbot;
