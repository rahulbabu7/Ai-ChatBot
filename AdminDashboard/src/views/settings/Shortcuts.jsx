import React, { useState } from 'react';
import { Container, Row, Col, Card, Table, Button, Form, Modal, Alert } from 'react-bootstrap';

const Shortcuts = () => {
  // Start with an empty shortcuts array
  const [shortcuts, setShortcuts] = useState([ 
    { id: 1, key: 'Public', action: 'hello', description: 'Hello! How can I help you today?' },
    { id: 2, key: 'Personal', action: 'thanks', description: 'Thank you for your message!' },
  ]);

  // State for selected shortcuts
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newShortcut, setNewShortcut] = useState({ key: '', action: '', description: '' });
  const [showDeleteSelectedAlert, setShowDeleteSelectedAlert] = useState(false);
  const [exportMessage, setExportMessage] = useState('');

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
  const handleAddShortcut = () => {
    if (newShortcut.key && newShortcut.action) {
      const newId = shortcuts.length > 0 ? Math.max(...shortcuts.map(s => s.id)) + 1 : 1;
      setShortcuts([...shortcuts, { 
        id: newId, 
        ...newShortcut 
      }]);
      setNewShortcut({ key: '', action: '', description: '' });
      setShowAddModal(false);
    }
  };

  // Delete single shortcut
  const handleDeleteShortcut = (id) => {
    setShortcuts(shortcuts.filter(shortcut => shortcut.id !== id));
    // Remove from selected if it was selected
    setSelectedIds(selectedIds.filter(selectedId => selectedId !== id));
  };

  // Delete selected shortcuts
  const handleDeleteSelected = () => {
    setShortcuts(shortcuts.filter(shortcut => !selectedIds.includes(shortcut.id)));
    setSelectedIds([]);
    setSelectAll(false);
    setShowDeleteSelectedAlert(false);
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

    // Determine which shortcuts to export
    const shortcutsToExport = selectedCount > 0 
      ? shortcuts.filter(shortcut => selectedIds.includes(shortcut.id))
      : shortcuts;

    // CSV headers
    const headers = ['ID', 'Action Type', 'Shortcut Command', 'Message'];
    
    // Convert shortcuts to CSV rows
    const csvRows = [
      headers.join(','), // Header row
      ...shortcutsToExport.map(shortcut => [
        shortcut.id,
        `"${shortcut.key}"`,
        `"${shortcut.action}"`,
        `"${shortcut.description.replace(/"/g, '""')}"` // Escape quotes in description
      ].join(','))
    ];

    // Create CSV string
    const csvString = csvRows.join('\n');
    
    // Create blob and download link
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // Create filename with timestamp
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

    // Show success message
    const exportedCount = shortcutsToExport.length;
    setExportMessage(`Exported ${exportedCount} shortcut${exportedCount !== 1 ? 's' : ''} to ${filename}`);
    setTimeout(() => setExportMessage(''), 3000);
  };

  return (
    <Container fluid>
      <Row className="align-items-center mb-4">
        <Col>
          <h4 className="mb-0">Shortcuts</h4>
          <p className="text-muted mb-0">Manage shortcuts for faster response</p>
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
              <i className="ph ph-check-circle me-2"></i>
              {exportMessage}
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
                  {selectedCount > 0 && ' - will be exported if you click Export CSV'}
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
                      <th width="15%">Action</th>
                      <th width="20%">Shortcut</th>
                      <th width="45%">Message</th>
                      <th width="15%" className="text-center">Delete</th>
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
                            {shortcut.key}
                          </code>
                        </td>
                        <td className="fw-medium">{shortcut.action}</td>
                        <td>
                          <div className="text-truncate" style={{ maxWidth: '500px' }}>
                            {shortcut.description}
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
                  <p className="text-muted">Click "Add Shortcut" to create your first shortcut</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Add Shortcut Modal */}
      <Modal show={showAddModal} onHide={() => setShowAddModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Add New Shortcut</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Action Type</Form.Label>
              <Form.Select
                value={newShortcut.key}
                onChange={(e) => setNewShortcut({...newShortcut, key: e.target.value})}
              >
                <option value="">Select action type</option>
                <option value="Public">Public</option>
                <option value="Personal">Personal</option>
                <option value="Admin">Admin</option>
                <option value="System">System</option>
              </Form.Select>
              <Form.Text className="text-muted">
                Choose the action type for this shortcut
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Shortcut Command</Form.Label>
              <Form.Control
                type="text"
                placeholder="e.g., hello, thanks, services"
                value={newShortcut.action}
                onChange={(e) => setNewShortcut({...newShortcut, action: e.target.value})}
              />
              <Form.Text className="text-muted">
                This is the command users will type to trigger the message
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Message Content</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                placeholder="Enter the message that will be sent when this shortcut is used..."
                value={newShortcut.description}
                onChange={(e) => setNewShortcut({...newShortcut, description: e.target.value})}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowAddModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleAddShortcut}>
            Add Shortcut
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
                .slice(0, 5) // Show only first 5 to avoid too long list
                .map(shortcut => (
                  <li key={shortcut.id} className="mb-1">
                    <code>{shortcut.action}</code> - {shortcut.description.substring(0, 50)}...
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
            Delete {selectedCount} Shortcut{selectedCount !== 1 ? 's' : ''}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default Shortcuts;