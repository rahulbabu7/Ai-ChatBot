import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import "../App.css";

const API = "http://localhost:8000";

const AdminDashboard = () => {
  const [clients, setClients] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [newClient, setNewClient] = useState("");
  const [log, setLog] = useState("");

  // Fetch existing clients
  const fetchClients = async () => {
    try {
      const res = await fetch(`${API}/admin/clients`);
      const data = await res.json();
      setClients(data.clients || []);
    } catch (err) {
      console.error("Error fetching clients:", err);
      setLog("❌ Failed to fetch clients.");
    } finally {
      setLoading(false);
    }
  };

  // Add new client
  const addClient = async () => {
    if (!newClient.trim()) return;
    try {
      const res = await fetch(`${API}/admin/add-client`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: newClient }),
      });
      const data = await res.json();
      setLog(data.message || "✅ Client added");
      setClients(data.clients || []);
      setNewClient("");
    } catch (err: any) {
      setLog(`❌ Error: ${err.message || err}`);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  return (
    <div className="admin-dashboard">
      <div className="dashboard-card">
        <h1 className="client-title">Admin Dashboard</h1>

        {/* Input + Add Client */}
        <div className="client-input-row">
          <input
            type="text"
            placeholder="Enter new client ID"
            value={newClient}
            onChange={(e) => setNewClient(e.target.value)}
          />
          <button onClick={addClient}>➕ Add Client</button>
        </div>

        {/* Logs */}
        {log && (
          <p
            className={`log-message ${
              log.startsWith("✅") ? "log-success" : log.startsWith("❌") ? "log-error" : ""
            }`}
          >
            {log}
          </p>
        )}

        {/* Client list */}
        {loading ? (
          <p>Loading clients...</p>
        ) : clients.length === 0 ? (
          <p>No clients found.</p>
        ) : (
          <ol>
            {clients.map((c) => (
              <li key={c}>
                <Link to={`/client/${c}`}>{c}</Link>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
