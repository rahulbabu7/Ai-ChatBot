import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import "assets/scss/style.scss";

const API = "http://localhost:8000";

const Dashboard = () => {
  const navigate = useNavigate();

  const [clientName, setClientName] = useState("");
  const [allowedDomain, setDomain] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("");
  const [qaFile, setQaFile] = useState(null);
  
  // Task management
  const [activeTasks, setActiveTasks] = useState({});
  const [taskHistory, setTaskHistory] = useState([]);

  const token = localStorage.getItem("jwt_token") || sessionStorage.getItem("jwt_token");

  useEffect(() => {
    if (!token) {
      setClientName("Unknown Client");
      return;
    }
    const fetchClient = async () => {
      try {
        const res = await fetch(`${API}/client/me`, {
          headers: { "x-token": token },
        });
        if (!res.ok) throw new Error("Failed to fetch client");
        const data = await res.json();
        setClientName(data.name || "Unknown Client");
      } catch (e) {
        console.error(e);
        setClientName("Unknown Client");
      }
    };
    fetchClient();
  }, [token]);

  // Fetch all client tasks on component mount
  useEffect(() => {
    if (token) {
      fetchClientTasks();
    }
  }, [token]);

  const fetchClientTasks = async () => {
    try {
      const res = await fetch(`${API}/client/me/tasks`, {
        headers: { "x-token": token },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveTasks(data.tasks || {});
        
        // Convert to array for history display
        const taskArray = Object.entries(data.tasks || {}).map(([id, task]) => ({
          id,
          ...task
        }));
        setTaskHistory(taskArray.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)));
      }
    } catch (e) {
      console.error("Failed to fetch tasks:", e);
    }
  };

  const pollTaskStatus = useCallback(async (taskId) => {
    if (!taskId) return;
    
    try {
      const res = await fetch(`${API}/client/me/task-status/${taskId}`, {
        headers: { "x-token": token },
      });
      
      if (res.ok) {
        const taskData = await res.json();
        
        setActiveTasks(prev => ({
          ...prev,
          [taskId]: taskData
        }));
        
        // Update task history
        setTaskHistory(prev => {
          const updated = prev.map(task => 
            task.id === taskId ? { id: taskId, ...taskData } : task
          );
          
          // Add new task if not in history
          if (!updated.find(task => task.id === taskId)) {
            updated.unshift({ id: taskId, ...taskData });
          }
          
          return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        });
        
        // Continue polling if task is still running
        if (taskData.status === "running" || taskData.status === "queued") {
          setTimeout(() => pollTaskStatus(taskId), 2000);
        } else {
          // Task completed, refresh client tasks
          setTimeout(fetchClientTasks, 1000);
        }
        
        setLog(JSON.stringify(taskData, null, 2));
      }
    } catch (e) {
      console.error(`Failed to poll task ${taskId}:`, e);
    }
  }, [token]);

  const call = async (url, options = {}) => {
    setBusy(true);
    setLog(`POST ${url} ...`);
    try {
      const res = await fetch(`${API}${url}`, {
        ...options,
        headers: { ...(options.headers || {}), "x-token": token },
      });
      const data = await res.json();
      setLog(JSON.stringify(data, null, 2));
      
      // If response contains task_id, start polling
      if (data.task_id) {
        pollTaskStatus(data.task_id);
      }
      
      return data;
    } catch (e) {
      setLog(`Error: ${e?.message || e}`);
      throw e;
    } finally {
      setBusy(false);
    }
  };

  const triggerCrawlAndEmbed = async () => {
    if (!allowedDomain || !startUrl) {
      alert("Please fill in the allowed domain and start URL.");
      return;
    }

    try {
      const data = await call("/client/me/crawl-and-embed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ allowed_domain: allowedDomain, start_url: startUrl }),
      });
      
      if (data.task_id) {
        setLog(`Task started with ID: ${data.task_id}\nStatus: ${data.status}\nMessage: ${data.message}`);
      }
    } catch (e) {
      console.error("Failed to start crawl and embed:", e);
    }
  };

  const triggerCrawlOnly = async () => {
    if (!allowedDomain || !startUrl) {
      alert("Please fill in the allowed domain and start URL.");
      return;
    }

    try {
      await call("/client/me/crawl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ allowed_domain: allowedDomain, start_url: startUrl }),
      });
    } catch (e) {
      console.error("Failed to start crawl:", e);
    }
  };

  const triggerEmbedOnly = async () => {
    try {
      await call("/client/me/embed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
    } catch (e) {
      console.error("Failed to start embeddings:", e);
    }
  };

  const uploadQA = async () => {
    if (!qaFile) {
      alert("Please select a JSON file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", qaFile);

    try {
      await call("/client/me/upload-qa", {
        method: "POST",
        body: formData,
      });
    } catch (e) {
      console.error("Failed to upload Q&A:", e);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed": return "success";
      case "failed": return "danger";
      case "running": return "primary";
      case "queued": return "warning";
      default: return "secondary";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed": return "✅";
      case "failed": return "❌";
      case "running": return "🔄";
      case "queued": return "⏳";
      default: return "📋";
    }
  };

  const refreshTasks = () => {
    fetchClientTasks();
  };

  if (!token) {
    return (
      <div className="text-center mt-10 text-red-600">
        Please login to access the dashboard.
      </div>
    );
  }

  return (
    <div className="container mt-4">
      <div className="mb-3">
        <button className="btn btn-secondary" onClick={() => navigate("/dashboard-admin")}>
          ← Back to Admin Dashboard
        </button>
        <button className="btn btn-info ms-2" onClick={refreshTasks}>
          🔄 Refresh Tasks
        </button>
      </div>

      <h2 className="mb-4">Manage Client: {clientName}</h2>
      
      {/* Crawling Configuration */}
      <div className="card p-4 shadow-sm mb-4">
        <h5 className="card-title">Website Crawling & Embeddings</h5>
        
        <div className="mb-3">
          <label htmlFor="allowedDomain" className="form-label">Allowed Domain:</label>
          <input
            id="allowedDomain"
            className="form-control mb-3"
            placeholder="e.g. abc.edu"
            value={allowedDomain}
            onChange={(e) => setDomain(e.target.value)}
          />

          <label htmlFor="startUrl" className="form-label">Start URL:</label>
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
            🚀 Crawl & Embed (Full Pipeline)
          </button>
          <button 
            className="btn btn-info" 
            disabled={busy} 
            onClick={triggerCrawlOnly}
          >
            🕷️ Crawl Only
          </button>
          <button 
            className="btn btn-success" 
            disabled={busy} 
            onClick={triggerEmbedOnly}
          >
            🧠 Embed Only
          </button>
        </div>

        {/* Q&A Upload */}
        <div className="mb-3 border-top pt-3">
          <label htmlFor="qaFile" className="form-label">Upload Q&A JSON File:</label>
          <input
            id="qaFile"
            type="file"
            accept="application/json"
            className="form-control mb-2"
            onChange={(e) => setQaFile(e.target.files?.[0] || null)}
          />
          <button 
            className="btn btn-warning" 
            disabled={busy || !qaFile} 
            onClick={uploadQA}
          >
            📥 Upload Q&A
          </button>
        </div>
      </div>

      {/* Active Tasks Status */}
      {Object.keys(activeTasks).length > 0 && (
        <div className="card p-4 shadow-sm mb-4">
          <h5 className="card-title">Active Tasks</h5>
          <div className="row">
            {Object.entries(activeTasks).map(([taskId, task]) => (
              <div key={taskId} className="col-md-6 mb-3">
                <div className={`card border-${getStatusColor(task.status)}`}>
                  <div className="card-body">
                    <h6 className="card-title">
                      {getStatusIcon(task.status)} {taskId.split('_')[0].toUpperCase()}
                    </h6>
                    <p className="card-text">
                      <strong>Status:</strong> <span className={`badge bg-${getStatusColor(task.status)}`}>
                        {task.status}
                      </span>
                    </p>
                    <p className="card-text">{task.message}</p>
                    {task.progress > 0 && (
                      <div className="progress mb-2">
                        <div 
                          className="progress-bar" 
                          style={{width: `${task.progress}%`}}
                        >
                          {task.progress}%
                        </div>
                      </div>
                    )}
                    <small className="text-muted">
                      Last Updated: {new Date(task.updated_at).toLocaleString()}
                    </small>
                    {task.status === "running" && (
                      <button 
                        className="btn btn-sm btn-outline-primary mt-2"
                        onClick={() => pollTaskStatus(taskId)}
                      >
                        🔄 Refresh Status
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task History */}
      {taskHistory.length > 0 && (
        <div className="card p-4 shadow-sm mb-4">
          <h5 className="card-title">Task History</h5>
          <div className="table-responsive">
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Status</th>
                  <th>Message</th>
                  <th>Progress</th>
                  <th>Last Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {taskHistory.slice(0, 10).map((task) => (
                  <tr key={task.id}>
                    <td>
                      <small className="text-muted">{task.id}</small>
                    </td>
                    <td>
                      <span className={`badge bg-${getStatusColor(task.status)}`}>
                        {getStatusIcon(task.status)} {task.status}
                      </span>
                    </td>
                    <td>
                      <small>{task.message}</small>
                    </td>
                    <td>
                      {task.progress > 0 && (
                        <div className="progress" style={{height: '20px', width: '100px'}}>
                          <div 
                            className="progress-bar progress-bar-sm" 
                            style={{width: `${task.progress}%`}}
                          >
                            {task.progress}%
                          </div>
                        </div>
                      )}
                    </td>
                    <td>
                      <small>{new Date(task.updated_at).toLocaleString()}</small>
                    </td>
                    <td>
                      {(task.status === "running" || task.status === "queued") && (
                        <button 
                          className="btn btn-sm btn-outline-primary"
                          onClick={() => pollTaskStatus(task.id)}
                        >
                          🔄
                        </button>
                      )}
                      {task.result && (
                        <button 
                          className="btn btn-sm btn-outline-info ms-1"
                          onClick={() => setLog(JSON.stringify(task, null, 2))}
                          title="View Details"
                        >
                          👁️
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Logs Section */}
      <div className="card p-4 shadow-sm">
        <h5 className="card-title">Logs & Status</h5>
        <pre className="bg-light p-3 border rounded" style={{maxHeight: '400px', overflow: 'auto'}}>
          {log || "No logs yet. Start a task to see real-time updates."}
        </pre>
      </div>

      {/* System Information */}
      {/* <div className="mt-4">
        <div className="alert alert-info">
          <h6>🚀 Concurrent Processing Enabled</h6>
          <p className="mb-0">
            Your tasks now run in the background! You can start multiple crawling and embedding 
            operations simultaneously. The system will process them concurrently without blocking 
            other users.
          </p>
        </div>
      </div>*/}
    </div>
  );
};

export default Dashboard;