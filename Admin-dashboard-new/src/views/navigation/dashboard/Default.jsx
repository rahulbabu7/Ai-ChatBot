import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../../../config';

// react-bootstrap
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Card from 'react-bootstrap/Card';
import Spinner from 'react-bootstrap/Spinner';
import ListGroup from 'react-bootstrap/ListGroup';

export default function DefaultPage() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState('');
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [visitorCount, setVisitorCount] = useState(0);

  const chatContainerRef = useRef(null);

  // Get JWT token from storage
  const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');

  // Fetch sessions on mount
  useEffect(() => {
    if (!token) return;

    axios
      .get(`${API_URL}/client/sessions/me`, {
        headers: { 'x-token': token }
      })
      .then((res) => {
        setSessions(res.data.sessions || []);
        setSelectedSession('');
        setChats([]);
        setVisitorCount(res.data.sessions?.length || 0);
      })
      .catch(() => {
        setSessions([]);
        setVisitorCount(0);
      });
  }, [token]);

  // Fetch chats whenever a session is selected
  useEffect(() => {
    if (!token || !selectedSession) return;

    setLoading(true);
    axios
      .get(
        `${API_URL}/client/chats/me?session_id=${selectedSession}`, // ✅ match backend
        { headers: { 'x-token': token } }
      )
      .then((res) => setChats(res.data.chats || []))
      .catch(() => setChats([]))
      .finally(() => setLoading(false));
  }, [token, selectedSession]);

  // Scroll chat to bottom when chats update
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chats]);

  if (!token) {
    return <p className="text-center mt-5">❌ You must log in to view this page.</p>;
  }

  return (
    <Row>
      {/* Sidebar (Sessions) */}
      <Col md={4} xl={3}>
        <Card className="shadow-sm h-100">
          <Card.Header>
            <h5 className="mb-0">Active Sessions</h5>
          </Card.Header>
          <Card.Body>
            {sessions.length > 0 ? (
              <ListGroup>
                {sessions.map((s) => (
                  <ListGroup.Item key={s} action active={selectedSession === s} onClick={() => setSelectedSession(s)}>
                    Session {s}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            ) : (
              <p className="text-muted">No sessions available</p>
            )}

            <Card
              className={`mt-3 text-center shadow-sm border-0 ${
                visitorCount > 5 ? 'bg-success text-white' : visitorCount > 0 ? 'bg-warning text-dark' : 'bg-danger text-white'
              }`}
            >
              <Card.Body>
                <h6 className="mb-1">Active Sessions</h6>
                <h2 className="fw-bold mb-0">{visitorCount}</h2>
              </Card.Body>
            </Card>
          </Card.Body>
        </Card>
      </Col>

      {/* Chat Area */}
      <Col md={8} xl={9}>
        <Card className="shadow-sm h-100">
          <Card.Header>
            <h5 className="mb-0">Chats</h5>
          </Card.Header>
          <Card.Body ref={chatContainerRef} className="chat-messages p-2" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            {loading ? (
              <div className="d-flex justify-content-center align-items-center h-100">
                <Spinner animation="border" />
                <span className="ms-2">Loading chats...</span>
              </div>
            ) : chats.length === 0 ? (
              <p className="text-muted">Select a session to view chats</p>
            ) : (
              chats.map((chat, i) => (
                <div
                  key={i}
                  className={`chat-message mb-3 p-2 rounded ${
                    chat.role === 'user' ? 'bg-primary text-white text-end' : 'bg-light border text-start'
                  }`}
                >
                  <div>{chat.message}</div>
                  <div className="small text-muted mt-1">
                    [{chat.role}] {new Date(chat.created_at).toLocaleString()} | UA: {chat.user_agent} | Country:{' '}
                    {chat.country_code || 'Unknown'}
                  </div>
                </div>
              ))
            )}
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
}
