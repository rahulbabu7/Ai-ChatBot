// src/pages/ClientManager.tsx
import { useParams } from "react-router-dom";

const ClientManager = () => {
  const { clientId } = useParams();

  return (
    <div>
      <h2>Manage {clientId}</h2>
      <button onClick={() => alert("🚀 Trigger crawl")}>Crawl Website</button>
      <button onClick={() => alert("📥 Upload Q&A")}>Upload Q&A</button>
      <button onClick={() => alert("⚡ Run embeddings")}>Run Embeddings</button>
    </div>
  );
};

export default ClientManager;