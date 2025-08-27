import { useParams } from "react-router-dom";
import { useState } from "react";
import "../App.css"; // ensure CSS applies

const API = "http://localhost:8000";

const ClientManager = () => {
  const { clientId } = useParams();
  const [allowed_domain, setDomain] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string>("");
  const [qaFile, setQaFile] = useState<File | null>(null);

  const call = async (url: string, options: RequestInit = {}) => {
    setBusy(true);
    setLog(`POST ${url} ...`);
    try {
      const res = await fetch(`${API}${url}`, options);
      const data = await res.json();
      setLog(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setLog(`Error: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  const triggerCrawl = () =>
    call("/admin/crawl", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: clientId,
        allowed_domain,
        start_url: startUrl,
      }),
    });

  const runEmbeddings = () =>
    call(`/admin/embed/${clientId}`, { method: "POST" });

  const uploadQA = async () => {
    if (!qaFile) {
      alert("Please select a JSON file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", qaFile);

    call(`/admin/upload-qa/${clientId}`, {
      method: "POST",
      body: formData,
    });
  };

  return (
    <div className="client-manager">
      <div className="dashboard-card">
        <h2 className="client-title">Manage {clientId}</h2>

        <div className="client-controls">
          {/* Crawl settings */}
          <label htmlFor="allowedDomain">Allowed Domain:</label>
          <input
            id="allowedDomain"
            placeholder="e.g. abc.edu"
            value={allowed_domain}
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

export default ClientManager;
