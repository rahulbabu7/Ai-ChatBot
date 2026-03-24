import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';
import { useDarkMode } from '../../../hooks/useDarkMode';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Badge from 'react-bootstrap/Badge';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Modal from 'react-bootstrap/Modal';
import Form from 'react-bootstrap/Form';

const PLAN_COLORS = { trial: 'warning', paid: 'success', cancelled: 'danger' };

export default function SuperAdminDashboard() {
  const { token } = useAuth();
  const [isDark] = useDarkMode();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Plan modal state
  const [planModal, setPlanModal] = useState(false);
  const [selected, setSelected] = useState(null);
  const [planValue, setPlanValue] = useState('trial');
  const [expiryDays, setExpiryDays] = useState('');
  const [saving, setSaving] = useState(false);

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const fetchClients = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/superadmin/clients`, authHeaders);
      setClients(res.data.clients || []);
    } catch (err) {
      console.error('Failed to fetch clients:', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) fetchClients();
  }, [token, fetchClients]);

  const toggleChatbot = async (clientId, currentState) => {
    try {
      const res = await axios.patch(`${API_URL}/superadmin/client/${clientId}/toggle`, {}, authHeaders);
      setClients((prev) =>
        prev.map((c) => (c.client_id === clientId ? { ...c, chatbot_enabled: res.data.chatbot_enabled } : c))
      );
    } catch (err) {
      alert('Failed to toggle chatbot: ' + (err.response?.data?.detail || err.message));
    }
  };

  const openPlanModal = (client) => {
    setSelected(client);
    setPlanValue(client.plan);
    setExpiryDays('');
    setPlanModal(true);
  };

  const savePlan = async () => {
    setSaving(true);
    try {
      const payload = {
        plan: planValue,
        expires_days: expiryDays ? parseInt(expiryDays) : null,
      };
      const res = await axios.patch(`${API_URL}/superadmin/client/${selected.client_id}/plan`, payload, authHeaders);
      setClients((prev) =>
        prev.map((c) =>
          c.client_id === selected.client_id
            ? { ...c, plan: res.data.plan, chatbot_enabled: res.data.chatbot_enabled, plan_expires_at: res.data.plan_expires_at }
            : c
        )
      );
      setPlanModal(false);
    } catch (err) {
      alert('Failed to update plan: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const filtered = clients.filter(
    (c) =>
      c.name?.toLowerCase().includes(search.toLowerCase()) ||
      c.email?.toLowerCase().includes(search.toLowerCase()) ||
      c.client_id?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: clients.length,
    paid: clients.filter((c) => c.plan === 'paid').length,
    trial: clients.filter((c) => c.plan === 'trial').length,
    cancelled: clients.filter((c) => c.plan === 'cancelled').length,
    disabled: clients.filter((c) => !c.chatbot_enabled).length,
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" />
        <p className="mt-2 text-muted">Loading clients...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h4 className="mb-0">Superadmin — Client Management</h4>
        <Button variant="outline-secondary" size="sm" onClick={fetchClients}>
          Refresh
        </Button>
      </div>

      {/* Summary cards */}
      <Row className="g-3 mb-4">
        {[
          { label: 'Total Clients', value: stats.total, color: 'info' },
          { label: 'Paid', value: stats.paid, color: 'success' },
          { label: 'Trial', value: stats.trial, color: 'warning' },
          { label: 'Cancelled', value: stats.cancelled, color: 'danger' },
          { label: 'Disabled', value: stats.disabled, color: 'secondary' },
        ].map((s) => (
          <Col key={s.label} xs={6} sm={4} md={2}>
            <Card className={`text-center border-0 bg-${s.color} bg-opacity-15 shadow-sm`}>
              <Card.Body className="py-3">
                <h5 className={`fw-bold mb-0 ${isDark ? 'text-light' : ''}`}>{s.value}</h5>
                <small className="text-muted">{s.label}</small>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Search */}
      <div className="mb-3">
        <Form.Control
          placeholder="Search by name, email or client ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <Card className="shadow-sm">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className={isDark ? 'table-dark' : 'table-light'}>
              <tr>
                <th>Client</th>
                <th>Plan</th>
                <th>Expires</th>
                <th>Chatbot</th>
                <th>Chats</th>
                <th>Leads</th>
                <th>Last Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center text-muted py-4">
                    No clients found
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.client_id}>
                    <td>
                      <div className={`fw-semibold ${isDark ? 'text-light' : ''}`}>{c.name}</div>
                      <small className="text-muted">{c.email}</small>
                    </td>
                    <td>
                      <Badge bg={PLAN_COLORS[c.plan] || 'secondary'}>{c.plan}</Badge>
                    </td>
                    <td>
                      {c.plan_expires_at ? (
                        <small className={new Date(c.plan_expires_at) < new Date() ? 'text-danger' : 'text-muted'}>
                          {new Date(c.plan_expires_at).toLocaleDateString('en-IN')}
                        </small>
                      ) : (
                        <small className="text-muted">—</small>
                      )}
                    </td>
                    <td>
                      <Badge bg={c.chatbot_enabled ? 'success' : 'secondary'}>
                        {c.chatbot_enabled ? 'ON' : 'OFF'}
                      </Badge>
                    </td>
                    <td className={isDark ? 'text-light' : ''}>{c.total_chats.toLocaleString()}</td>
                    <td className={isDark ? 'text-light' : ''}>{c.total_leads}</td>
                    <td>
                      <small className="text-muted">
                        {c.last_active ? new Date(c.last_active).toLocaleDateString('en-IN') : '—'}
                      </small>
                    </td>
                    <td>
                      <div className="d-flex gap-2">
                        <Button
                          size="sm"
                          variant={c.chatbot_enabled ? 'outline-danger' : 'outline-success'}
                          onClick={() => toggleChatbot(c.client_id, c.chatbot_enabled)}
                        >
                          {c.chatbot_enabled ? 'Disable' : 'Enable'}
                        </Button>
                        <Button size="sm" variant="outline-primary" onClick={() => openPlanModal(c)}>
                          Plan
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Plan Modal */}
      <Modal show={planModal} onHide={() => setPlanModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Update Plan — {selected?.name}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label>Plan</Form.Label>
            <Form.Select value={planValue} onChange={(e) => setPlanValue(e.target.value)}>
              <option value="trial">Trial</option>
              <option value="paid">Paid</option>
              <option value="cancelled">Cancelled</option>
            </Form.Select>
            {planValue === 'cancelled' && (
              <Form.Text className="text-danger">Chatbot will be disabled immediately.</Form.Text>
            )}
          </Form.Group>
          <Form.Group>
            <Form.Label>Expires in (days) <span className="text-muted fw-normal">— leave blank for no expiry</span></Form.Label>
            <Form.Control
              type="number"
              min={1}
              placeholder="e.g. 30"
              value={expiryDays}
              onChange={(e) => setExpiryDays(e.target.value)}
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setPlanModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={savePlan} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}
