// ProfileSettings.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert } from 'react-bootstrap';
import { useAuth } from '../../hooks/useAuth';
import { FaEdit, FaSave, FaPen, FaTimes, FaRobot } from 'react-icons/fa';
import { API_URL } from '../../config';
//import { useAuth } from '../../../hooks/useAuth';

const ProfileSettings = () => {
  const { token } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    name: '',
    email: '',
    mobileNumber: '',
    chatbotName: ''
  });

  const [originalData, setOriginalData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [editingField, setEditingField] = useState(null);

  // Track which fields have been modified
  const modifiedFieldsRef = useRef(new Set());

  // Fetch user profile data on component mount
  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        setLoading(true);

        // If user data is available from auth hook, use it
        // Alternatively, fetch from your API
        const response = await fetch(`${API_URL}/client/profile`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const userData = await response.json();
          const initialData = {
            username: userData.username || '',
            name: userData.name || '',
            email: userData.email || '',
            mobileNumber: userData.mobile_number || '',
            chatbotName: userData.chatbot_name || userData.botName || ''
          };

          setFormData(initialData);
          setOriginalData(initialData);
        }
      } catch (err) {
        setError('Failed to load profile data');
        console.error('Error fetching profile:', err);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchUserProfile();
    }
  }, [token]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;

    // Skip if field is username (cannot be edited)
    if (name === 'username') return;

    const newFormData = {
      ...formData,
      [name]: value
    };

    setFormData(newFormData);

    // Check if value has changed from original
    if (value !== originalData[name]) {
      modifiedFieldsRef.current.add(name);
    } else {
      modifiedFieldsRef.current.delete(name);
    }

    // Update hasChanges state
    setHasChanges(modifiedFieldsRef.current.size > 0);
  };

  const handleEditClick = (fieldName) => {
    setEditingField(fieldName);
    // Focus on the input field after a small delay to ensure it's rendered
    setTimeout(() => {
      const input = document.querySelector(`[name="${fieldName}"]`);
      if (input) {
        input.focus();
        input.select();
      }
    }, 10);
  };

  const handleCancelEdit = (fieldName) => {
    // Revert this field to original value
    setFormData({
      ...formData,
      [fieldName]: originalData[fieldName]
    });

    // Remove from modified fields
    modifiedFieldsRef.current.delete(fieldName);
    setHasChanges(modifiedFieldsRef.current.size > 0);

    // Exit edit mode
    setEditingField(null);
  };

  const handleSaveChanges = async () => {
    try {
      setError('');
      setSuccess('');

      // Prepare data with only modified fields
      const modifiedData = {};

      modifiedFieldsRef.current.forEach((field) => {
        if (field === 'mobileNumber') {
          modifiedData.mobile_number = formData.mobileNumber;
        } else if (field === 'chatbotName') {
          modifiedData.chatbot_name = formData.chatbotName;
        } else {
          modifiedData[field] = formData[field];
        }
      });

      // If no changes, show message and return
      if (Object.keys(modifiedData).length === 0) {
        setSuccess('No changes to save');
        setTimeout(() => setSuccess(''), 3000);
        return;
      }

      const response = await fetch(`${API_URL}/client/profile/edit`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(modifiedData)
      });

      if (response.ok) {
        const updatedData = await response.json();

        // Update original data with saved changes
        const newOriginalData = { ...originalData };
        Object.keys(modifiedData).forEach((field) => {
          newOriginalData[field] = formData[field];
        });
        setOriginalData(newOriginalData);

        // Clear modified fields and exit edit mode
        modifiedFieldsRef.current.clear();
        setHasChanges(false);
        setEditingField(null);

        setSuccess('Profile updated successfully!');

        // Clear success message after 3 seconds
        setTimeout(() => {
          setSuccess('');
        }, 3000);
      } else {
        setError('Failed to update profile');
      }
    } catch (err) {
      setError('Error updating profile');
      console.error('Update error:', err);
    }
  };

  const renderEditableField = (label, fieldName, type = 'text', placeholder, icon) => {
    const isUsername = fieldName === 'username';
    const isModified = modifiedFieldsRef.current.has(fieldName);
    const isEditing = editingField === fieldName;

    return (
      <Form.Group className="mb-4">
        <Form.Label className="fw-medium d-flex justify-content-between align-items-center">
          <span className="d-flex align-items-center gap-2">
            {icon}
            {label}
          </span>
          {isModified && !isUsername && <span className="badge bg-warning text-dark">Modified</span>}
        </Form.Label>
        <div className="d-flex align-items-center">
          <Form.Control
            type={type}
            name={fieldName}
            value={formData[fieldName]}
            onChange={handleInputChange}
            placeholder={placeholder}
            disabled={isUsername}
            className={`flex-grow-1 ${isUsername ? 'bg-light' : ''} ${isModified ? 'border-warning' : ''} ${isEditing ? 'border-primary' : ''}`}
          />
          {!isUsername && (
            <div className="ms-2">
              {isEditing ? (
                // Cancel button when editing
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={() => handleCancelEdit(fieldName)}
                  title="Cancel"
                  className="d-flex align-items-center gap-1"
                >
                  <FaTimes size={12} />
                  <span>Cancel</span>
                </Button>
              ) : (
                // Edit button when not editing
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => handleEditClick(fieldName)}
                  title="Edit"
                  className="d-flex align-items-center gap-1"
                >
                  <FaPen size={12} />
                  <span>Edit</span>
                </Button>
              )}
            </div>
          )}
        </div>
        {isUsername && <Form.Text className="text-muted">Username cannot be changed</Form.Text>}
      </Form.Group>
    );
  };

  if (loading) {
    return (
      <Container fluid className="vh-100 d-flex align-items-center justify-content-center">
        <div className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading profile...</p>
        </div>
      </Container>
    );
  }

  return (
    <Container fluid className="h-100 py-4">
      <Row className="h-100">
        <Col className="h-100 d-flex flex-column">
          <div className="mb-4">
            <h4 className="mb-0 fw-bold">Profile Settings</h4>
            <p className="text-muted mt-1">Manage your profile and chatbot information</p>
          </div>

          <div className="flex-grow-1">
            <Card className="h-100 border-0 shadow-sm">
              <Card.Body className="p-4">
                {error && (
                  <Alert variant="danger" dismissible onClose={() => setError('')} className="mb-4">
                    {error}
                  </Alert>
                )}

                {success && (
                  <Alert variant="success" dismissible onClose={() => setSuccess('')} className="mb-4">
                    {success}
                  </Alert>
                )}

                <Form className="h-100">
                  <div className="h-100">
                    {renderEditableField('Username', 'username', 'text', 'Enter your username')}
                    {renderEditableField('Full Name', 'name', 'text', 'Enter your full name')}
                    {renderEditableField('Email Address', 'email', 'email', 'Enter your email address')}
                    {renderEditableField('Mobile Number', 'mobileNumber', 'tel', 'Enter your mobile number')}
                    {renderEditableField('Chatbot Name', 'chatbotName', 'text', "Enter your chatbot's name", <FaRobot />)}
                  </div>

                  {/* Save Button */}
                  <div className="mt-5 pt-4 border-top">
                    <div className="d-flex justify-content-between align-items-center">
                      <div>
                        {hasChanges && (
                          <span className="text-warning fw-medium d-flex align-items-center">
                            <FaEdit className="me-2" />
                            You have unsaved changes
                          </span>
                        )}
                      </div>
                      <Button
                        variant="primary"
                        onClick={handleSaveChanges}
                        disabled={!hasChanges}
                        className="d-flex align-items-center gap-2 px-4"
                      >
                        <FaSave />
                        Save Changes
                      </Button>
                    </div>
                  </div>
                </Form>
              </Card.Body>
            </Card>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default ProfileSettings;
