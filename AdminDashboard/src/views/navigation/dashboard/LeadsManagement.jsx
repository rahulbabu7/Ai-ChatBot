import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import 'assets/scss/style.scss';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';

const LeadsManagement = () => {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState('all'); // 'all', 'today', 'week', 'month'
  
  // Update lead state
  const [updateStatus, setUpdateStatus] = useState('');
  const [updateNotes, setUpdateNotes] = useState('');

  useEffect(() => {
    if (token) {
      fetchLeads();
      fetchStats();
    }
  }, [token, statusFilter]);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const url = statusFilter 
        ? `${API_URL}/leads/me?status=${statusFilter}&limit=200`
        : `${API_URL}/leads/me?limit=200`;
      
      const res = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads || []);
      } else {
        console.error('Failed to fetch leads');
      }
    } catch (e) {
      console.error('Error fetching leads:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/leads/stats/me`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Error fetching stats:', e);
    }
  };

  const handleStatusUpdate = async (leadId) => {
    if (!updateStatus) {
      alert('Please select a status');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/leads/${leadId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          status: updateStatus,
          notes: updateNotes || null
        })
      });

      if (res.ok) {
        alert('Lead status updated successfully!');
        setShowDetailsModal(false);
        fetchLeads();
        fetchStats();
        setUpdateStatus('');
        setUpdateNotes('');
      } else {
        alert('Failed to update lead status');
      }
    } catch (e) {
      console.error('Error updating lead:', e);
      alert('Error updating lead status');
    }
  };

  const viewLeadDetails = (lead) => {
    setSelectedLead(lead);
    setUpdateStatus(lead.status);
    setUpdateNotes(lead.notes || '');
    setShowDetailsModal(true);
  };

  const getStatusBadge = (status) => {
    const colors = {
      new: 'primary',
      contacted: 'info',
      converted: 'success',
      closed: 'secondary'
    };
    return colors[status] || 'secondary';
  };

  const getFormTypeBadge = (formType) => {
    const types = {
      contact: { label: 'Contact', color: 'info' },
      demo_booking: { label: 'Demo', color: 'warning' }
    };
    const type = types[formType] || { label: formType, color: 'secondary' };
    return type;
  };

  const filterLeadsByDate = (leads) => {
    if (dateFilter === 'all') return leads;

    const now = new Date();
    const filtered = leads.filter(lead => {
      const leadDate = new Date(lead.created_at);
      
      switch (dateFilter) {
        case 'today':
          return leadDate.toDateString() === now.toDateString();
        case 'week':
          const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          return leadDate >= weekAgo;
        case 'month':
          const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          return leadDate >= monthAgo;
        default:
          return true;
      }
    });

    return filtered;
  };

  const filterLeadsBySearch = (leads) => {
    if (!searchTerm) return leads;

    const term = searchTerm.toLowerCase();
    return leads.filter(lead => 
      lead.name?.toLowerCase().includes(term) ||
      lead.email?.toLowerCase().includes(term) ||
      lead.phone?.toLowerCase().includes(term) ||
      lead.company?.toLowerCase().includes(term) ||
      lead.message?.toLowerCase().includes(term)
    );
  };

  const filteredLeads = filterLeadsBySearch(filterLeadsByDate(leads));

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'Email', 'Phone', 'Company', 'Status', 'Form Type', 'Message', 'Created At'];
    const rows = filteredLeads.map(lead => [
      lead.id,
      lead.name || '',
      lead.email || '',
      lead.phone || '',
      lead.company || '',
      lead.status,
      lead.form_type,
      lead.message || '',
      lead.created_at
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `leads_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="container-fluid mt-4">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>📋 Lead Management</h2>
        <div className="d-flex gap-2">
          <button className="btn btn-success" onClick={exportToCSV} disabled={filteredLeads.length === 0}>
            📥 Export CSV
          </button>
          <button className="btn btn-outline-primary" onClick={() => { fetchLeads(); fetchStats(); }}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="row mb-4">
          <div className="col-md-3">
            <div className="card bg-primary text-white">
              <div className="card-body">
                <h3>{stats.total_leads || 0}</h3>
                <p className="mb-0">Total Leads</p>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card bg-info text-white">
              <div className="card-body">
                <h3>{stats.leads_by_status?.new || 0}</h3>
                <p className="mb-0">New Leads</p>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card bg-warning text-white">
              <div className="card-body">
                <h3>{stats.leads_by_status?.contacted || 0}</h3>
                <p className="mb-0">Contacted</p>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card bg-success text-white">
              <div className="card-body">
                <h3>{stats.leads_by_status?.converted || 0}</h3>
                <p className="mb-0">Converted</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card mb-4">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-3">
              <label className="form-label">Status Filter</label>
              <select 
                className="form-select" 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="converted">Converted</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div className="col-md-3">
              <label className="form-label">Date Filter</label>
              <select 
                className="form-select" 
                value={dateFilter} 
                onChange={(e) => setDateFilter(e.target.value)}
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="week">Last 7 Days</option>
                <option value="month">Last 30 Days</option>
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Search</label>
              <input
                type="text"
                className="form-control"
                placeholder="Search by name, email, phone, company..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="card">
        <div className="card-body">
          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2">Loading leads...</p>
            </div>
          ) : filteredLeads.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <h4>No leads found</h4>
              <p>Try adjusting your filters or wait for new leads to come in.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Company</th>
                    <th>Form Type</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.map(lead => (
                    <tr key={lead.id}>
                      <td>#{lead.id}</td>
                      <td>
                        <strong>{lead.name || 'N/A'}</strong>
                      </td>
                      <td>
                        {lead.email ? (
                          <a href={`mailto:${lead.email}`}>{lead.email}</a>
                        ) : 'N/A'}
                      </td>
                      <td>
                        {lead.phone ? (
                          <a href={`tel:${lead.phone}`}>{lead.phone}</a>
                        ) : 'N/A'}
                      </td>
                      <td>{lead.company || 'N/A'}</td>
                      <td>
                        <span className={`badge bg-${getFormTypeBadge(lead.form_type).color}`}>
                          {getFormTypeBadge(lead.form_type).label}
                        </span>
                      </td>
                      <td>
                        <span className={`badge bg-${getStatusBadge(lead.status)}`}>
                          {lead.status}
                        </span>
                      </td>
                      <td>
                        <small>{formatDate(lead.created_at)}</small>
                      </td>
                      <td>
                        <button 
                          className="btn btn-sm btn-outline-primary"
                          onClick={() => viewLeadDetails(lead)}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          {/* Summary */}
          {filteredLeads.length > 0 && (
            <div className="text-muted mt-3">
              Showing {filteredLeads.length} of {leads.length} leads
            </div>
          )}
        </div>
      </div>

      {/* Lead Details Modal */}
      {showDetailsModal && selectedLead && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Lead Details - #{selectedLead.id}</h5>
                <button className="btn-close" onClick={() => setShowDetailsModal(false)}></button>
              </div>
              <div className="modal-body">
                {/* Contact Information */}
                <div className="row mb-4">
                  <div className="col-md-6">
                    <h6 className="border-bottom pb-2">Contact Information</h6>
                    <dl className="row">
                      <dt className="col-sm-4">Name:</dt>
                      <dd className="col-sm-8">{selectedLead.name || 'N/A'}</dd>
                      
                      <dt className="col-sm-4">Email:</dt>
                      <dd className="col-sm-8">
                        {selectedLead.email ? (
                          <a href={`mailto:${selectedLead.email}`}>{selectedLead.email}</a>
                        ) : 'N/A'}
                      </dd>
                      
                      <dt className="col-sm-4">Phone:</dt>
                      <dd className="col-sm-8">
                        {selectedLead.phone ? (
                          <a href={`tel:${selectedLead.phone}`}>{selectedLead.phone}</a>
                        ) : 'N/A'}
                      </dd>
                      
                      <dt className="col-sm-4">Company:</dt>
                      <dd className="col-sm-8">{selectedLead.company || 'N/A'}</dd>
                    </dl>
                  </div>

                  <div className="col-md-6">
                    <h6 className="border-bottom pb-2">Lead Information</h6>
                    <dl className="row">
                      <dt className="col-sm-5">Form Type:</dt>
                      <dd className="col-sm-7">
                        <span className={`badge bg-${getFormTypeBadge(selectedLead.form_type).color}`}>
                          {getFormTypeBadge(selectedLead.form_type).label}
                        </span>
                      </dd>
                      
                      <dt className="col-sm-5">Status:</dt>
                      <dd className="col-sm-7">
                        <span className={`badge bg-${getStatusBadge(selectedLead.status)}`}>
                          {selectedLead.status}
                        </span>
                      </dd>
                      
                      <dt className="col-sm-5">Preferred Time:</dt>
                      <dd className="col-sm-7">{selectedLead.preferred_time || 'N/A'}</dd>
                      
                      <dt className="col-sm-5">Country:</dt>
                      <dd className="col-sm-7">{selectedLead.country_code || 'Unknown'}</dd>
                      
                      <dt className="col-sm-5">Session ID:</dt>
                      <dd className="col-sm-7">
                        <small className="text-muted">{selectedLead.session_id}</small>
                      </dd>
                    </dl>
                  </div>
                </div>

                {/* Message */}
                {selectedLead.message && (
                  <div className="mb-4">
                    <h6 className="border-bottom pb-2">Message</h6>
                    <div className="bg-light p-3 rounded">
                      {selectedLead.message}
                    </div>
                  </div>
                )}

                {/* Timestamps */}
                <div className="row mb-4">
                  <div className="col-md-6">
                    <small className="text-muted">
                      <strong>Created:</strong> {formatDate(selectedLead.created_at)}
                    </small>
                  </div>
                  <div className="col-md-6">
                    <small className="text-muted">
                      <strong>Last Updated:</strong> {formatDate(selectedLead.updated_at)}
                    </small>
                  </div>
                  {selectedLead.contacted_at && (
                    <div className="col-md-12 mt-2">
                      <small className="text-muted">
                        <strong>Contacted At:</strong> {formatDate(selectedLead.contacted_at)}
                      </small>
                    </div>
                  )}
                </div>

                {/* Existing Notes */}
                {selectedLead.notes && (
                  <div className="mb-4">
                    <h6 className="border-bottom pb-2">Previous Notes</h6>
                    <div className="bg-light p-3 rounded">
                      {selectedLead.notes}
                    </div>
                  </div>
                )}

                {/* Update Status Section */}
                <div className="border-top pt-4">
                  <h6 className="mb-3">Update Lead Status</h6>
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label">Status</label>
                      <select 
                        className="form-select"
                        value={updateStatus}
                        onChange={(e) => setUpdateStatus(e.target.value)}
                      >
                        <option value="new">New</option>
                        <option value="contacted">Contacted</option>
                        <option value="converted">Converted</option>
                        <option value="closed">Closed</option>
                      </select>
                    </div>
                    <div className="col-md-12">
                      <label className="form-label">Notes (optional)</label>
                      <textarea
                        className="form-control"
                        rows="3"
                        value={updateNotes}
                        onChange={(e) => setUpdateNotes(e.target.value)}
                        placeholder="Add notes about this lead..."
                      ></textarea>
                    </div>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setShowDetailsModal(false)}>
                  Close
                </button>
                <button 
                  className="btn btn-primary" 
                  onClick={() => handleStatusUpdate(selectedLead.id)}
                >
                  💾 Update Status
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadsManagement;