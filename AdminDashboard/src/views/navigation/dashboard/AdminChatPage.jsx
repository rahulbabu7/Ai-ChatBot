import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, Button, Form, Spinner, Badge, Alert, Toast, ToastContainer } from 'react-bootstrap';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';

export default function AdminChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  
  const [chats, setChats] = useState([]);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [replyMessage, setReplyMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ show: false, message: '', variant: 'success' });
  const [wsConnected, setWsConnected] = useState(false);
  const [isUserTyping, setIsUserTyping] = useState(false);

  const chatContainerRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  const [shortcuts, setShortcuts] = useState([]);
  const [showShortcutsDropdown, setShowShortcutsDropdown] = useState(false);
  const [filteredShortcuts, setFilteredShortcuts] = useState([]);

  // WebSocket URL
  const WS_URL = API_URL.replace('http', 'ws').replace('https', 'wss');

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

  // Connect to WebSocket
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // console.log('✅ WebSocket already connected');
      return;
    }

    try {
      const wsUrl = `${WS_URL}/ws/admin/${sessionId}?token=${token}`;
      // console.log('🔌 Admin connecting to WebSocket:', wsUrl);

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        // console.log('✅ Admin WebSocket connected');
        setWsConnected(true);

        // Send ping every 30 seconds
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);

        ws.pingInterval = pingInterval;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // console.log('📨 Admin WebSocket message:', data);

          handleWebSocketMessage(data);
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ Admin WebSocket error:', error);
        setWsConnected(false);
      };

      ws.onclose = () => {
        // console.log('📴 Admin WebSocket disconnected');
        setWsConnected(false);

        if (ws.pingInterval) {
          clearInterval(ws.pingInterval);
        }

        // Auto-reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          // console.log('🔄 Attempting to reconnect Admin WebSocket...');
          connectWebSocket();
        }, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('❌ Failed to create Admin WebSocket:', error);
    }
  };

  // Disconnect WebSocket
  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      if (wsRef.current.pingInterval) {
        clearInterval(wsRef.current.pingInterval);
      }
      wsRef.current.close();
      wsRef.current = null;
    }

    setWsConnected(false);
  };

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'new_user_message':
        // User sent a new message
        const messageContent = typeof data.message === 'string' ? data.message : data.message.message;
        const userMsg = {
          id: data.message.id || `ws_user_${Date.now()}`,
          role: 'user',
          message: messageContent,
          created_at: data.message.timestamp || data.timestamp,
          admin_override: 0,
          country_code: data.message.country_code,
          user_agent: data.message.user_agent
        };

        setChats((prev) => {
          // Prevent duplicates by checking if message with same ID already exists
          const existingIndex = prev.findIndex(chat => chat.id === userMsg.id);
          if (existingIndex !== -1) {
            // Update existing message
            const updated = [...prev];
            updated[existingIndex] = userMsg;
            return updated;
          }
          // Add new message
          return [...prev, userMsg];
        });
        setToast({ show: true, message: '📩 New message from user', variant: 'info' });
        break;

      case 'new_bot_message':
        // Chatbot sent a reply
        const botMsg = {
          id: data.message.id || `ws_bot_${Date.now()}`,
          role: 'assistant',
          message: data.message.message,
          created_at: data.message.timestamp,
          admin_override: data.message.admin_override || false,
          response_time: data.message.response_time
        };

        setChats((prev) => {
          // Prevent duplicates by checking if message with same ID already exists
          const existingIndex = prev.findIndex(chat => chat.id === botMsg.id);
          if (existingIndex !== -1) {
            // Update existing message
            const updated = [...prev];
            updated[existingIndex] = botMsg;
            return updated;
          }
          // Add new message
          return [...prev, botMsg];
        });
        setToast({ show: true, message: '🤖 Bot replied', variant: 'success' });
        break;

      case 'user_typing':
        setIsUserTyping(data.is_typing);
        break;

      case 'client_disconnected':
        setToast({ show: true, message: '📴 User disconnected', variant: 'warning' });
        break;

      case 'pong':
        // Keep-alive response
        break;

      default:
        // console.log('Unknown WebSocket message type:', data.type, data);
    }
  };

  // Send typing indicator
  const sendTypingIndicator = (isTyping) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'typing',
          is_typing: isTyping
        })
      );
    }
  };

  // Handle input change with typing indicator
  const handleReplyMessageChange = (e) => {
    const value = e.target.value;
    setReplyMessage(value);

    // Send typing indicator
    if (value.trim()) {
      sendTypingIndicator(true);

      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      typingTimeoutRef.current = setTimeout(() => {
        sendTypingIndicator(false);
      }, 2000);
    } else {
      sendTypingIndicator(false);
    }

    // Handle shortcuts
    if (value.startsWith('/')) {
      const command = value.slice(1).toLowerCase();

      if (command.length > 0) {
        const filtered = shortcuts.filter((s) => s.command.toLowerCase().startsWith(command));
        setFilteredShortcuts(filtered);
        setShowShortcutsDropdown(filtered.length > 0);
      } else {
        setFilteredShortcuts(shortcuts);
        setShowShortcutsDropdown(shortcuts.length > 0);
      }
    } else {
      setShowShortcutsDropdown(false);
    }
  };

  const handleUseShortcut = (shortcut) => {
    setReplyMessage(shortcut.message);
    setShowShortcutsDropdown(false);
  };

  const handleKeyDown = (e) => {
    if (showShortcutsDropdown && filteredShortcuts.length > 0) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
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
    if (!sessionId) {
      setError('No session ID provided');
      setLoading(false);
      return;
    }

    // Initial fetch
    fetchSessionDetails();

    // Connect WebSocket
    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, [sessionId, token, navigate]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chats]);

  // Send admin reply via WebSocket and HTTP
  const handleSendReply = async (e) => {
    e.preventDefault();

    if (!replyMessage.trim()) {
      return;
    }

    setSending(true);
    sendTypingIndicator(false);

    try {
      // Send via HTTP (saves to database)
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

      // Send via WebSocket for instant delivery
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'admin_reply',
            message: replyMessage
          })
        );
      }

      // Add message to local state immediately
      const newMsg = {
        id: `temp_${Date.now()}`,
        role: 'assistant',
        message: replyMessage,
        created_at: new Date().toISOString(), // Already in UTC format
        admin_override: 1
      };

      setChats((prev) => {
        // Prevent duplicates by checking if message with same ID already exists
        const existingIndex = prev.findIndex(chat => chat.id === newMsg.id);
        if (existingIndex !== -1) {
          // Update existing message
          const updated = [...prev];
          updated[existingIndex] = newMsg;
          return updated;
        }
        // Add new message
        return [...prev, newMsg];
      });
      setReplyMessage('');
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
      await axios.delete(`${API_URL}/client/delete-chat/${chatId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      // Notify client via WebSocket
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'delete_message',
            message_id: chatId
          })
        );
      }

      setChats((prev) => prev.filter((chat) => chat.id !== chatId));
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
      <ToastContainer position="top-end" className="p-3" style={{ zIndex: 9999 }}>
        <Toast show={toast.show} onClose={() => setToast({ ...toast, show: false })} delay={3000} autohide bg={toast.variant}>
          <Toast.Body className="text-white">{toast.message}</Toast.Body>
        </Toast>
      </ToastContainer>

      {/* Header */}
      <Card className="mb-3 border-0 shadow-sm">
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <div className="d-flex align-items-center gap-3">
              <Button variant="outline-secondary" size="sm" onClick={() => navigate(-1)}>
                ← Back
              </Button>
              <div>
                <h5 className="mb-1">
                  💬 Admin Chat Interface
                  <Badge bg={wsConnected ? 'success' : 'danger'} className="ms-2">
                    {wsConnected ? (
                      <>
                        <span className="spinner-grow spinner-grow-sm me-1"></span>
                        LIVE
                      </>
                    ) : (
                      'DISCONNECTED'
                    )}
                  </Badge>
                </h5>
                <small className="text-muted">Session: {sessionId.substring(0, 40)}...</small>
              </div>
            </div>

            {sessionInfo && sessionInfo.started_at && (
              <div className="text-end small">
                <div>🌍 {sessionInfo.country_code || 'Unknown'}</div>
                <div className="text-muted">🕒 {new Date(sessionInfo.started_at).toLocaleString('en-IN', {
                  year: 'numeric',
                  month: 'short', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                  timeZone: 'Asia/Kolkata',
                  timeZoneName: 'short'
                })}</div>
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

      {/* Chat Messages */}
      <Card className="mb-3 shadow-sm">
        <Card.Body
          ref={chatContainerRef}
          className="overflow-auto p-4 admin-chat-messages"
          style={{
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
              {chats.map((chat, index) => (
                <div key={`${chat.id}-${index}`} className={`d-flex ${chat.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
                  <div
                    className={`p-3 rounded ${
                      chat.role === 'user'
                        ? 'bg-primary text-white'
                        : chat.admin_override
                          ? 'bg-success text-white border border-success border-3'
                          : 'chat-bubble-bot border'
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
                      {new Date(chat.created_at).toLocaleString('en-IN', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit',
                        day: 'numeric',
                        month: 'short',
                        timeZone: 'Asia/Kolkata',
                        timeZoneName: 'short'
                      })}
                      {chat.admin_override && (
                        <Badge bg="light" text="success" className="ms-2">
                          Admin Override
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* User typing indicator */}
              {isUserTyping && (
                <div className="d-flex justify-content-end">
                  <div className="p-3 rounded chat-bubble-bot" style={{ maxWidth: '70%' }}>
                    <small className="text-muted">
                      <span className="spinner-grow spinner-grow-sm me-2" style={{ width: '0.5rem', height: '0.5rem' }}></span>
                      User is typing...
                    </small>
                  </div>
                </div>
              )}
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
                  {/* <Badge bg="success" className="ms-2">
                    User will see this instantly via WebSocket
                  </Badge>*/}
                </span>
                <small className="text-muted fw-normal">💡 Type / for shortcuts ({shortcuts.length} available)</small>
              </Form.Label>

              <Form.Control
                as="textarea"
                rows={3}
                value={replyMessage}
                onChange={handleReplyMessageChange}
                onKeyDown={handleKeyDown}
                placeholder="Type your admin reply... Or type / to use a shortcut"
                disabled={sending || !wsConnected}
              />

              {/* Shortcuts Dropdown */}
              {showShortcutsDropdown && (
                <div
                  className="shortcuts-dropdown"
                  style={{
                    position: 'absolute',
                    bottom: '100%',
                    left: 0,
                    right: 0,
                    borderRadius: '8px',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    boxShadow: '0 -4px 12px rgba(0,0,0,0.1)',
                    zIndex: 1000,
                    marginBottom: '8px'
                  }}
                >
                  <div className="shortcuts-header p-2 bg-light border-bottom">
                    <small className="text-muted fw-bold">⚡ Available Shortcuts ({filteredShortcuts.length})</small>
                  </div>
                  {filteredShortcuts.map((shortcut) => (
                    <div
                      key={shortcut.id}
                      className="shortcut-item"
                      onClick={() => handleUseShortcut(shortcut)}
                      style={{
                        padding: '12px',
                        cursor: 'pointer',
                        transition: 'background 0.2s'
                      }}
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
                </div>
              )}
            </Form.Group>

            <div className="d-flex justify-content-between align-items-center">
              <div>
                <small className="text-muted d-block mb-1">
                  💡 Your reply will appear with a green background and "Support Team" label
                </small>
                {/* <small
                  className={wsConnected ? 'text-success' : 'text-danger'}
                  style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <span
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: wsConnected ? '#10b981' : '#ef4444',
                      display: 'inline-block'
                    }}
                  ></span>
                  {wsConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
                </small>*/}
              </div>

              <Button type="submit" variant="success" disabled={sending || !replyMessage.trim() || !wsConnected} size="lg">
                {sending ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    Sending...
                  </>
                ) : (
                  <>📤 Send Admin Reply</>
                )}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </div>
  );
}
