// src/pages/AdminDashboard.tsx
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

const API = "http://localhost:8000";

const AdminDashboard = () => {
  const [clients, setClients] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [newClient, setNewClient] = useState("");
  const [log, setLog] = useState("");

  const fetchClients = async () => {
    try {
      const res = await fetch(`${API}/admin/clients`);
      const data = await res.json();
      setClients(data.clients || []);
    } catch (err) {
      console.error("Error fetching clients:", err);
    } finally {
      setLoading(false);
    }
  };

  const addClient = async () => {
    if (!newClient.trim()) return;
    try {
      const res = await fetch(`${API}/admin/add-client`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: newClient }),
      });
      const data = await res.json();
      setLog(data.message);
      setClients(data.clients);
      setNewClient("");
    } catch (err: any) {
      setLog(`Error: ${err.message || err}`);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  if (loading) return <p>Loading clients...</p>;

  return (
    <div>
      <h2>Admin Dashboard</h2>

      <div style={{ marginBottom: 20 }}>
        <input
          placeholder="Enter new client ID"
          value={newClient}
          onChange={(e) => setNewClient(e.target.value)}
        />
        <button onClick={addClient}>➕ Add Client</button>
      </div>

      {log && <p>{log}</p>}

      {clients.length === 0 ? (
        <p>No clients found.</p>
      ) : (
        <ul>
          {clients.map((c) => (
            <li key={c}>
              <Link to={`/client/${c}`}>{c}</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AdminDashboard;
