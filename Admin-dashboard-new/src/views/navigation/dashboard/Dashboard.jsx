import { useParams, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import "../App.css";

const API = "http://localhost:8000";

const Dashboard = () => {
  const { clientId } = useParams();
  const [clientName, setClientName] = useState("");
  const [allowedDomain, setDomain] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("");
  const [qaFile, setQaFile] = useState(null);

  // fetch client details on mount
  useEffect(() => {
    const fetchClient = async () => {
      try {
        const res = await fetch(`${API}/client/${clientId}`);
        if (!res.ok) throw new Error("Failed to fetch client");
        const data = await res.json();
        setClientName(data.name); // use "name" from DB
      } catch (e) {
        console.error(e);
        setClientName(clientId || "Unknown Client");
      }
    };
    fetchClient();
  }, [clientId]);

  const call = async (url, options = {}) => {
    setBusy(true);
    setLog(`POST ${url} ...`);
    try {
      const res = await fetch(`${API}${url}`, options);
      const data = await res.json();
      setLog(JSON.stringify(data, null, 2));
    } catch (e) {
      setLog(`Error: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  const triggerCrawl = () =>
    call(`/client/crawl`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: clientId,
        allowed_domain: allowedDomain,
        start_url: startUrl,
      }),
    });

  const runEmbeddings = () =>
    call(`/client/embed/${clientId}`, { method: "POST" });

  const uploadQA = async () => {
    if (!qaFile) {
      alert("Please select a JSON file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", qaFile);

    call(`/client/upload-qa/${clientId}`, {
      method: "POST",
      body: formData,
    });
  };

  return (
    <div className="client-manager">
      <div className="dashboard-card">
        <h2 className="client-title">Manage Client: {clientName}</h2>

        <div className="client-controls">
          {/* Crawl settings */}
          <label htmlFor="allowedDomain">Allowed Domain:</label>
          <input
            id="allowedDomain"
            placeholder="e.g. abc.edu"
            value={allowedDomain}
            onChange={(e) => setDomain(e.target.value)}
          />

          <label htmlFor="startUrl">Start URL:</label>
          <input
            id="startUrl"
            placeholder="e.g. https://abc.edu/"
            value={startUrl}
            onChange={(e) => setStartUrl(e.target.value)}
          />

          <button disabled={busy} onClick={triggerCrawl}>
            🚀 Crawl Website
          </button>

          {/* Embeddings */}
          <button disabled={busy} onClick={runEmbeddings}>
            ⚡ Run Embeddings
          </button>

          {/* Upload Q&A */}
          <label htmlFor="qaFile">Upload Q&A JSON File:</label>
          <input
            id="qaFile"
            type="file"
            accept="application/json"
            onChange={(e) => setQaFile(e.target.files?.[0] || null)}
          />
          <button disabled={busy} onClick={uploadQA}>
            📥 Upload Q&A
          </button>
        </div>

        {/* Logs */}
        <pre className="client-log">{log}</pre>
      </div>
    </div>
  );
};

export default Dashboard;
