import { useEffect, useState } from "react";
import axios from "axios";
import "./ChatsPage.css";

export default function ChatsPage() {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState("");
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [visitorCount, setVisitorCount] = useState(0);

  useEffect(() => {
    axios.get("http://localhost:8000/admin/clients").then((res) => {
      setClients(res.data.clients);
    });
  }, []);

  useEffect(() => {
    if (selectedClient) {
      axios
        .get(`http://localhost:8000/client/${selectedClient}/sessions`)
        .then((res) => {
          setSessions(res.data.sessions);
          setSelectedSession("");
          setChats([]);
          setVisitorCount(res.data.sessions.length);
        });
    } else {
      setVisitorCount(0);
      setSessions([]);
      setChats([]);
      setSelectedSession("");
    }
  }, [selectedClient]);

  useEffect(() => {
    if (selectedClient && selectedSession) {
      setLoading(true);
      axios
        .get(
          `http://localhost:8000/client/${selectedClient}/chats?session_id=${selectedSession}`
        )
        .then((res) => setChats(res.data.chats))
        .finally(() => setLoading(false));
    }
  }, [selectedClient, selectedSession]);

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <h2>Clients</h2>

        {/* Client Select with accessible label and title */}
        <label htmlFor="clientSelect" className="sr-only">
          Select Client
        </label>
        <select
          id="clientSelect"
          title="Select Client"
          value={selectedClient}
          onChange={(e) => setSelectedClient(e.target.value)}
        >
          <option value="">-- Choose Client --</option>
          {clients.map((c) => (
            <option key={c.client_id} value={c.client_id}>
              {c.name} ({c.username})
            </option>
          ))}
        </select>

        {/* Visitor Count */}
        {selectedClient && (
          <div className="visitor-card">
            <h3>Chats</h3>
            <p>{visitorCount}</p>
          </div>
        )}

        {/* Session List */}
        {sessions.length > 0 && (
          <div className="sessions-list">
            <h3>Chat History</h3>
            {sessions.map((s) => (
              <div
                key={s}
                className={`session-item ${
                  selectedSession === s ? "active" : ""
                }`}
                onClick={() => setSelectedSession(s)}
              >
                {s}
              </div>
            ))}
          </div>
        )}
      </aside>

      {/* Chat Area */}
      <main className="chat-main">
        {loading ? (
          <p className="loading-text">Loading chats...</p>
        ) : chats.length === 0 ? (
          <p className="loading-text">Select a session to view chats</p>
        ) : (
          <div className="chat-messages">
            {chats.map((chat, i) => (
              <div
                key={i}
                className={`chat-message ${
                  chat.role === "user" ? "user" : "bot"
                }`}
              >
                <div className="message-content">{chat.message}</div>
                <div className="message-meta">
                  [{chat.role}] {new Date(chat.created_at).toLocaleString()} | UA:{" "}
                  {chat.user_agent}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
