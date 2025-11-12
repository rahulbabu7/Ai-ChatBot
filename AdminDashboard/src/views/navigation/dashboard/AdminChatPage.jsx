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

  // Fetch session details
  const fetchSessionDetails = async () => {
    try {
      const res = await axios.get(`${API_URL}/client/session-details/${sessionId}`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });

      setChats(res.data.chats || []);
      setSessionInfo(res.data.session_info || {});
      setError('');
    } catch (error) {
      console.error('Failed to fetch session details:', error);
      setError('Failed to load chat session');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }

    fetchSessionDetails();

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchSessionDetails, 5000);
    return () => clearInterval(interval);
  }, [sessionId, token, navigate]);

  // Auto-scroll to bottom
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
      await fetchSessionDetails();
      
      setToast({ show: true, message: 'Reply sent successfully', variant: 'success' });
    } catch (error) {
      console.error('Failed to send reply:', error);
      setToast({ show: true, message: 'Failed to send reply', variant: 'danger' });
    } finally {
      setSending(false);
    }
  };

  // Delete message
  const handleDeleteMessage = async (chatId) => {
    try {
      await axios.delete(`${API_URL}/client/delete-chat/${chatId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      await fetchSessionDetails();
      setToast({ show: true, message: 'Message deleted', variant: 'info' });
    } catch (error) {
      console.error('Failed to delete message:', error);
      setToast({ show: true, message: 'Failed to delete message', variant: 'danger' });
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
        <Toast 
          show={toast.show} 
          onClose={() => setToast({ ...toast, show: false })} 
          delay={3000} 
          autohide
          bg={toast.variant}
        >
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
                <h5 className="mb-1">Admin Chat Interface</h5>
                <small className="text-muted">Session: {sessionId.substring(0, 30)}...</small>
              </div>
            </div>

            {sessionInfo && (
              <div className="text-end small">
                <div>🌍 {sessionInfo.country_code || 'Unknown'}</div>
                <div className="text-muted">🕒 {new Date(sessionInfo.started_at).toLocaleString()}</div>
              </div>
            )}
          </div>
        </Card.Header>
      </Card>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError('')}>
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
              <p>No messages in this session yet</p>
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
                          ? 'bg-success bg-opacity-10 border border-success border-2'
                          : 'bg-white border'
                    }`}
                    style={{ maxWidth: '70%' }}
                  >
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <strong className="small">{chat.role === 'user' ? '👤 User' : chat.admin_override ? '👨‍💼 Admin' : '🤖 Bot'}</strong>
                      {chat.role === 'assistant' && (
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0 ms-2 text-danger"
                          onClick={() => handleDeleteMessage(chat.id)}
                          title="Delete message"
                        >
                          🗑️
                        </Button>
                      )}
                    </div>

                    <p className="mb-2" style={{ whiteSpace: 'pre-wrap' }}>
                      {chat.message}
                    </p>

                    <div className="small text-muted">
                      {new Date(chat.created_at).toLocaleTimeString()}
                      {chat.admin_override && (
                        <Badge bg="success" className="ms-2">
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

      {/* Reply Input - Now properly positioned */}
      <Card className="shadow-sm mb-4">
        <Card.Body>
          <Form onSubmit={handleSendReply}>
            <Form.Group className="mb-3">
              <Form.Control
                as="textarea"
                rows={3}
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder="Type your admin reply here..."
                disabled={sending}
              />
            </Form.Group>

            <div className="d-flex justify-content-between align-items-center">
              <small className="text-muted">💡 Your reply will be sent to the user</small>

              <Button type="submit" variant="primary" disabled={sending || !replyMessage.trim()}>
                {sending ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    Sending...
                  </>
                ) : (
                  'Send Admin Reply'
                )}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </div>
  );
}