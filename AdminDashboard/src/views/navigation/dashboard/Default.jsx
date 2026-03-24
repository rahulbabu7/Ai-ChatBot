import { useNavigate } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// react-bootstrap
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Card from 'react-bootstrap/Card';
import Spinner from 'react-bootstrap/Spinner';
import ListGroup from 'react-bootstrap/ListGroup';
import Badge from 'react-bootstrap/Badge';
import Button from 'react-bootstrap/Button';

// Chart.js
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

export default function DefaultPage() {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState('');
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);

  // Dashboard stats from new endpoint
  const [totalSessions, setTotalSessions] = useState(0);
  const [todaySessions, setTodaySessions] = useState(0);
  const [todayVisitors, setTodayVisitors] = useState(0);
  const [activeUsersNow, setActiveUsersNow] = useState(0);

  // Active users details
  const [activeUsersList, setActiveUsersList] = useState([]);

  // Graph data
  const [dailyStats, setDailyStats] = useState([]);
  const [statsLoading, setStatsLoading] = useState(false);

  const chatContainerRef = useRef(null);

  // Fetch dashboard stats (all metrics in one call)
  useEffect(() => {
    if (!token) return;

    const fetchDashboardStats = async () => {
      try {
        const res = await axios.get(`${API_URL}/client/stats/dashboard`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });

        // console.log('📊 Dashboard stats:', res.data);

        setTotalSessions(res.data.total_sessions);
        setTodaySessions(res.data.today_sessions);
        setTodayVisitors(res.data.today_visitors);
        setActiveUsersNow(res.data.active_users_now);
      } catch (error) {
        console.error('❌ Failed to fetch dashboard stats:', error);
      }
    };

    fetchDashboardStats();
    const intervalId = setInterval(fetchDashboardStats, 5000);

    return () => clearInterval(intervalId);
  }, [token]);

  // Fetch active users details
  useEffect(() => {
    if (!token) return;

    const fetchActiveUsers = async () => {
      try {
        const res = await axios.get(`${API_URL}/client/active-users/me`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });

        setActiveUsersList(res.data.sessions || []);
      } catch (error) {
        console.error('❌ Failed to fetch active users list:', error);
        setActiveUsersList([]);
      }
    };

    fetchActiveUsers();
    const intervalId = setInterval(fetchActiveUsers, 5000);

    return () => clearInterval(intervalId);
  }, [token]);

  // Fetch daily stats for graph
  useEffect(() => {
    if (!token) return;

    const fetchDailyStats = async () => {
      setStatsLoading(true);
      try {
        const res = await axios.get(`${API_URL}/client/stats/daily`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });

        // console.log('📈 Daily stats:', res.data);
        setDailyStats(res.data.daily_stats || []);
      } catch (error) {
        console.error('❌ Failed to fetch daily stats:', error);
        setDailyStats([]);
      } finally {
        setStatsLoading(false);
      }
    };

    fetchDailyStats();
    const intervalId = setInterval(fetchDailyStats, 60000);

    return () => clearInterval(intervalId);
  }, [token]);

  // Fetch sessions
  useEffect(() => {
    if (!token) return;

    const fetchSessions = async () => {
      try {
        const res = await axios.get(`${API_URL}/client/sessions/me`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });

        const sessionsData = res.data.sessions || [];
        setSessions(sessionsData);
      } catch (error) {
        console.error('❌ Failed to fetch sessions:', error);
        setSessions([]);
      }
    };

    fetchSessions();
    const intervalId = setInterval(fetchSessions, 30000);

    return () => clearInterval(intervalId);
  }, [token]);

  // Fetch chats when session selected
  useEffect(() => {
    if (!token || !selectedSession) return;

    const fetchChats = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_URL}/client/chats/me?session_id=${selectedSession}`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });
        setChats(res.data.chats || []);
      } catch (error) {
        console.error('❌ Failed to fetch chats:', error);
        setChats([]);
      } finally {
        setLoading(false);
      }
    };

    fetchChats();
  }, [token, selectedSession]);

  // Auto-scroll chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chats]);

  // Prepare chart data
  const chartData = {
    labels: dailyStats.map((stat) => {
      const date = new Date(stat.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'Daily Visitors',
        data: dailyStats.map((stat) => stat.visitors),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Daily Chats',
        data: dailyStats.map((stat) => stat.chats),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.4,
        fill: true
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top'
      },
      title: {
        display: true,
        text: 'Last 7 Days - Visitors & Chats'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
          precision: 0
        }
      }
    }
  };


  return (
    <>
      {/* Stats Cards */}
      <Row className="mb-4">
        <Col md={3} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-info text-white">
            <Card.Body className="d-flex flex-column justify-content-center">
              <h6 className="mb-1">Total Sessions</h6>
              <h2 className="fw-bold mb-0">{totalSessions}</h2>
              <small className="opacity-75">All time</small>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-danger text-white position-relative">
            <Card.Body className="d-flex flex-column justify-content-center">
              <div className="position-absolute top-0 end-0 m-2">
                <span className="badge bg-light text-danger">
                  <span className="spinner-grow spinner-grow-sm me-1" role="status"></span>
                  LIVE
                </span>
              </div>
              <h6 className="mb-1">Active Users Now</h6>
              <h2 className="fw-bold mb-0">{activeUsersNow}</h2>
              <small className="opacity-75">Chatbot open</small>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-success text-white">
            <Card.Body className="d-flex flex-column justify-content-center">
              <h6 className="mb-1">Today's Sessions</h6>
              <h2 className="fw-bold mb-0">{todaySessions}</h2>
              <small className="opacity-75">Unique conversations</small>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-warning text-dark">
            <Card.Body className="d-flex flex-column justify-content-center">
              <h6 className="mb-1">Today's Visitors</h6>
              <h2 className="fw-bold mb-0">{todayVisitors}</h2>
              <small className="opacity-75">Unique users</small>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Active Users Details - NOW CLICKABLE */}
      {activeUsersNow > 0 && (
        <Row className="mb-4">
          <Col>
            <Card className="shadow-sm border-success">
              <Card.Header className="bg-success text-white d-flex justify-content-between align-items-center">
                <h5 className="mb-0">🟢 Active Users Right Now ({activeUsersNow})</h5>
                <Badge bg="light" text="success">
                  <span className="spinner-grow spinner-grow-sm me-1"></span>
                  LIVE
                </Badge>
              </Card.Header>
              <Card.Body style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <ListGroup>
                  {activeUsersList.map((user, idx) => {
                    const lastSeenDate = new Date(user.last_seen);
                    const now = new Date();
                    const secondsAgo = Math.floor((now - lastSeenDate) / 1000);

                    return (
                      <ListGroup.Item
                        key={idx}
                        className="d-flex justify-content-between align-items-start"
                        action
                        onClick={() => {
                          // console.log('🔍 Navigating to session:', user.session_id);
                          // console.log('🔍 Full session ID length:', user.session_id.length);
                          // FIX: Use FULL session_id, not truncated
                          navigate(`/client-chat/${user.session_id}`);
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="flex-grow-1">
                          <div className="d-flex align-items-center mb-1">
                            <span className="badge bg-success me-2">●</span>
                            <strong>Session:</strong>
                            {/* Display truncated but NAVIGATE with full ID */}
                            <code className="ms-2 small">{user.session_id.substring(0, 30)}...</code>
                            <Badge bg="primary" className="ms-2">
                              Click to Chat
                            </Badge>
                          </div>
                          <div className="small text-muted">
                            <div>📍 IP: {user.ip}</div>
                            <div className="text-truncate" style={{ maxWidth: '500px' }}>
                              🖥️ {user.user_agent.substring(0, 80)}...
                            </div>
                          </div>
                        </div>
                        <Badge bg="success" pill>
                          {secondsAgo}s ago
                        </Badge>
                      </ListGroup.Item>
                    );
                  })}
                </ListGroup>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {/* Graph Section */}
      <Row className="mb-4">
        <Col>
          <Card className="shadow-sm">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Daily Analytics (Last 7 Days)</h5>
              {!statsLoading && dailyStats.length > 0 && (
                <small className="text-muted">
                  Total: {dailyStats.reduce((sum, s) => sum + s.visitors, 0)} visitors, {dailyStats.reduce((sum, s) => sum + s.chats, 0)}{' '}
                  chats
                </small>
              )}
            </Card.Header>
            <Card.Body>
              {statsLoading ? (
                <div className="d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
                  <Spinner animation="border" />
                  <span className="ms-2">Loading analytics...</span>
                </div>
              ) : dailyStats.length === 0 || dailyStats.every((s) => s.visitors === 0 && s.chats === 0) ? (
                <div className="d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
                  <div className="text-center text-muted">
                    <p className="mb-2">📊 No chat data yet</p>
                    <small>Start chatting to see analytics</small>
                  </div>
                </div>
              ) : (
                <div style={{ height: '300px' }}>
                  <Line data={chartData} options={chartOptions} />
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Chat History */}
      <Row>
        <Col md={4} xl={3}>
          <Card className="shadow-sm h-100">
            <Card.Header>
              <h5 className="mb-0">Chat Sessions ({sessions.length})</h5>
              <small className="text-muted">Click to view or chat</small>
            </Card.Header>
            <Card.Body style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              {sessions.length > 0 ? (
                <ListGroup>
                  {sessions.map((s) => (
                    <div key={s}>
                      <ListGroup.Item
                        action
                        active={selectedSession === s}
                        onClick={() => setSelectedSession(s)}
                        className="d-flex justify-content-between align-items-center mb-2"
                      >
                        <span className="text-truncate">{s.substring(0, 25)}...</span>
                        {selectedSession === s && <Badge bg="primary">Viewing</Badge>}
                      </ListGroup.Item>

                      {/* {selectedSession === s && (
                        <Button
                          variant="success"
                          size="sm"
                          className="w-100 mb-2"
                          onClick={() => navigate(`/client-chat/${s}`)}
                        >
                          💬 Open Admin Chat
                        </Button>
                      )}*/}
                    </div>
                  ))}
                </ListGroup>
              ) : (
                <p className="text-muted text-center mt-4">No sessions available</p>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={8} xl={9}>
          <Card className="shadow-sm h-100">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">{selectedSession ? `Chat: ${selectedSession.substring(0, 30)}...` : 'Select a session'}</h5>
              {/* {selectedSession && (
                <Button
                  variant="success"
                  size="sm"
                  onClick={() => navigate(`/client-chat/${selectedSession}`)}
                >
                  💬 Open in Admin Chat
                </Button>
              )}*/}
            </Card.Header>
            <Card.Body
              ref={chatContainerRef}
              className="chat-messages p-3"
              style={{ maxHeight: '70vh', overflowY: 'auto' }}
            className="chat-messages-container"
            >
              {loading ? (
                <div className="d-flex justify-content-center align-items-center h-100">
                  <Spinner animation="border" />
                  <span className="ms-2">Loading chats...</span>
                </div>
              ) : chats.length === 0 ? (
                <div className="text-center text-muted mt-5">
                  <p>Select a session to view chats</p>
                </div>
              ) : (
                chats.map((chat, i) => (
                  <div
                    key={i}
                    className={`chat-message mb-3 p-3 rounded ${
                      chat.role === 'user' ? 'bg-primary text-white ms-auto' : 'chat-bubble-bot border me-auto'
                    }`}
                    style={{ maxWidth: '75%' }}
                  >
                    <div className="mb-2">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {chat.message}
                      </ReactMarkdown>
                    </div>
                    <div className={`small mt-2 ${chat.role === 'user' ? 'text-white-50' : 'text-muted'}`}>
                      <div>
                        <strong>[{chat.role}]</strong> {new Date(chat.created_at).toLocaleString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                          timeZone: 'Asia/Kolkata',
                          timeZoneName: 'short'
                        })}
                      </div>
                      <div className="text-truncate">
                        {chat.country_code && `🌍 ${chat.country_code} | `}
                        🖥️ {chat.user_agent.substring(0, 50)}...
                      </div>
                    </div>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
}
