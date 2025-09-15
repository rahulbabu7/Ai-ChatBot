import { useState } from "react";
import { Link } from "react-router-dom";
import "assets/scss/style.scss"; // use the global SCSS

const Dashboard = () => {
  const [domain, setDomain] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);

  return (
    <div className="container mt-4">
      <div className="card">
        <div className="card-body">
          <h3 className="mb-4">Client Dashboard</h3>

          {/* Allowed Domain */}
          <div className="mb-3">
            <label className="form-label">Allowed Domain:</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. abc.edu"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            />
          </div>

          {/* Start URL */}
          <div className="mb-3">
            <label className="form-label">Start URL:</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. https://abc.edu/"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>

          {/* Crawl Website */}
          <div className="mb-3">
            <button className="btn btn-primary w-100">🚀 Crawl Website</button>
          </div>

          {/* Run Embeddings */}
          <div className="mb-3">
            <button className="btn btn-success w-100">⚡ Run Embeddings</button>
          </div>

          {/* Upload Q&A JSON File */}
          <div className="mb-3">
            <label className="form-label">📥 Upload Q&A JSON File:</label>
            <input
              type="file"
              className="form-control"
              accept=".json"
              onChange={(e) => setFile(e.target.files[0])}
            />
            {file && <small className="text-muted">Selected: {file.name}</small>}
          </div>

          {/* Back to Default Dashboard */}
          <div className="mt-4">
            <Link to="/">
              <button className="btn btn-outline-secondary w-100">
                ⬅ Back to Dashboard
              </button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 
