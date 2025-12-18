import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, Button, Form, Spinner, Badge, Alert, Toast, ToastContainer } from 'react-bootstrap';
import { API_URL } from '../../../config';

export default function AdminChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [chats, setChats] = useState([]);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [replyMessage, setReplyMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ show: false, message: '', variant: 'success' });
  const chatContainerRef = useRef(null);
  const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
  const lastMessageCountRef = useRef(0);
  const [shortcuts, setShortcuts] = useState([]);
  const [showShortcutsDropdown, setShowShortcutsDropdown] = useState(false);
  const [filteredShortcuts, setFilteredShortcuts] = useState([]);

    // Fetch shortcuts on mount
    useEffect(() => {
      const fetchShortcuts = async () => {
        try {
          const res = await axios.get(`${API_URL}/shortcuts/`, {
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`
            }
          });
          setShortcuts(res.data);
        } catch (error) {
          console.error('Failed to fetch shortcuts:', error);
        }
      };

      if (token) {
        fetchShortcuts();
      }
    }, [token]);

    // Detect shortcut commands (starting with /)
    const handleReplyMessageChange = (e) => {
      const value = e.target.value;
      setReplyMessage(value);

      // Detect if typing a shortcut command
      if (value.startsWith('/')) {
        const command = value.slice(1).toLowerCase();

        if (command.length > 0) {
          // Filter shortcuts based on typed command
          const filtered = shortcuts.filter(s =>
            s.command.toLowerCase().startsWith(command)
          );
          setFilteredShortcuts(filtered);
          setShowShortcutsDropdown(filtered.length > 0);
        } else {
          // Show all shortcuts if just "/" is typed
          setFilteredShortcuts(shortcuts);
          setShowShortcutsDropdown(shortcuts.length > 0);
        }
      } else {
        setShowShortcutsDropdown(false);
      }
    };

    // Use a shortcut
    const handleUseShortcut = (shortcut) => {
      setReplyMessage(shortcut.message);
      setShowShortcutsDropdown(false);
    };

    // Handle keyboard navigation in shortcuts dropdown
    const handleKeyDown = (e) => {
      if (showShortcutsDropdown && filteredShortcuts.length > 0) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault();
          // Implement arrow key navigation if needed
        } else if (e.key === 'Enter' && filteredShortcuts.length === 1) {
          e.preventDefault();
          handleUseShortcut(filteredShortcuts[0]);
        } else if (e.key === 'Escape') {
          setShowShortcutsDropdown(false);
        }
      }
    };
  // Fetch session details
  const fetchSessionDetails = async () => {
    try {
      console.log('🔍 Fetching session details for:', sessionId);

      const res = await axios.get(`${API_URL}/client/session-details/${sessionId}`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });

      console.log('✅ Session details received:', res.data);

      const newChats = res.data.chats || [];

      // Only update if message count changed (prevents unnecessary re-renders)
      if (newChats.length !== lastMessageCountRef.current) {
        console.log(`📩 Message count changed: ${lastMessageCountRef.current} → ${newChats.length}`);
        setChats(newChats);
        lastMessageCountRef.current = newChats.length;
      }

      setSessionInfo(res.data.session_info || {});
      setError('');
    } catch (error) {
      console.error('❌ Failed to fetch session details:', error);

      if (error.response?.status === 404) {
        setError('Session not found. The user may not have sent any messages yet.');
      } else {
        setError('Failed to load chat session');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }

    if (!sessionId) {
      setError('No session ID provided');
      setLoading(false);
      return;
    }

    // Initial fetch
    fetchSessionDetails();

    // Auto-refresh every 2 seconds (faster for live chat)
    const interval = setInterval(fetchSessionDetails, 2000);
    return () => clearInterval(interval);
  }, [sessionId, token, navigate]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chats]);

  // Send admin reply
  const handleSendReply = async (e) => {
    e.preventDefault();

    if (!replyMessage.trim()) {
      return;
    }

    setSending(true);

    try {
      console.log('📤 Sending admin reply to session:', sessionId);

      await axios.post(
        `${API_URL}/client/client-reply/${sessionId}`,
        { message: replyMessage },
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        }
      );

      setReplyMessage('');

      // Immediately fetch updated chat to show the admin message
      await fetchSessionDetails();

      setToast({ show: true, message: '✅ Reply sent successfully', variant: 'success' });
    } catch (error) {
      console.error('❌ Failed to send reply:', error);
      setToast({ show: true, message: '❌ Failed to send reply', variant: 'danger' });
    } finally {
      setSending(false);
    }
  };

  // Delete message
  const handleDeleteMessage = async (chatId) => {
    if (!window.confirm('Are you sure you want to delete this message?')) {
      return;
    }

    try {
      console.log('🗑️ Deleting message:', chatId);

      await axios.delete(`${API_URL}/client/delete-chat/${chatId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      await fetchSessionDetails();
      setToast({ show: true, message: '✅ Message deleted', variant: 'info' });
    } catch (error) {
      console.error('❌ Failed to delete message:', error);
      setToast({ show: true, message: '❌ Failed to delete message', variant: 'danger' });
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
        <div className="text-center">
          <Spinner animation="border" variant="primary" />
          <p className="mt-3 text-muted">Loading chat session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid p-3" style={{ paddingBottom: '20px' }}>
      {/* Toast notifications */}
      <ToastContainer position="top-end" className="p-3" style={{ zIndex: 9999 }}>
        <Toast show={toast.show} onClose={() => setToast({ ...toast, show: false })} delay={3000} autohide bg={toast.variant}>
          <Toast.Body className="text-white">{toast.message}</Toast.Body>
        </Toast>
      </ToastContainer>

      {/* Header */}
      <Card className="mb-3 border-0 shadow-sm">
        <Card.Header className="bg-white">
          <div className="d-flex justify-content-between align-items-center">
            <div className="d-flex align-items-center gap-3">
              <Button variant="outline-secondary" size="sm" onClick={() => navigate(-1)}>
                ← Back
              </Button>
              <div>
                <h5 className="mb-1">
                  💬 Admin Chat Interface
                  <Badge bg="success" className="ms-2">
                    <span className="spinner-grow spinner-grow-sm me-1"></span>
                    LIVE
                  </Badge>
                </h5>
                <small className="text-muted">Session: {sessionId.substring(0, 40)}...</small>
              </div>
            </div>

            {sessionInfo && sessionInfo.started_at && (
              <div className="text-end small">
                <div>🌍 {sessionInfo.country_code || 'Unknown'}</div>
                <div className="text-muted">🕒 {new Date(sessionInfo.started_at).toLocaleString()}</div>
                <div className="text-muted">
                  <Badge bg="info">{chats.length} messages</Badge>
                </div>
              </div>
            )}
          </div>
        </Card.Header>
      </Card>

      {error && (
        <Alert variant="warning" dismissible onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Chat Messages - Fixed height with scroll */}
      <Card className="mb-3 shadow-sm">
        <Card.Body
          ref={chatContainerRef}
          className="overflow-auto p-4"
          style={{
            backgroundColor: '#f8f9fa',
            height: '55vh',
            minHeight: '400px'
          }}
        >
          {chats.length === 0 ? (
            <div className="text-center text-muted mt-5">
              <p className="mb-2">📭 No messages in this session yet</p>
              <small>The user hasn't started chatting. Messages will appear here when they send their first message.</small>
            </div>
          ) : (
            <div className="d-flex flex-column gap-3">
              {chats.map((chat) => (
                <div key={chat.id} className={`d-flex ${chat.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
                  <div
                    className={`p-3 rounded ${
                      chat.role === 'user'
                        ? 'bg-primary text-white'
                        : chat.admin_override
                          ? 'bg-success text-white border border-success border-3'
                          : 'bg-white border'
                    }`}
                    style={{ maxWidth: '70%' }}
                  >
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <strong className="small">
                        {chat.role === 'user' ? '👤 User' : chat.admin_override ? '👨‍💼 Admin (You)' : '🤖 Bot'}
                      </strong>
                      {chat.role === 'assistant' && !chat.admin_override && (
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0 ms-2 text-danger"
                          onClick={() => handleDeleteMessage(chat.id)}
                          title="Delete this bot message"
                        >
                          🗑️
                        </Button>
                      )}
                    </div>

                    <p className="mb-2" style={{ whiteSpace: 'pre-wrap' }}>
                      {chat.message}
                    </p>

                    <div className={`small ${chat.role === 'user' || chat.admin_override ? 'text-white-50' : 'text-muted'}`}>
                      {new Date(chat.created_at).toLocaleTimeString()}
                      {chat.admin_override && (
                        <Badge bg="light" text="success" className="ms-2">
                          Admin Override
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Reply Input */}
      <Card className="shadow-sm mb-4">
              <Card.Body>
                <Form onSubmit={handleSendReply}>
                  <Form.Group className="mb-3" style={{ position: 'relative' }}>
                    <Form.Label className="fw-bold d-flex justify-content-between align-items-center">
                      <span>
                        💬 Send Admin Reply
                        <Badge bg="success" className="ms-2">User will see this instantly</Badge>
                      </span>
                      <small className="text-muted fw-normal">
                        💡 Type / for shortcuts ({shortcuts.length} available)
                      </small>
                    </Form.Label>

                    <Form.Control
                      as="textarea"
                      rows={3}
                      value={replyMessage}
                      onChange={handleReplyMessageChange}
                      onKeyDown={handleKeyDown}
                      placeholder="Type your admin reply... Or type / to use a shortcut"
                      disabled={sending}
                    />

                    {/* Shortcuts Dropdown */}
                    {showShortcutsDropdown && (
                      <div
                        style={{
                          position: 'absolute',
                          bottom: '100%',
                          left: 0,
                          right: 0,
                          backgroundColor: 'white',
                          border: '1px solid #ddd',
                          borderRadius: '8px',
                          maxHeight: '200px',
                          overflowY: 'auto',
                          boxShadow: '0 -4px 12px rgba(0,0,0,0.1)',
                          zIndex: 1000,
                          marginBottom: '8px'
                        }}
                      >
                        <div className="p-2 bg-light border-bottom">
                          <small className="text-muted fw-bold">
                            ⚡ Available Shortcuts ({filteredShortcuts.length})
                          </small>
                        </div>
                        {filteredShortcuts.map(shortcut => (
                          <div
                            key={shortcut.id}
                            onClick={() => handleUseShortcut(shortcut)}
                            style={{
                              padding: '12px',
                              cursor: 'pointer',
                              borderBottom: '1px solid #f0f0f0',
                              transition: 'background 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                          >
                            <div className="d-flex justify-content-between align-items-start">
                              <div style={{ flex: 1 }}>
                                <div className="mb-1">
                                  <code className="text-primary fw-bold">/{shortcut.command}</code>
                                  <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.7rem' }}>
                                    {shortcut.action_type}
                                  </Badge>
                                </div>
                                <small className="text-muted d-block text-truncate" style={{ maxWidth: '90%' }}>
                                  {shortcut.message}
                                </small>
                              </div>
                              <small className="text-muted">Click to use</small>
                            </div>
                          </div>
                        ))}

                        {filteredShortcuts.length === 0 && (
                          <div className="p-3 text-center text-muted">
                            <small>No shortcuts found. Press ESC to close.</small>
                          </div>
                        )}
                      </div>
                    )}
                  </Form.Group>

                  <div className="d-flex justify-content-between align-items-center">
                    <div>
                      <small className="text-muted d-block mb-1">
                        💡 Your reply will appear with a green background and "Support Team" label
                      </small>
                      {shortcuts.length > 0 && (
                        <small className="text-success d-block">
                          ⚡ {shortcuts.length} shortcuts available - Type / to see all
                        </small>
                      )}
                    </div>

                    <Button
                      type="submit"
                      variant="success"
                      disabled={sending || !replyMessage.trim()}
                      size="lg"
                    >
                      {sending ? (
                        <>
                          <Spinner animation="border" size="sm" className="me-2" />
                          Sending...
                        </>
                      ) : (
                        <>
                          📤 Send Admin Reply
                        </>
                      )}
                    </Button>
                  </div>
                </Form>
              </Card.Body>
            </Card>
    </div>
  );
}
