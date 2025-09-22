import React, { useState, useEffect } from 'react';
import { Globe, Plus, Check, AlertCircle, Copy, ExternalLink, Trash2 } from 'lucide-react';

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
      const res = await fetch('http://localhost:8000/client/domains/me', {
        headers: { 'x-token': token }
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
      const res = await fetch('http://localhost:8000/client/me/register-domains', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-token': token },
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
      const res = await fetch(`http://localhost:8000/client/domains/me/${domainName}`, {
        method: 'DELETE',
        headers: { 'x-token': token }
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
  <div id="chatbot-container"></div>
  <script>
    const iframe = document.createElement('iframe');
    iframe.src = 'http://localhost:3000/chatbot';
    iframe.style.cssText = 'position:fixed;bottom:20px;right:20px;width:400px;height:600px;border:none;z-index:1000;';
    document.body.appendChild(iframe);
  </script>`;

  if (isLoading) return <div className="flex items-center justify-center min-h-screen">Loading domains...</div>;
  if (!token) return <div className="text-center mt-10 text-red-600">Please login first to manage your domains.</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="px-4 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Globe className="w-6 h-6 text-blue-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">My Domains</h2>
              <p className="text-sm text-gray-600">Manage domains where your chatbot will appear</p>
            </div>
          </div>
          <button onClick={() => setShowIntegrationCode(!showIntegrationCode)} className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700">
            <ExternalLink className="w-4 h-4" />
            Integration Code
          </button>
        </div>

        {/* Status Message */}
        {message.text && (
          <div className={`mx-6 mt-4 p-3 rounded-lg flex items-center gap-2 ${message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
            {message.type === 'success' ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {message.text}
          </div>
        )}

        {/* Integration Code */}
        {showIntegrationCode && (
          <div className="px-4 py-4 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-3">Integration Code</h3>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Add this to your website</label>
              <button onClick={() => copyToClipboard(integrationCode)} className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1">
                <Copy className="w-3 h-3" /> Copy
              </button>
            </div>
            <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto">{integrationCode}</pre>
          </div>
        )}

        {/* Add Domain */}
        <div className="px-4 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Add New Domain</h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              placeholder="yourdomain.com"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
              onKeyPress={(e) => e.key === 'Enter' && addDomain()}
            />
            <button onClick={addDomain} disabled={!newDomain.trim() || isAdding} className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-300">
              {isAdding ? 'Adding...' : <><Plus className="w-4 h-4" /> Add Domain</>}
            </button>
          </div>
        </div>

        {/* Domains List */}
        <div className="px-4 py-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Registered Domains</h3>
          {domains.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Globe className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-lg font-medium">No domains registered yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {domains.map((domain, i) => (
                <div key={i} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <Globe className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">{domain.domain}</h4>
                      <p className="text-sm text-gray-500">Registered on {new Date(domain.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                      <Check className="w-3 h-3" /> Active
                    </span>
                    <button onClick={() => deleteDomain(domain.domain)} className="text-red-600 hover:text-red-800 p-1 rounded border border-red-200" title="Delete domain">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Domain;
