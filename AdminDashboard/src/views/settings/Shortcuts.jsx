import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Table, Button, Form, Modal, Alert, Spinner } from 'react-bootstrap';
import axios from 'axios';
import { API_URL } from '../../config';

const Shortcuts = () => {
  const [shortcuts, setShortcuts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newShortcut, setNewShortcut] = useState({ action_type: '', command: '', message: '' });
  const [showDeleteSelectedAlert, setShowDeleteSelectedAlert] = useState(false);
  const [exportMessage, setExportMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');

  // Fetch shortcuts from backend
  const fetchShortcuts = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/shortcuts/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      setShortcuts(response.data);
      setError('');
    } catch (err) {
      console.error('Failed to fetch shortcuts:', err);
      setError('Failed to load shortcuts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShortcuts();
  }, []);

  // Handle individual checkbox selection
  const handleCheckboxChange = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  // Handle "Select All" checkbox
  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedIds([]);
    } else {
      setSelectedIds(shortcuts.map(shortcut => shortcut.id));
    }
    setSelectAll(!selectAll);
  };

  // Add new shortcut
  const handleAddShortcut = async () => {
    if (!newShortcut.action_type || !newShortcut.command || !newShortcut.message) {
      setError('Please fill in all fields');
      return;
    }

    try {
      setSaving(true);
      await axios.post(
        `${API_URL}/shortcuts/`,
        {
          action_type: newShortcut.action_type,
          command: newShortcut.command,
          message: newShortcut.message
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      setNewShortcut({ action_type: '', command: '', message: '' });
      setShowAddModal(false);
      setExportMessage(`✅ Shortcut /${newShortcut.command} created successfully`);
      setTimeout(() => setExportMessage(''), 3000);

      // Refresh list
      await fetchShortcuts();
    } catch (err) {
      console.error('Failed to create shortcut:', err);
      setError(err.response?.data?.detail || 'Failed to create shortcut');
    } finally {
      setSaving(false);
    }
  };

  // Delete single shortcut
  const handleDeleteShortcut = async (id) => {
    if (!window.confirm('Are you sure you want to delete this shortcut?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/shortcuts/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      setExportMessage('✅ Shortcut deleted successfully');
      setTimeout(() => setExportMessage(''), 3000);

      // Refresh list
      await fetchShortcuts();

      // Remove from selected if it was selected
      setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
    } catch (err) {
      console.error('Failed to delete shortcut:', err);
      setError('Failed to delete shortcut');
    }
  };

  // Delete selected shortcuts
  const handleDeleteSelected = async () => {
    try {
      await axios.post(
        `${API_URL}/shortcuts/bulk-delete`,
        selectedIds,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      setExportMessage(`✅ Deleted ${selectedIds.length} shortcuts successfully`);
      setTimeout(() => setExportMessage(''), 3000);

      setSelectedIds([]);
      setSelectAll(false);
      setShowDeleteSelectedAlert(false);

      // Refresh list
      await fetchShortcuts();
    } catch (err) {
      console.error('Failed to delete shortcuts:', err);
      setError('Failed to delete shortcuts');
    }
  };

  // Get selected count
  const selectedCount = selectedIds.length;

  // Export to CSV function
  const handleExportCSV = () => {
    if (shortcuts.length === 0) {
      setExportMessage('No shortcuts to export');
      setTimeout(() => setExportMessage(''), 3000);
      return;
    }

    const shortcutsToExport = selectedCount > 0
      ? shortcuts.filter(shortcut => selectedIds.includes(shortcut.id))
      : shortcuts;

    const headers = ['ID', 'Action Type', 'Command', 'Message', 'Created At'];

    const csvRows = [
      headers.join(','),
      ...shortcutsToExport.map(shortcut => [
        shortcut.id,
        `"${shortcut.action_type}"`,
        `"/${shortcut.command}"`,
        `"${shortcut.message.replace(/"/g, '""')}"`,
        `"${new Date(shortcut.created_at).toLocaleString()}"`
      ].join(','))
    ];

    const csvString = csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
    const filename = selectedCount > 0
      ? `shortcuts-selected-${timestamp}.csv`
      : `shortcuts-all-${timestamp}.csv`;

    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    const exportedCount = shortcutsToExport.length;
    setExportMessage(`📥 Exported ${exportedCount} shortcut${exportedCount !== 1 ? 's' : ''} to ${filename}`);
    setTimeout(() => setExportMessage(''), 3000);
  };

  if (loading) {
    return (
      <Container fluid className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="text-center">
          <Spinner animation="border" variant="primary" />
          <p className="mt-3">Loading shortcuts...</p>
        </div>
      </Container>
    );
  }

  return (
    <Container fluid>
      <Row className="align-items-center mb-4">
        <Col>
          <h4 className="mb-0">⚡ Shortcuts</h4>
          <p className="text-muted mb-0">Quick responses for faster admin replies • Use /command in admin chat</p>
        </Col>
        <Col className="text-end">
          <Button variant="primary" onClick={() => setShowAddModal(true)} className="me-2">
            <i className="ph ph-plus me-2"></i>Add Shortcut
          </Button>

          {selectedCount > 0 && (
            <Button
              variant="danger"
              onClick={() => setShowDeleteSelectedAlert(true)}
              className="me-2"
            >
              <i className="ph ph-trash me-2"></i>Delete Selected ({selectedCount})
            </Button>
          )}

          <Button
            variant="outline-secondary"
            onClick={handleExportCSV}
            disabled={shortcuts.length === 0}
          >
            <i className="ph ph-download me-2"></i>
            Export CSV
            {selectedCount > 0 && ` (${selectedCount})`}
          </Button>
        </Col>
      </Row>

      {exportMessage && (
        <Row className="mb-3">
          <Col>
            <Alert
              variant="success"
              className="py-2"
              onClose={() => setExportMessage('')}
              dismissible
            >
              {exportMessage}
            </Alert>
          </Col>
        </Row>
      )}

      {error && (
        <Row className="mb-3">
          <Col>
            <Alert
              variant="danger"
              className="py-2"
              onClose={() => setError('')}
              dismissible
            >
              <i className="ph ph-warning me-2"></i>
              {error}
            </Alert>
          </Col>
        </Row>
      )}

      {selectedCount > 0 && (
        <Row className="mb-3">
          <Col>
            <Alert variant="info" className="py-2">
              <div className="d-flex justify-content-between align-items-center">
                <span>
                  <i className="ph ph-info me-2"></i>
                  {selectedCount} shortcut{selectedCount !== 1 ? 's' : ''} selected
                </span>
                <Button
                  variant="outline-info"
                  size="sm"
                  onClick={() => {
                    setSelectedIds([]);
                    setSelectAll(false);
                  }}
                >
                  Clear Selection
                </Button>
              </div>
            </Alert>
          </Col>
        </Row>
      )}

      <Row>
        <Col>
          <Card>
            <Card.Body>
              {shortcuts.length > 0 ? (
                <Table responsive hover>
                  <thead>
                    <tr>
                      <th width="5%" className="text-center">
                        <Form.Check
                          type="checkbox"
                          checked={selectAll && shortcuts.length > 0}
                          onChange={handleSelectAll}
                          disabled={shortcuts.length === 0}
                        />
                      </th>
                      <th width="15%">Action Type</th>
                      <th width="20%">Command</th>
                      <th width="45%">Message</th>
                      <th width="15%" className="text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shortcuts.map((shortcut) => (
                      <tr key={shortcut.id}>
                        <td className="text-center">
                          <Form.Check
                            type="checkbox"
                            checked={selectedIds.includes(shortcut.id)}
                            onChange={() => handleCheckboxChange(shortcut.id)}
                          />
                        </td>
                        <td>
                          <code className="bg-light p-2 rounded d-block text-center">
                            {shortcut.action_type}
                          </code>
                        </td>
                        <td className="fw-medium">
                          <code className="text-primary">/{shortcut.command}</code>
                        </td>
                        <td>
                          <div className="text-truncate" style={{ maxWidth: '500px' }}>
                            {shortcut.message}
                          </div>
                        </td>
                        <td className="text-center">
                          <Button
                            variant="outline-danger"
                            size="sm"
                            onClick={() => handleDeleteShortcut(shortcut.id)}
                            title="Delete this shortcut"
                          >
                            <i className="ph ph-trash"></i>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <div className="text-center py-5">
                  <div className="mb-3">
                    <i className="ph ph-keyboard" style={{ fontSize: '3rem', color: '#6c757d' }}></i>
                  </div>
                  <h5>No shortcuts yet</h5>
                  <p className="text-muted mb-3">Create shortcuts to send quick responses in admin chat</p>
                  <Button variant="primary" onClick={() => setShowAddModal(true)}>
                    <i className="ph ph-plus me-2"></i>Add Your First Shortcut
                  </Button>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Add Shortcut Modal */}
      <Modal show={showAddModal} onHide={() => setShowAddModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>⚡ Add New Shortcut</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Action Type</Form.Label>
              <Form.Select
                value={newShortcut.action_type}
                onChange={(e) => setNewShortcut({...newShortcut, action_type: e.target.value})}
              >
                <option value="">Select action type</option>
                <option value="Public">Public</option>
                <option value="Personal">Personal</option>
                <option value="Admin">Admin</option>
                <option value="System">System</option>
              </Form.Select>
              <Form.Text className="text-muted">
                Choose the category for this shortcut
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Command</Form.Label>
              <div className="input-group">
                <span className="input-group-text">/</span>
                <Form.Control
                  type="text"
                  placeholder="hello, refund, support..."
                  value={newShortcut.command}
                  onChange={(e) => setNewShortcut({...newShortcut, command: e.target.value.toLowerCase()})}
                />
              </div>
              <Form.Text className="text-muted">
                Type this in admin chat to use the shortcut (e.g., /hello)
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Message Content</Form.Label>
              <Form.Control
                as="textarea"
                rows={4}
                placeholder="Hello! Thank you for contacting us. How can I help you today?"
                value={newShortcut.message}
                onChange={(e) => setNewShortcut({...newShortcut, message: e.target.value})}
              />
              <Form.Text className="text-muted">
                This message will be sent when you type /{newShortcut.command || 'command'}
              </Form.Text>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowAddModal(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleAddShortcut}
            disabled={saving || !newShortcut.action_type || !newShortcut.command || !newShortcut.message}
          >
            {saving ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Creating...
              </>
            ) : (
              <>
                <i className="ph ph-check me-2"></i>
                Create Shortcut
              </>
            )}
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Delete Selected Confirmation Modal */}
      <Modal show={showDeleteSelectedAlert} onHide={() => setShowDeleteSelectedAlert(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Delete Selected Shortcuts</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Alert variant="warning">
            <i className="ph ph-warning me-2"></i>
            Are you sure you want to delete {selectedCount} selected shortcut{selectedCount !== 1 ? 's' : ''}?
            <br />
            <strong>This action cannot be undone.</strong>
          </Alert>
          <div className="mt-3">
            <h6>Shortcuts to be deleted:</h6>
            <ul className="list-unstyled">
              {shortcuts
                .filter(shortcut => selectedIds.includes(shortcut.id))
                .slice(0, 5)
                .map(shortcut => (
                  <li key={shortcut.id} className="mb-1">
                    <code className="text-primary">/{shortcut.command}</code> - {shortcut.message.substring(0, 50)}...
                  </li>
                ))}
              {selectedCount > 5 && (
                <li>...and {selectedCount - 5} more</li>
              )}
            </ul>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDeleteSelectedAlert(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDeleteSelected}>
            <i className="ph ph-trash me-2"></i>
            Delete {selectedCount} Shortcut{selectedCount !== 1 ? 's' : ''}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default Shortcuts;
