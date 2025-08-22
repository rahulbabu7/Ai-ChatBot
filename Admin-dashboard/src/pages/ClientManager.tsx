// // src/pages/ClientManager.tsx
// // import { useParams } from "react-router-dom";

// // const ClientManager = () => {
// //   const { clientId } = useParams();

// //   return (
// //     <div>
// //       <h2>Manage {clientId}</h2>
// //       <button onClick={() => alert("🚀 Trigger crawl")}>Crawl Website</button>
// //       <button onClick={() => alert("📥 Upload Q&A")}>Upload Q&A</button>
// //       <button onClick={() => alert("⚡ Run embeddings")}>Run Embeddings</button>
// //     </div>
// //   );
// // };

// // export default ClientManager;
// // 
// // 
// // 

// import { useParams } from "react-router-dom";
// import { useState } from "react";

// const API = "http://localhost:8000";

// const ClientManager = () => {
//   const { clientId } = useParams();
//   const [allowed_domain, setDomain] = useState("");
//   const [startUrl, setStartUrl] = useState("");
//   const [busy, setBusy] = useState(false);
//   const [log, setLog] = useState<string>("");

//   const call = async (url: string, options: RequestInit = {}) => {
//     setBusy(true);
//     setLog(`POST ${url} ...`);
//     try {
//       const res = await fetch(`${API}${url}`, options);
//       const data = await res.json();
//       setLog(JSON.stringify(data, null, 2));
//     } catch (e: any) {
//       setLog(`Error: ${e?.message || e}`);
//     } finally {
//       setBusy(false);
//     }
//   };

//   const triggerCrawl = () =>
//     call("/admin/crawl", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         client_id: clientId,
//        allowed_domain,   // ✅ fixed (was allowed_domain)
//         start_url: startUrl,
//       }),
//     });

//   const runEmbeddings = () =>
//     call(`/admin/embed/${clientId}`, { method: "POST" }); // ✅ fixed (was body)

//   const uploadQA = async () => {
//     // Prepare sample JSON file
//     const sample = [
//       { question: "who is the principal", answer: "Dr. X is the principal." },
//       { question: "college name", answer: "ABC College of Engineering." },
//     ];
//     const blob = new Blob([JSON.stringify(sample, null, 2)], { type: "application/json" });
//     const formData = new FormData();
//     formData.append("file", blob, "custom_qa.json");

//     call(`/admin/upload-qa/${clientId}`, {
//       method: "POST",
//       body: formData,
//     });
//   };

//   return (
//     <div>
//       <h2>Manage {clientId}</h2>

//       <div style={{ display: "grid", gap: 8, maxWidth: 600 }}>
//         <input
//           placeholder="Allowed domain (abc.edu)"
//           value={allowed_domain}
//           onChange={(e) => setDomain(e.target.value)}
//         />
//         <input
//           placeholder="Start URL (https://abc.edu/)"
//           value={startUrl}
//           onChange={(e) => setStartUrl(e.target.value)}
//         />
//         <button disabled={busy} onClick={triggerCrawl}>
//           🚀 Crawl Website
//         </button>
//         <button disabled={busy} onClick={runEmbeddings}>
//           ⚡ Run Embeddings
//         </button>
//         <button disabled={busy} onClick={uploadQA}>
//           📥 Upload Q&A (sample)
//         </button>
//       </div>

//       <pre
//         style={{
//           marginTop: 16,
//           background: "#111",
//           color: "#0f0",
//           padding: 12,
//           maxHeight: 300,
//           overflow: "auto",
//         }}
//       >
//         {log}
//       </pre>
//     </div>
//   );
// };

// export default ClientManager;


// // src/pages/ClientManager.tsx
import { useParams } from "react-router-dom";
import { useState } from "react";

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
    <div>
      <h2>Manage {clientId}</h2>

      <div style={{ display: "grid", gap: 10, maxWidth: 600 }}>
        {/* Crawl settings */}
        <input
          placeholder="Allowed domain (abc.edu)"
          value={allowed_domain}
          onChange={(e) => setDomain(e.target.value)}
        />
        <input
          placeholder="Start URL (https://abc.edu/)"
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
        <input
          type="file"
          accept="application/json"
          onChange={(e) => setQaFile(e.target.files?.[0] || null)}
        />
        <button disabled={busy} onClick={uploadQA}>
          📥 Upload Q&A
        </button>
      </div>

      {/* Logs */}
      <pre
        style={{
          marginTop: 16,
          background: "#111",
          color: "#0f0",
          padding: 12,
          maxHeight: 300,
          overflow: "auto",
        }}
      >
        {log}
      </pre>
    </div>
  );
};

export default ClientManager;
