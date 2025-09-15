import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import "assets/scss/style.scss"; // use the global SCSS

const API = "http://localhost:8000";

const AdminDashboard = () => {
  const [clients, setClients] = useState([]);
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
    } catch (err) {
      setLog(`❌ Error: ${err.message || err}`);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  return (
    <div className="container mt-4">
      <div className="card">
        <div className="card-body">
          <h2 className="mb-3">Admin Dashboard</h2>

          {/* Back to Home */}
          <div className="mb-3">
            <Link to="/">
              <button className="btn btn-outline-secondary">🏠 Back to Home</button>
            </Link>
          </div>

          {/* Add New Client */}
          <div className="mb-3 d-flex gap-2">
            <input
              type="text"
              className="form-control"
              placeholder="Enter new client ID"
              value={newClient}
              onChange={(e) => setNewClient(e.target.value)}
            />
            <button className="btn btn-primary" onClick={addClient}>
              ➕ Add Client
            </button>
          </div>

          {/* Logs */}
          {log && (
            <p
              className={`${
                log.startsWith("✅") ? "text-success" : log.startsWith("❌") ? "text-danger" : ""
              }`}
            >
              {log}
            </p>
          )}

          {/* Client List */}
          {loading ? (
            <p>Loading clients...</p>
          ) : clients.length === 0 ? (
            <p>No clients found.</p>
          ) : (
            <ul className="list-group">
              {clients.map((c) => (
                <li key={c.client_id} className="list-group-item">
                  {/* ✅ Link to Dashboard.jsx using client_id */}
                  <Link to={`/client/${c.client_id}`}>
                    {c.name} ({c.email})
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
