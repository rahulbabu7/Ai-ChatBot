import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../../../config';
import { useAuth } from '../../../hooks/useAuth';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Card from 'react-bootstrap/Card';
import Spinner from 'react-bootstrap/Spinner';
import Badge from 'react-bootstrap/Badge';

export default function Analytics() {
  const { token } = useAuth();
  const [days, setDays] = useState(30);
  const [topQuestions, setTopQuestions] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [totalUnanswered, setTotalUnanswered] = useState(0);
  const [loading, setLoading] = useState(false);

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    if (!token) return;
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [topRes, unansweredRes] = await Promise.all([
          axios.get(`${API_URL}/client/stats/top-questions?days=${days}&limit=15`, authHeaders),
          axios.get(`${API_URL}/client/stats/unanswered?days=${days}&limit=15`, authHeaders),
        ]);
        setTopQuestions(topRes.data.top_questions || []);
        setUnanswered(unansweredRes.data.unanswered_questions || []);
        setTotalUnanswered(unansweredRes.data.total_unanswered || 0);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [token, days]);

  const maxCount = topQuestions.length > 0 ? topQuestions[0].count : 1;

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h4 className="mb-0">Question Analytics</h4>
        <div className="d-flex align-items-center gap-2">
          <span className="text-muted small">Time range:</span>
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              className={`btn btn-sm ${days === d ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" />
          <p className="mt-2 text-muted">Loading analytics...</p>
        </div>
      ) : (
        <Row className="g-4">
          {/* Top Questions */}
          <Col md={7}>
            <Card className="shadow-sm h-100">
              <Card.Header className="border-bottom">
                <h5 className="mb-0">
                  Top Questions Asked
                  <Badge bg="secondary" className="ms-2">{topQuestions.length}</Badge>
                </h5>
                <small className="text-muted">Most frequent user messages in last {days} days</small>
              </Card.Header>
              <Card.Body style={{ maxHeight: '520px', overflowY: 'auto' }}>
                {topQuestions.length === 0 ? (
                  <div className="text-center text-muted py-5">
                    <p>No chat data yet</p>
                    <small>Questions will appear here once users start chatting</small>
                  </div>
                ) : (
                  <ol className="list-unstyled mb-0">
                    {topQuestions.map((q, i) => (
                      <li key={i} className="mb-3">
                        <div className="d-flex justify-content-between align-items-start mb-1">
                          <span className="small fw-medium text-dark" style={{ maxWidth: '85%' }}>
                            <span className="text-muted me-2">#{i + 1}</span>
                            {q.question}
                          </span>
                          <Badge bg="primary" pill>{q.count}x</Badge>
                        </div>
                        <div className="progress" style={{ height: '4px' }}>
                          <div
                            className="progress-bar bg-primary"
                            style={{ width: `${(q.count / maxCount) * 100}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </Card.Body>
            </Card>
          </Col>

          {/* Unanswered Questions */}
          <Col md={5}>
            <Card className="shadow-sm h-100">
              <Card.Header className="border-bottom">
                <h5 className="mb-0">
                  Unanswered Questions
                  {totalUnanswered > 0 && (
                    <Badge bg="danger" className="ms-2">{totalUnanswered}</Badge>
                  )}
                </h5>
                <small className="text-muted">Questions bot couldn't answer — add to knowledge base</small>
              </Card.Header>
              <Card.Body style={{ maxHeight: '520px', overflowY: 'auto' }}>
                {unanswered.length === 0 ? (
                  <div className="text-center text-muted py-5">
                    <p className="text-success">No unanswered questions!</p>
                    <small>Your bot is handling all queries</small>
                  </div>
                ) : (
                  <ul className="list-unstyled mb-0">
                    {unanswered.map((q, i) => (
                      <li
                        key={i}
                        className="d-flex justify-content-between align-items-start p-2 mb-2 rounded border-start border-danger border-3 bg-light"
                      >
                        <span className="small text-dark" style={{ maxWidth: '80%' }}>
                          {q.question}
                        </span>
                        <Badge bg="danger" pill>{q.count}x</Badge>
                      </li>
                    ))}
                  </ul>
                )}
                {totalUnanswered > 15 && (
                  <p className="text-muted small mt-2 text-center">
                    Showing top 15 of {totalUnanswered} unanswered questions
                  </p>
                )}
              </Card.Body>
            </Card>
          </Col>

          {/* Summary row */}
          <Col xs={12}>
            <Row className="g-3">
              <Col sm={4}>
                <Card className="text-center shadow-sm border-0 bg-info bg-opacity-10">
                  <Card.Body>
                    <h6 className="text-muted mb-1">Unique Questions</h6>
                    <h3 className="fw-bold mb-0 text-info">{topQuestions.length}</h3>
                    <small className="text-muted">in last {days} days</small>
                  </Card.Body>
                </Card>
              </Col>
              <Col sm={4}>
                <Card className="text-center shadow-sm border-0 bg-success bg-opacity-10">
                  <Card.Body>
                    <h6 className="text-muted mb-1">Total Asks</h6>
                    <h3 className="fw-bold mb-0 text-success">
                      {topQuestions.reduce((s, q) => s + q.count, 0)}
                    </h3>
                    <small className="text-muted">user messages</small>
                  </Card.Body>
                </Card>
              </Col>
              <Col sm={4}>
                <Card className="text-center shadow-sm border-0 bg-danger bg-opacity-10">
                  <Card.Body>
                    <h6 className="text-muted mb-1">Unanswered Rate</h6>
                    <h3 className="fw-bold mb-0 text-danger">
                      {topQuestions.reduce((s, q) => s + q.count, 0) > 0
                        ? `${Math.round((totalUnanswered / topQuestions.reduce((s, q) => s + q.count, 0)) * 100)}%`
                        : '—'}
                    </h3>
                    <small className="text-muted">questions without answers</small>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Col>
        </Row>
      )}
    </div>
  );
}
