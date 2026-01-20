import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Dropdown from 'react-bootstrap/Dropdown';
import Image from 'react-bootstrap/Image';
import Nav from 'react-bootstrap/Nav';
import Stack from 'react-bootstrap/Stack';
import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import { handlerDrawerOpen, useGetMenuMaster } from 'api/menu';
import Img2 from 'assets/images/user/avatar-2.png';
import { API_URL } from '../../config';

export default function Header() {
  const navigate = useNavigate();
  const { menuMaster } = useGetMenuMaster();
  const drawerOpen = menuMaster?.isDashboardDrawerOpened;

  const [user, setUser] = useState({ name: '', email: '' });
  const [showShareModal, setShowShareModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [shareUrl, setShareUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchUserDetails = async () => {
      try {
        const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
        if (!token) return;

        const res = await fetch(`${API_URL}/auth/me`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });
        if (!res.ok) throw new Error('Failed to fetch user details');

        const data = await res.json();
        setUser({ name: data.name, email: data.email });
      } catch (error) {
        console.error('Error fetching user details:', error);
      }
    };

    fetchUserDetails();
    setShareUrl(window.location.href);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('jwt_token');
    sessionStorage.removeItem('jwt_token');
    navigate('/login', { replace: true });
  };

  // Share functionality
  const handleShare = () => {
    setShowShareModal(true);
  };

  const copyToClipboard = () => {
    navigator.clipboard
      .writeText(shareUrl)
      .then(() => {
        setSuccess('Link copied to clipboard!');
        setTimeout(() => setSuccess(''), 3000);
      })
      .catch((err) => {
        setError('Failed to copy link');
        console.error('Failed to copy: ', err);
      });
  };

  const shareViaNative = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Check out this app',
          text: 'Check out this amazing application!',
          url: shareUrl
        });
      } catch (err) {
        console.error('Error sharing:', err);
      }
    } else {
      copyToClipboard();
    }
  };

  // Change Password functionality - Client Side Only
  const handleChangePassword = () => {
    setShowPasswordModal(true);
    setError('');
    setSuccess('');
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData((prev) => ({
      ...prev,
      [name]: value
    }));
    if (error) setError('');
  };

  const validatePassword = () => {
    if (!passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword) {
      setError('All fields are required');
      return false;
    }

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setError("New passwords don't match!");
      return false;
    }

    if (passwordData.newPassword.length < 6) {
      setError('Password must be at least 6 characters long!');
      return false;
    }

    if (passwordData.currentPassword === passwordData.newPassword) {
      setError('New password must be different from current password');
      return false;
    }

    // Additional security validations
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/;
    if (!passwordRegex.test(passwordData.newPassword)) {
      setError('Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character');
      return false;
    }

    return true;
  };

  const submitPasswordChange = async () => {
    setError('');
    setSuccess('');

    if (!validatePassword()) {
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');

      const response = await fetch(`${API_URL}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: passwordData.currentPassword,
          new_password: passwordData.newPassword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to change password');
      }

      setSuccess('Password changed successfully!');

      setTimeout(() => {
        setShowPasswordModal(false);
        setPasswordData({
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        });
        setSuccess('');
      }, 2000);
    } catch (error) {
      console.error('Error changing password:', error);
      setError(error.message || 'Error changing password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const closePasswordModal = () => {
    setShowPasswordModal(false);
    setPasswordData({
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    });
    setError('');
    setSuccess('');
  };

  // Navigation handlers for settings sub-buttons
  const navigateToPage = (path) => {
    navigate(path);
  };

  return (
    <>
      <header className="pc-header">
        <div className="header-wrapper d-flex align-items-center justify-content-between">
          <Nav className="list-unstyled d-flex align-items-center">
            <Nav.Item className="pc-h-item pc-sidebar-collapse">
              <Nav.Link as={Link} to="#" className="pc-head-link ms-0" onClick={() => handlerDrawerOpen(!drawerOpen)}>
                <i className="ph ph-list" />
              </Nav.Link>
            </Nav.Item>
          </Nav>

          <Nav className="list-unstyled d-flex align-items-center ms-auto">
            {/* User Profile Dropdown */}
            <Dropdown align="end">
              <Dropdown.Toggle className="pc-head-link p-0 border-0 bg-transparent" variant="link" id="user-dropdown">
                <Image src={Img2} alt="user-avatar" style={{ width: '35px', height: '35px', cursor: 'pointer' }} roundedCircle />
              </Dropdown.Toggle>
              
              <Dropdown.Menu className="dropdown-user-profile pc-h-dropdown p-0 overflow-hidden">
                <Dropdown.Header className="bg-primary">
                  <Stack direction="horizontal" gap={2} className="my-2 align-items-center">
                    <Image src={Img2} alt="user-avatar" style={{ width: '35px', height: '35px' }} roundedCircle />
                    <div>
                      <h6 className="text-white mb-0">{user.name || 'Loading...'}</h6>
                      <span className="text-white text-opacity-75">{user.email || ''}</span>
                    </div>
                  </Stack>
                </Dropdown.Header>

                <div className="dropdown-body p-2">
                  <Dropdown.Header className="fw-bold"> Settings</Dropdown.Header>
                  <Dropdown.Item as="button" className="justify-content-start" onClick={() => navigateToPage('/settings/profile')}>
                  <i className="ph ph-user me-2" /> Profile Settings
                  </Dropdown.Item>
                  <Dropdown.Item as="button" className="justify-content-start" onClick={() => navigateToPage('/settings/shortcuts')}>
                  <i className="ph ph-keyboard me-2" /> Shortcuts
                  </Dropdown.Item>
                  <Dropdown.Item as="button" className="justify-content-start" onClick={handleChangePassword}>
                    <i className="ph ph-lock-key me-2" /> Change Password
                  </Dropdown.Item>
                  <Dropdown.Divider />
                  <Dropdown.Item as="button" className="justify-content-start" onClick={handleLogout}>
                    <i className="ph ph-sign-out me-2" /> Logout
                  </Dropdown.Item>
                </div>
              </Dropdown.Menu>
            </Dropdown>
          </Nav>
        </div>
      </header>  

      {/* Share Modal */}
      <Modal show={showShareModal} onHide={() => setShowShareModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Share Application</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {success && <Alert variant="success">{success}</Alert>}
          {error && <Alert variant="danger">{error}</Alert>}
          <p>Share this application with others:</p>
          <div className="input-group mb-3">
            <Form.Control type="text" value={shareUrl} readOnly />
            <Button variant="outline-secondary" onClick={copyToClipboard}>
              Copy
            </Button>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowShareModal(false)}>
            Close
          </Button>
          <Button variant="primary" onClick={shareViaNative}>
            Share
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Change Password Modal */}
      <Modal show={showPasswordModal} onHide={closePasswordModal} centered>
        <Modal.Header closeButton>
          <Modal.Title>Change Password</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {success && <Alert variant="success">{success}</Alert>}
          {error && <Alert variant="danger">{error}</Alert>}

          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Current Password</Form.Label>
              <Form.Control
                type="password"
                name="currentPassword"
                value={passwordData.currentPassword}
                onChange={handlePasswordChange}
                placeholder="Enter current password"
                disabled={loading}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>New Password</Form.Label>
              <Form.Control
                type="password"
                name="newPassword"
                value={passwordData.newPassword}
                onChange={handlePasswordChange}
                placeholder="Enter new password (min. 6 characters with uppercase, lowercase, number & special character)"
                disabled={loading}
              />
              <Form.Text className="text-muted">
                Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character
              </Form.Text>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Confirm New Password</Form.Label>
              <Form.Control
                type="password"
                name="confirmPassword"
                value={passwordData.confirmPassword}
                onChange={handlePasswordChange}
                placeholder="Confirm new password"
                disabled={loading}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={closePasswordModal} disabled={loading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submitPasswordChange} disabled={loading}>
            {loading ? 'Changing Password...' : 'Change Password'}
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
