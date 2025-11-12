import React, { useState, useEffect } from 'react';
import { Globe, Plus, Check, AlertCircle, Copy, ExternalLink, Trash2 } from 'lucide-react';
import 'assets/scss/style.scss';
import { API_URL } from '../../../config';
const Domain = () => {
  const [domains, setDomains] = useState([]);
  const [newDomain, setNewDomain] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [showIntegrationCode, setShowIntegrationCode] = useState(false);

  // Get JWT token from storage
  const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');

  useEffect(() => {
    if (!token) {
      setMessage({ type: 'error', text: 'Please login first to manage your domains.' });
      setIsLoading(false);
      return;
    }
    fetchClientDomains();
  }, [token]);

  const fetchClientDomains = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/client/domains/me`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('Failed to fetch domains');
      const data = await res.json();
      setDomains(data.domains || []);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load your domains.' });
    } finally {
      setIsLoading(false);
    }
  };

  const addDomain = async () => {
    if (!newDomain.trim()) return;
    setIsAdding(true);
    try {
      const res = await fetch(`${API_URL}/client/register-my-domains/me`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify([newDomain.trim()])
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setMessage({ type: 'success', text: `Domain "${data.registered_domains[0]}" registered successfully!` });
        setNewDomain('');
        fetchClientDomains();
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to register domain' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setIsAdding(false);
      setTimeout(() => setMessage({ type: '', text: '' }), 5000);
    }
  };

  const deleteDomain = async (domainName) => {
    if (!window.confirm(`Are you sure you want to delete "${domainName}"?`)) return;

    try {
      const res = await fetch(`${API_URL}/client/domains/me/${domainName}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });

      if (!res.ok) throw new Error('Failed to delete domain');

      setMessage({ type: 'success', text: `Domain "${domainName}" deleted successfully!` });
      fetchClientDomains();
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to delete "${domainName}".` });
    } finally {
      setTimeout(() => setMessage({ type: '', text: '' }), 5000);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setMessage({ type: 'success', text: 'Copied to clipboard!' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to copy to clipboard' });
    } finally {
      setTimeout(() => setMessage({ type: '', text: '' }), 2000);
    }
  };

  const integrationCode = `<!-- Add this to your website -->
  <script>
    (function() {
      const domain = encodeURIComponent(window.location.hostname);
      const iframe = document.createElement("iframe");
      iframe.src = "https://aichat360.kochi.digital?domain=" + domain;
      iframe.style.cssText = "position:fixed; bottom:20px; right:20px; width:400px; height:600px; border:none; z-index:999999;";
      document.body.appendChild(iframe);
    })();
  </script>
  `;
  const simpleIntegrationCode = `<!-- Add this to your website  replace yourDomain with the correct domain -->


<iframe
  src="https://aichat360.kochi.digital/?domain=yourDomain"
  style="position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; border: none; z-index: 999999;">
</iframe>`;

  if (isLoading)
    return (
      <div className="container mt-4">
        <div className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading domains...</p>
        </div>
      </div>
    );

  if (!token)
    return (
      <div className="container mt-4">
        <div className="alert alert-danger text-center">Please login first to manage your domains.</div>
      </div>
    );

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div className="d-flex align-items-center">
          <Globe className="me-2" size={24} style={{ color: '#0d6efd' }} />
          <div>
            <h2 className="mb-0">My Domains</h2>
            <p className="text-muted mb-0">Manage domains where your chatbot will appear</p>
          </div>
        </div>
        <button className="btn btn-success d-flex align-items-center" onClick={() => setShowIntegrationCode(!showIntegrationCode)}>
          <ExternalLink className="me-2" size={16} />
          Integration Code
        </button>
      </div>

      {/* Status Message */}
      {message.text && (
        <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-danger'} d-flex align-items-center`}>
          {message.type === 'success' ? <Check className="me-2" size={16} /> : <AlertCircle className="me-2" size={16} />}
          {message.text}
        </div>
      )}

      {/* Integration Code Section */}
      {showIntegrationCode && (
        <div className="card p-4 shadow-sm mb-4">
          <h5 className="card-title">Integration Code</h5>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <label className="form-label mb-0">Add this to your website</label>
            <button className="btn btn-outline-primary btn-sm d-flex align-items-center" onClick={() => copyToClipboard(integrationCode)}>
              <Copy className="me-1" size={14} /> Copy
            </button>
          </div>
          <pre className="bg-dark text-success p-3 rounded" style={{ fontSize: '0.8rem', overflowX: 'auto' }}>
            {integrationCode}
          </pre>
        </div>
      )}

      {/* Integration Code Section */}
      {showIntegrationCode && (
        <div className="card p-4 shadow-sm mb-4">
          <h5 className="card-title">Integration Code</h5>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <label className="form-label mb-0">Add this to your website</label>
            <button className="btn btn-outline-primary btn-sm d-flex align-items-center" onClick={() => copyToClipboard(integrationCode)}>
              <Copy className="me-1" size={14} /> Copy
            </button>
          </div>
          <pre className="bg-dark text-success p-3 rounded" style={{ fontSize: '0.8rem', overflowX: 'auto' }}>
            {simpleIntegrationCode}
          </pre>
        </div>
      )}

      {/* Add Domain Section */}
      <div className="card p-4 shadow-sm mb-4">
        <h5 className="card-title">Add New Domain</h5>
        <div className="row">
          <div className="col-md-8">
            <input
              type="text"
              className="form-control"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              placeholder="yourdomain.com"
              onKeyPress={(e) => e.key === 'Enter' && addDomain()}
            />
          </div>
          <div className="col-md-4">
            <button
              className="btn btn-primary w-100 d-flex align-items-center justify-content-center"
              onClick={addDomain}
              disabled={!newDomain.trim() || isAdding}
            >
              {isAdding ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="me-2" size={16} />
                  Add Domain
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Domains List Section */}
      <div className="card p-4 shadow-sm">
        <h5 className="card-title">Registered Domains</h5>
        {domains.length === 0 ? (
          <div className="text-center py-5">
            <Globe className="text-muted mb-3" size={48} />
            <h6 className="text-muted">No domains registered yet</h6>
            <p className="text-muted">Add your first domain to get started with the chatbot integration.</p>
          </div>
        ) : (
          <div className="row">
            {domains.map((domain, i) => (
              <div key={i} className="col-md-6 mb-3">
                <div className="card h-100 border">
                  <div className="card-body">
                    <div className="d-flex align-items-start justify-content-between">
                      <div className="d-flex align-items-center flex-grow-1">
                        <div className="bg-primary bg-opacity-10 rounded-circle p-2 me-3">
                          <Globe className="text-primary" size={20} />
                        </div>
                        <div className="flex-grow-1">
                          <h6 className="card-title mb-1">{domain.domain}</h6>
                          <small className="text-muted">Registered on {new Date(domain.created_at).toLocaleDateString()}</small>
                        </div>
                      </div>
                      <div className="d-flex align-items-center gap-2">
                        <span className="badge bg-success d-flex align-items-center">
                          <Check className="me-1" size={12} /> Active
                        </span>
                        <button className="btn btn-outline-danger btn-sm" onClick={() => deleteDomain(domain.domain)} title="Delete domain">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Domain;
