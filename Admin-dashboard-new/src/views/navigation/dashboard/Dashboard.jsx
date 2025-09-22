import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "assets/scss/style.scss"; // global SCSS

const API = "http://localhost:8000";

const Dashboard = () => {
  const { clientId } = useParams();   // ✅ use route param
  const navigate = useNavigate();

  const [clientName, setClientName] = useState("");
  const [allowedDomain, setDomain] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("");
  const [qaFile, setQaFile] = useState(null);

  useEffect(() => {
    if (!clientId) {
      setClientName("Unknown Client");
      return;
    }
    const fetchClient = async () => {
      try {
        const res = await fetch(`${API}/client/${clientId}`);
        if (!res.ok) throw new Error("Failed to fetch client");
        const data = await res.json();
        console.log(data)
        setClientName(data.name || clientId);
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

  const triggerCrawlAndEmbed = () => {
    if (!allowedDomain || !startUrl) {
      alert("Please fill in the allowed domain and start URL.");
      return;
    }

    call(`/client/crawl-and-embed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: clientId,
        allowed_domain: allowedDomain,
        start_url: startUrl,
      }),
    });
  };

  const uploadQA = () => {
    if (!qaFile) {
      alert("Please select a JSON file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", qaFile);
    formData.append("client_id", clientId);

    call(`/client/upload-qa/${clientId}`, {
      method: "POST",
      body: formData,
    });
  };

  return (
    <div className="container mt-4">
      <div className="mb-3">
        <button
          className="btn btn-secondary"
          onClick={() => navigate("/dashboard-admin")}
        >
          ← Back to Admin Dashboard
        </button>
      </div>

      <h2 className="mb-4">Manage Client: {clientName}</h2>
      <div className="card p-4 shadow-sm">
        <div className="mb-3">
          <label htmlFor="allowedDomain" className="form-label">
            Allowed Domain:
          </label>
          <input
            id="allowedDomain"
            className="form-control mb-3"
            placeholder="e.g. abc.edu"
            value={allowedDomain}
            onChange={(e) => setDomain(e.target.value)}
          />

          <label htmlFor="startUrl" className="form-label">
            Start URL:
          </label>
          <input
            id="startUrl"
            className="form-control mb-3"
            placeholder="e.g. https://abc.edu/"
            value={startUrl}
            onChange={(e) => setStartUrl(e.target.value)}
          />
        </div>

        <div className="d-flex flex-wrap gap-2 mb-3">
          <button
            className="btn btn-primary"
            disabled={busy}
            onClick={triggerCrawlAndEmbed}
          >
            🚀 Start Crawl and Embedding
          </button>
        </div>

        <div className="mb-3">
          <label htmlFor="qaFile" className="form-label">
            Upload Q&A JSON File:
          </label>
          <input
            id="qaFile"
            type="file"
            accept="application/json"
            className="form-control mb-2"
            onChange={(e) => setQaFile(e.target.files?.[0] || null)}
          />
          <button
            className="btn btn-info"
            disabled={busy || !qaFile}
            onClick={uploadQA}
          >
            📥 Upload Q&A
          </button>
        </div>

        <div className="mt-3">
          <h6>Logs:</h6>
          <pre className="bg-light p-2 border rounded">{log}</pre>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
