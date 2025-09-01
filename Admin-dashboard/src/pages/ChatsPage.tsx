import { useEffect, useState } from "react";
import axios from "axios";

interface Client {
  client_id: string;
  name: string;
  username: string;
  email: string;
}

interface Session {
  session_id: string;
}

interface Chat {
  session_id: string;
  role: string;
  message: string;
  user_agent: string;
  created_at: string;
}

export default function ChatsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClient, setSelectedClient] = useState<string>("");
  const [sessions, setSessions] = useState<string[]>([]);
  const [selectedSession, setSelectedSession] = useState<string>("");
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(false);

  // Load all clients (admin view)
  useEffect(() => {
    axios.get("http://localhost:8000/admin/clients").then((res) => {
      setClients(res.data.clients);
    });
  }, []);

  // Load sessions when client changes
  useEffect(() => {
    if (selectedClient) {
      axios
        .get(`http://localhost:8000/client/${selectedClient}/sessions`)
        .then((res) => {
          setSessions(res.data.sessions);
          setSelectedSession("");
          setChats([]);
        });
    }
  }, [selectedClient]);

  // Load chats when session changes
  useEffect(() => {
    if (selectedClient && selectedSession) {
      setLoading(true);
      axios
        .get(
          `http://localhost:8000/client/${selectedClient}/chats?session_id=${selectedSession}`
        )
        .then((res) => {
          setChats(res.data.chats);
        })
        .finally(() => setLoading(false));
    }
  }, [selectedClient, selectedSession]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Client Chats</h1>

      {/* Select Client */}
      <div>
        <label className="font-semibold">Select Client:</label>
        <select
          className="ml-2 p-2 border rounded"
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
      </div>

      {/* Select Session */}
      {sessions.length > 0 && (
        <div>
          <label className="font-semibold">Select Session:</label>
          <select
            className="ml-2 p-2 border rounded"
            value={selectedSession}
            onChange={(e) => setSelectedSession(e.target.value)}
          >
            <option value="">-- Choose Session --</option>
            {sessions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Chat Messages */}
      <div className="border p-4 rounded bg-gray-50 max-h-[500px] overflow-y-auto">
        {loading ? (
          <p>Loading chats...</p>
        ) : chats.length === 0 ? (
          <p className="text-gray-500">No chats available.</p>
        ) : (
          chats.map((chat, i) => (
            <div
              key={i}
              className={`my-2 p-2 rounded ${
                chat.role === "user"
                  ? "bg-blue-100 text-left"
                  : "bg-green-100 text-right"
              }`}
            >
              <p className="text-sm text-gray-600">
                [{chat.role}] {new Date(chat.created_at).toLocaleString()}  
              </p>
              <p className="text-base">{chat.message}</p>
              <p className="text-xs text-gray-500">UA: {chat.user_agent}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

