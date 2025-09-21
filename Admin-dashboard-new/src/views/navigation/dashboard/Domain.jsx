import React, { useState, useEffect } from 'react';
import { Globe, Plus, Trash2, Check, AlertCircle, Copy, ExternalLink } from 'lucide-react';

const Domain = () => {
  const [domains, setDomains] = useState([]);
  const [newDomain, setNewDomain] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [showIntegrationCode, setShowIntegrationCode] = useState(false);
  const [clientCredentials, setClientCredentials] = useState({
    clientId: '',
    chatbotKey: ''
  });

  useEffect(() => {
    // Get client credentials from localStorage or sessionStorage
    const clientId = localStorage.getItem('clientId') || sessionStorage.getItem('clientId');
    const chatbotKey = localStorage.getItem('chatbotKey') || sessionStorage.getItem('chatbotKey');
    
    console.log('Domain component - stored credentials:', { clientId, chatbotKey }); // Debug log
    
    if (clientId && chatbotKey) {
      setClientCredentials({ clientId, chatbotKey });
      fetchClientDomains(clientId, chatbotKey);
    } else {
      setMessage({ 
        type: 'error', 
        text: 'Please login first to manage your domains.' 
      });
      setIsLoading(false);
    }
  }, []);

  const fetchClientDomains = async (clientId, chatbotKey) => {
    try {
      const response = await fetch(`http://localhost:8000/client/${clientId}/domains`, {
        headers: { 'x-chatbot-key': chatbotKey }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDomains(data.domains || []);
      } else {
        throw new Error('Failed to fetch domains');
      }
    } catch (error) {
      console.error('Failed to fetch domains:', error);
      setMessage({ type: 'error', text: 'Failed to load your domains.' });
    } finally {
      setIsLoading(false);
    }
  };

  const addDomain = async () => {
    if (!newDomain.trim()) return;

    setIsAdding(true);
    try {
      const response = await fetch(`http://localhost:8000/client/register-my-domains/${clientCredentials.clientId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-chatbot-key': clientCredentials.chatbotKey
        },
        body: JSON.stringify([newDomain.trim()])
      });

      const data = await response.json();
      
      if (response.ok && data.success) {
        setMessage({ type: 'success', text: `Domain "${data.registered_domains[0]}" registered successfully!` });
        setNewDomain('');
        fetchClientDomains(clientCredentials.clientId, clientCredentials.chatbotKey);
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to register domain' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setIsAdding(false);
    }

    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setMessage({ type: 'success', text: 'Copied to clipboard!' });
    setTimeout(() => setMessage({ type: '', text: '' }), 2000);
  };

  const integrationCode = `<!-- Add this to your website's HTML -->
<div id="chatbot-container"></div>
<script>
  // Create chatbot iframe
  const iframe = document.createElement('iframe');
  iframe.src = 'http://localhost:3000/chatbot'; // Your chatbot URL
  iframe.style.cssText = 'position:fixed;bottom:20px;right:20px;width:400px;height:600px;border:none;z-index:1000;';
  document.body.appendChild(iframe);
</script>`;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">Loading your domains...</div>
      </div>
    );
  }

  if (!clientCredentials.clientId) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-800">Please login first to manage your domains.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Globe className="w-6 h-6 text-blue-600" />
              <div>
                <h2 className="text-xl font-semibold text-gray-900">My Domains</h2>
                <p className="text-sm text-gray-600">Manage domains where your chatbot will appear</p>
              </div>
            </div>
            <button
              onClick={() => setShowIntegrationCode(!showIntegrationCode)}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Integration Code
            </button>
          </div>
        </div>

        {/* Status Message */}
        {message.text && (
          <div className={`mx-6 mt-4 p-3 rounded-lg flex items-center gap-2 ${
            message.type === 'success' 
              ? 'bg-green-50 text-green-800 border border-green-200' 
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {message.type === 'success' ? (
              <Check className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            {message.text}
          </div>
        )}

        {/* Integration Code Section */}
        {showIntegrationCode && (
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-3">Integration Code</h3>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">Add this to your website</label>
                <button
                  onClick={() => copyToClipboard(integrationCode)}
                  className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                >
                  <Copy className="w-3 h-3" />
                  Copy
                </button>
              </div>
              <pre className="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto">
                {integrationCode}
              </pre>
            </div>
          </div>
        )}

        {/* Add Domain Section */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Add New Domain</h3>
          <div className="flex gap-3">
            <div className="flex-1">
              <input
                type="text"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="yourdomain.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyPress={(e) => e.key === 'Enter' && addDomain()}
              />
              <p className="text-xs text-gray-500 mt-1">
                Enter your domain without http:// or www. (e.g., yourdomain.com)
              </p>
            </div>
            <button
              onClick={addDomain}
              disabled={!newDomain.trim() || isAdding}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isAdding ? (
                'Adding...'
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Add Domain
                </>
              )}
            </button>
          </div>
        </div>

        {/* Domains List */}
        <div className="px-6 py-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Registered Domains</h3>
          
          {domains.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Globe className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-lg font-medium">No domains registered yet</p>
              <p className="text-sm">Add your first domain to enable automatic chatbot integration</p>
            </div>
          ) : (
            <div className="space-y-3">
              {domains.map((domain, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <Globe className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">{domain.domain}</h4>
                      <p className="text-sm text-gray-500">
                        Registered on {new Date(domain.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                    <Check className="w-3 h-3" />
                    Active
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="px-6 py-4 bg-blue-50 border-t border-gray-200">
          <h4 className="font-medium text-blue-900 mb-2">📋 How it works:</h4>
          <ol className="text-sm text-blue-800 space-y-1">
            <li>1. Add your website domain above</li>
            <li>2. Copy the integration code and add it to your website</li>
            <li>3. The chatbot will automatically appear on your domain</li>
            <li>4. Visitors will see your personalized chatbot assistant</li>
          </ol>
        </div>

        {/* Client Info */}
        <div className="px-6 py-3 bg-gray-100 border-t border-gray-200 text-xs text-gray-600">
          <strong>Client ID:</strong> {clientCredentials.clientId} | 
          <strong> API Key:</strong> {clientCredentials.chatbotKey?.slice(0, 8)}...
        </div>
      </div>
    </div>
  );
};

export default Domain;
