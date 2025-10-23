import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { API_URL } from '../../../config';

// react-bootstrap
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Card from 'react-bootstrap/Card';
import Spinner from 'react-bootstrap/Spinner';
import ListGroup from 'react-bootstrap/ListGroup';

// Chart.js for graphs
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function DefaultPage() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState('');
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalSessions, setTotalSessions] = useState(0);
  const [activeSessions, setActiveSessions] = useState(0);
  const [dailyStats, setDailyStats] = useState([]);
  const [statsLoading, setStatsLoading] = useState(false);

  const chatContainerRef = useRef(null);

  // Get JWT token from storage
  const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');

  // Fetch sessions on mount and set up polling for active sessions
  useEffect(() => {
    if (!token) return;

    const fetchSessions = () => {
      axios
        .get(`${API_URL}/client/sessions/me`, {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        })
        .then((res) => {
          const sessionsData = res.data.sessions || [];
          setSessions(sessionsData);
          setSelectedSession('');
          setChats([]);
          setTotalSessions(sessionsData.length);
          
          // Calculate active sessions (sessions with activity in last 5 minutes)
          const now = new Date();
          const activeThreshold = 5 * 60 * 1000; // 5 minutes in milliseconds
          
          const activeCount = sessionsData.filter(session => {
            const lastActivity = session.last_activity ? new Date(session.last_activity) : 
                              session.created_at ? new Date(session.created_at) : now;
            return (now - lastActivity) < activeThreshold;
          }).length;
          
          setActiveSessions(activeCount);
        })
        .catch(() => {
          setSessions([]);
          setTotalSessions(0);
          setActiveSessions(0);
        });
    };

    // Initial fetch
    fetchSessions();

    // Set up polling for active sessions every 30 seconds
    const intervalId = setInterval(fetchSessions, 30000);

    // Cleanup interval on component unmount
    return () => clearInterval(intervalId);
  }, [token]);

  // Fetch daily stats for the graph
  useEffect(() => {
    if (!token) return;

    setStatsLoading(true);
    axios
      .get(`${API_URL}/client/stats/daily`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      })
      .then((res) => {
        setDailyStats(res.data.daily_stats || []);
      })
      .catch(() => {
        setDailyStats([]);
      })
      .finally(() => {
        setStatsLoading(false);
      });
  }, [token]);

  // Fetch chats whenever a session is selected
  useEffect(() => {
    if (!token || !selectedSession) return;

    setLoading(true);
    axios
      .get(
        `${API_URL}/client/chats/me?session_id=${selectedSession}`,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        }
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

  // Generate mock data if API doesn't have daily stats endpoint
  const generateMockDailyData = () => {
    const days = 7;
    const mockData = [];
    const today = new Date();
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      
      mockData.push({
        date: date.toISOString().split('T')[0],
        visitors: Math.floor(Math.random() * 50) + 10,
        chats: Math.floor(Math.random() * 30) + 5,
      });
    }
    
    return mockData;
  };

  // Prepare chart data
  const chartData = {
    labels: (dailyStats.length > 0 ? dailyStats : generateMockDailyData()).map(stat => {
      const date = new Date(stat.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'Daily Visitors',
        data: (dailyStats.length > 0 ? dailyStats : generateMockDailyData()).map(stat => stat.visitors),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Daily Chats',
        data: (dailyStats.length > 0 ? dailyStats : generateMockDailyData()).map(stat => stat.chats),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.4,
        fill: true,
      }
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Daily Visitors & Chats',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 10,
        },
      },
    },
  };

  if (!token) {
    return <p className="text-center mt-5">❌ You must log in to view this page.</p>;
  }

  return (
    <>
      {/* Stats Cards - Horizontal at the top */}
      <Row className="mb-4">
        <Col md={4} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-info text-white">
            <Card.Body className="d-flex flex-column justify-content-center">
              <h6 className="mb-1">Total Sessions</h6>
              <h2 className="fw-bold mb-0">{totalSessions}</h2>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-success text-white">
            <Card.Body className="d-flex flex-column justify-content-center">
              <h6 className="mb-1">Active Sessions</h6>
              <h2 className="fw-bold mb-0">{activeSessions}</h2>
              <small className="opacity-75">Last 5 minutes</small>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="text-center shadow-sm border-0 h-100 bg-warning text-dark">
            <Card.Body className="d-flex flex-column justify-content-center">
              <h6 className="mb-1">Daily Visitors</h6>
              <h2 className="fw-bold mb-0">
                {dailyStats.length > 0 
                  ? dailyStats[dailyStats.length - 1]?.visitors || 0
                  : generateMockDailyData()[generateMockDailyData().length - 1]?.visitors || 0
                }
              </h2>
              <small className="opacity-75">Today</small>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Graph Section */}
      <Row className="mb-4">
        <Col>
          <Card className="shadow-sm">
            <Card.Header>
              <h5 className="mb-0">Daily Analytics</h5>
            </Card.Header>
            <Card.Body>
              {statsLoading ? (
                <div className="d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
                  <Spinner animation="border" />
                  <span className="ms-2">Loading analytics...</span>
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

      {/* Main Content */}
      <Row>
        {/* Sidebar (Sessions) */}
        <Col md={4} xl={3}>
          <Card className="shadow-sm h-100">
            <Card.Header>
              <h5 className="mb-0">Sessions</h5>
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
    </>
  );
}
