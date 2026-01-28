import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import 'assets/scss/style.scss';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';

const Dashboard = () => {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [clientName, setClientName] = useState('');
  const [allowedDomain, setDomain] = useState('');
  const [startUrl, setStartUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState('');
  const [qaFile, setQaFile] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);

  // Task management
  const [activeTasks, setActiveTasks] = useState({});
  const [taskHistory, setTaskHistory] = useState([]);

  // New states for custom Q&A
  const [showQAModal, setShowQAModal] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [qaList, setQaList] = useState([]);

  // New states for viewing content
  const [showViewModal, setShowViewModal] = useState(false);
  const [viewType, setViewType] = useState(''); // 'qa' or 'pdf'
  const [viewContent, setViewContent] = useState(null);

  useEffect(() => {
    if (!token) {
      setClientName('Unknown Client');
      return;
    }
    const fetchClient = async () => {
      try {
        const res = await fetch(`${API_URL}/client/me`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });
        if (!res.ok) throw new Error('Failed to fetch client');
        const data = await res.json();
        setClientName(data.name || 'Unknown Client');
      } catch (e) {
        console.error(e);
        setClientName('Unknown Client');
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
      const res = await fetch(`${API_URL}/client/me/tasks`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setActiveTasks(data.tasks || {});

        const taskArray = Object.entries(data.tasks || {}).map(([id, task]) => ({
          id,
          ...task
        }));
        setTaskHistory(taskArray.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)));
      }
    } catch (e) {
      console.error('Failed to fetch tasks:', e);
    }
  };

  const pollTaskStatus = useCallback(
    async (taskId) => {
      if (!taskId) return;

      try {
        const res = await fetch(`${API_URL}/client/me/task-status/${taskId}`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });

        if (res.ok) {
          const taskData = await res.json();

          setActiveTasks((prev) => ({
            ...prev,
            [taskId]: taskData
          }));

          setTaskHistory((prev) => {
            const updated = prev.map((task) => (task.id === taskId ? { id: taskId, ...taskData } : task));
            if (!updated.find((task) => task.id === taskId)) {
              updated.unshift({ id: taskId, ...taskData });
            }
            return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
          });

          if (taskData.status === 'running' || taskData.status === 'queued') {
            setTimeout(() => pollTaskStatus(taskId), 2000);
          } else {
            setTimeout(fetchClientTasks, 1000);
          }

          setLog(JSON.stringify(taskData, null, 2));
        }
      } catch (e) {
        console.error(`Failed to poll task ${taskId}:`, e);
      }
    },
    [token]
  );

  // const call = async (url, options = {}) => {
  //   setBusy(true);
  //   setLog(`Calling ${url} ...`);
  //   try {
  //     const res = await fetch(`${API_URL}${url}`, {
  //       ...options,
  //       headers: { ...(options.headers || {}), 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
  //     });
  //     const data = await res.json();
  //     setLog(JSON.stringify(data, null, 2));

  //     if (data.task_id) {
  //       pollTaskStatus(data.task_id);
  //     }

  //     return data;
  //   } catch (e) {
  //     setLog(`Error: ${e?.message || e}`);
  //     throw e;
  //   } finally {
  //     setBusy(false);
  //   }
  // };
  const call = async (url, options = {}) => {
    setBusy(true);
    setLog(`Calling ${url} ...`);
    try {
      const headers = { ...(options.headers || {}), Authorization: `Bearer ${token}` };

      // If body is FormData, do NOT set Content-Type (browser sets it automatically)
      if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
      }

      const res = await fetch(`${API_URL}${url}`, { ...options, headers });
      const data = await res.json();
      setLog(JSON.stringify(data, null, 2));

      if (data.task_id) pollTaskStatus(data.task_id);

      return data;
    } catch (e) {
      setLog(`Error: ${e?.message || e}`);
      throw e;
    } finally {
      setBusy(false);
    }
  };

  // Existing functions...
  const triggerCrawlAndEmbed = async () => {
    if (!allowedDomain || !startUrl) {
      alert('Please fill in the allowed domain and start URL.');
      return;
    }
    try {
      const data = await call('/client/me/crawl-and-embed', {
        method: 'POST',
        body: JSON.stringify({ allowed_domain: allowedDomain, start_url: startUrl })
      });
      if (data.task_id) {
        setLog(`Task started with ID: ${data.task_id}\nStatus: ${data.status}\nMessage: ${data.message}`);
      }
    } catch (e) {
      console.error('Failed to start crawl and embed:', e);
    }
  };

  const uploadQA = async () => {
    if (!qaFile) {
      alert('Please select a JSON file first.');
      return;
    }
    const formData = new FormData();
    formData.append('file', qaFile);
    try {
      await call('/client/upload-qa/me', {
        method: 'POST',
        body: formData
      });
    } catch (e) {
      console.error('Failed to upload Q&A:', e);
    }
  };

  const uploadPDF = async () => {
    if (!pdfFile) {
      alert('Please select a PDF file first.');
      return;
    }
    const formData = new FormData();
    formData.append('file', pdfFile);
    try {
      await call('/client/upload-pdf/me', {
        method: 'POST',
        body: formData
      });
    } catch (e) {
      console.error('Failed to upload PDF:', e);
    }
  };

  const triggerPDFEmbed = async () => {
    try {
      const data = await call('/client/me/embed-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({})
      });
      if (data.task_id) {
        setLog(`PDF Embedding Task started with ID: ${data.task_id}\nStatus: ${data.status}\nMessage: ${data.message}`);
      }
    } catch (e) {
      console.error('Failed to start PDF embedding:', e);
    }
  };

  // Custom Q&A functions
  const addQAPair = () => {
    if (!question.trim() || !answer.trim()) {
      alert('Please fill both fields');
      return;
    }
    setQaList([...qaList, { question, answer }]);
    setQuestion('');
    setAnswer('');
  };

  const submitQAs = async () => {
    if (qaList.length === 0) {
      alert('Please add at least one Q&A.');
      return;
    }

    const qaJson = qaList;
    const blob = new Blob([JSON.stringify(qaJson, null, 2)], { type: 'application/json' });
    const formData = new FormData();
    formData.append('file', blob, 'manual_qa.json');

    try {
      await call('/client/upload-qa/me', { method: 'POST', body: formData });
      setShowQAModal(false);
      setQuestion('');
      setAnswer('');
    } catch (e) {
      console.error('Failed to upload Q&A:', e);
    }
  };

  // New functions for viewing content
  const viewQAContent = async () => {
    try {
      const data = await call('/client/view-qa/me', { method: 'GET' });
      setViewContent(data);
      setViewType('qa');
      setShowViewModal(true);
    } catch (e) {
      console.error('Failed to fetch Q&A content:', e);
    }
  };

  const viewPDFInfo = async () => {
    try {
      const data = await call('/client/view-pdf-info/me', { method: 'GET' });
      setViewContent(data);
      setViewType('pdf');
      setShowViewModal(true);
    } catch (e) {
      console.error('Failed to fetch PDF info:', e);
    }
  };

  const deleteContent = async (contentType) => {
    if (!confirm(`Are you sure you want to delete your ${contentType} content?`)) {
      return;
    }

    try {
      const endpoint = contentType === 'qa' ? '/client/delete-qa/me' : '/client/delete-pdf/me';
      const data = await call(endpoint, { method: 'DELETE' });
      
      setShowViewModal(false);
      setViewContent(null);
      
      // Handle re-embedding task if returned
      if (data.re_embedding?.task_id) {
        setLog(`${contentType.toUpperCase()} deleted successfully!\n\n` + 
               `Re-embedding Task: ${data.re_embedding.task_id}\n` + 
               `Status: ${data.re_embedding.status}\n` + 
               `Message: ${data.re_embedding.message}\n` + 
               `Remaining sources: ${data.re_embedding.remaining_sources?.join(', ') || 'none'}`);
        
        // Start polling the re-embedding task
        pollTaskStatus(data.re_embedding.task_id);
      } else {
        setLog(`${contentType.toUpperCase()} deleted successfully!\n\n` + 
               (data.message || 'No re-embedding needed (no other sources remain)'));
      }
      
      // Refresh tasks to show the new re-embedding task
      setTimeout(fetchClientTasks, 1000);
    } catch (e) {
      console.error(`Failed to delete ${contentType}:`, e);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'danger';
      case 'running':
        return 'primary';
      case 'pending':
        return 'warning';
      default:
        return 'secondary';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      case 'running':
        return '🔄';
      case 'queued':
        return '⏳';
      default:
        return '📋';
    }
  };

  const refreshTasks = () => fetchClientTasks();


  return (
    <div className="container mt-4">
      {/* Top actions */}
      {/* <div className="mb-3">
        <button className="btn btn-secondary" onClick={() => navigate('/dashboard-admin')}>
          ← Back to Admin Dashboard
        </button>
        <button className="btn btn-info ms-2" onClick={refreshTasks}>
          🔄 Refresh Tasks
        </button>
      </div>*/}

      <h2 className="mb-4">Manage Client: {clientName}</h2>

      {/* Crawling Config */}
      <div className="card p-4 shadow-sm mb-4">
        <h5 className="card-title">Website Crawling & Embeddings</h5>
        <div className="mb-3">
          <label className="form-label">Allowed Domain:</label>
          <input className="form-control mb-3" value={allowedDomain} onChange={(e) => setDomain(e.target.value)} />
          <label className="form-label">Start URL:</label>
          <input className="form-control mb-3" value={startUrl} onChange={(e) => setStartUrl(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={busy} onClick={triggerCrawlAndEmbed}>
          🚀 Crawl & Embed Website
        </button>
      </div>

      {/* Q&A Section */}
      <div className="card p-4 shadow-sm mb-4">
        <h5 className="card-title">Custom Q&A Management</h5>
        <div className="row">
          <div className="col-md-8">
            <label className="form-label">Upload Q&A JSON File:</label>
            <input
              type="file"
              accept="application/json"
              className="form-control mb-2"
              onChange={(e) => setQaFile(e.target.files?.[0] || null)}
            />
            <div className="d-flex flex-wrap gap-2">
              <button className="btn btn-warning" disabled={busy || !qaFile} onClick={uploadQA}>
                📥 Upload Q&A File
              </button>
              <button className="btn btn-outline-success" onClick={() => setShowQAModal(true)}>
                ➕ Add Custom Q&A
              </button>
            </div>
          </div>
          <div className="col-md-4">
            <label className="form-label">Manage Existing Q&A:</label>
            <div className="d-grid gap-2">
              <button className="btn btn-outline-info" onClick={viewQAContent}>
                👁️ View Q&A Content
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* PDF Section */}
      <div className="card p-4 shadow-sm mb-4">
        <h5 className="card-title">PDF Document Management</h5>
        <div className="row">
          <div className="col-md-8">
            <label className="form-label">Upload Custom PDF:</label>
            <input
              type="file"
              accept="application/pdf"
              className="form-control mb-2"
              onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
            />
            <div className="d-flex flex-wrap gap-2">
              <button className="btn btn-warning" disabled={busy || !pdfFile} onClick={uploadPDF}>
                📄 Upload PDF
              </button>
              <button className="btn btn-success" disabled={busy} onClick={triggerPDFEmbed}>
                🚀 Embed PDF
              </button>
            </div>
          </div>
          <div className="col-md-4">
            <label className="form-label">Manage Existing PDF:</label>
            <div className="d-grid gap-2">
              <button className="btn btn-outline-info" onClick={viewPDFInfo}>
                👁️ View PDF Info
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Custom Q&A Modal */}
      {showQAModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Add Custom Q&A Pairs</h5>
                <button className="btn-close" onClick={() => setShowQAModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label">Question</label>
                  <input
                    type="text"
                    className="form-control"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Enter your question..."
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Answer</label>
                  <textarea
                    className="form-control"
                    rows="3"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Enter the answer..."
                  ></textarea>
                </div>
                <button className="btn btn-secondary mb-3" onClick={addQAPair}>
                  ➕ Add to List ({qaList.length} items)
                </button>

                {qaList.length > 0 && (
                  <div className="border p-3 bg-light" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    <h6>Q&A List Preview:</h6>
                    {qaList.map((qa, i) => (
                      <div key={i} className="mb-2 p-2 border-bottom">
                        <strong>Q{i + 1}:</strong> {qa.question}
                        <br />
                        <strong>A{i + 1}:</strong> {qa.answer}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setShowQAModal(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={submitQAs} disabled={qaList.length === 0}>
                  📤 Submit All Q&As ({qaList.length})
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content Viewer Modal */}
      {showViewModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-xl">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">{viewType === 'qa' ? 'Q&A Content' : 'PDF Information'}</h5>
                <button className="btn-close" onClick={() => setShowViewModal(false)}></button>
              </div>
              <div className="modal-body">
                {viewType === 'qa' && viewContent && (
                  <div>
                    {viewContent.has_qa ? (
                      <div>
                        <div className="alert alert-success">Found {viewContent.qa_count} Q&A pairs</div>
                        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                          {viewContent.qa_data.map((qa, i) => (
                            <div key={i} className="card mb-2">
                              <div className="card-body">
                                <h6 className="card-title">
                                  Q{i + 1}: {qa.question || qa.questions?.[0]}
                                </h6>
                                {qa.questions?.length > 1 && (
                                  <small className="text-muted">Alternative questions: {qa.questions.slice(1).join(', ')}</small>
                                )}
                                <p className="card-text mt-2">
                                  <strong>Answer:</strong> {qa.answer}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="alert alert-warning">{viewContent.message}</div>
                    )}
                  </div>
                )}

                {viewType === 'pdf' && viewContent && (
                  <div>
                    {viewContent.has_pdf ? (
                      <div>
                        <div className="alert alert-success">PDF file found and processed</div>
                        <div className="row">
                          <div className="col-md-6">
                            <h6>File Information:</h6>
                            <ul className="list-group list-group-flush">
                              <li className="list-group-item">
                                <strong>Filename:</strong> {viewContent.pdf_info.filename}
                              </li>
                              <li className="list-group-item">
                                <strong>Size:</strong> {viewContent.pdf_info.size_mb} MB
                              </li>
                              <li className="list-group-item">
                                <strong>Text Extracted:</strong> {viewContent.has_extracted_text ? 'Yes' : 'No'}
                              </li>
                              {viewContent.pdf_info.word_count && (
                                <li className="list-group-item">
                                  <strong>Word Count:</strong> {viewContent.pdf_info.word_count}
                                </li>
                              )}
                            </ul>
                          </div>
                          <div className="col-md-6">
                            {viewContent.pdf_info.preview && (
                              <div>
                                <h6>Text Preview:</h6>
                                <div className="border p-3 bg-light" style={{ maxHeight: '300px', overflowY: 'auto', fontSize: '0.9em' }}>
                                  {viewContent.pdf_info.preview}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="alert alert-warning">No PDF file found</div>
                    )}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setShowViewModal(false)}>
                  Close
                </button>
                {((viewType === 'qa' && viewContent?.has_qa) || (viewType === 'pdf' && viewContent?.has_pdf)) && (
                  <button className="btn btn-danger" onClick={() => deleteContent(viewType)}>
                    🗑️ Delete {viewType === 'qa' ? 'Q&A' : 'PDF'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Logs */}
      <div className="card p-4 shadow-sm">
        <h5 className="card-title">Logs & Status</h5>
        <pre className="bg-light p-3 border rounded" style={{ maxHeight: '400px', overflow: 'auto' }}>
          {log || 'No logs yet. Start a task to see real-time updates.'}
        </pre>
      </div>
    </div>
  );
};

export default Dashboard;
