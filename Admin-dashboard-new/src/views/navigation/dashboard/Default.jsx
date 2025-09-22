// react
import { useEffect, useState } from "react";
import axios from "axios";

// react-bootstrap
import Col from "react-bootstrap/Col";
import Row from "react-bootstrap/Row";
import Card from "react-bootstrap/Card";
import Spinner from "react-bootstrap/Spinner";
import ListGroup from "react-bootstrap/ListGroup";

// Utility to get latest client from storage
const getLatestClientId = () => {
  const localKeys = Object.keys(localStorage).filter((k) => k.startsWith("clientId_"));
  const sessionKeys = Object.keys(sessionStorage).filter((k) => k.startsWith("clientId_"));

  const allClientIds = [...localKeys, ...sessionKeys].map(
    (key) => localStorage.getItem(key) || sessionStorage.getItem(key)
  );

  return allClientIds.length ? allClientIds[allClientIds.length - 1] : "";
};

export default function DefaultPage() {
  const [selectedClient, setSelectedClient] = useState(getLatestClientId());
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [visitorCount, setVisitorCount] = useState(0);

  // fetch sessions on client select
  useEffect(() => {
    if (!selectedClient) return;

    axios
      .get(`http://localhost:8000/client/${selectedClient}/sessions`)
      .then((res) => {
        setSessions(res.data.sessions || []);
        setSelectedSession("");
        setChats([]);
        setVisitorCount(res.data.sessions?.length || 0);
      })
      .catch(() => {
        setSessions([]);
        setVisitorCount(0);
      });
  }, [selectedClient]);

  // fetch chats on session select
  useEffect(() => {
    if (!selectedClient || !selectedSession) return;

    setLoading(true);
    axios
      .get(
        `http://localhost:8000/client/${selectedClient}/chats?session_id=${selectedSession}`
      )
      .then((res) => setChats(res.data.chats || []))
      .catch(() => setChats([]))
      .finally(() => setLoading(false));
  }, [selectedClient, selectedSession]);

  return (
    <Row>
      {/* Sidebar (Sessions) */}
      <Col md={4} xl={3}>
        <Card className="shadow-sm h-100">
          <Card.Header>
            <h5 className="mb-0">Active Sessions</h5>
          </Card.Header>
          <Card.Body>
            {selectedClient && sessions.length > 0 ? (
              <ListGroup>
                {sessions.map((s) => (
                  <ListGroup.Item
                    key={s}
                    action
                    active={selectedSession === s}
                    onClick={() => setSelectedSession(s)}
                  >
                    Session {s}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            ) : (
              <p className="text-muted">No sessions available</p>
            )}

            {selectedClient && (
              <Card
                className={`mt-3 text-center shadow-sm border-0 ${
                  visitorCount > 5
                    ? "bg-success text-white"
                    : visitorCount > 0
                    ? "bg-warning text-dark"
                    : "bg-danger text-white"
                }`}
              >
                <Card.Body>
                  <h6 className="mb-1">Active Sessions</h6>
                  <h2 className="fw-bold mb-0">{visitorCount}</h2>
                </Card.Body>
              </Card>
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
          <Card.Body>
            {loading ? (
              <div className="d-flex justify-content-center align-items-center h-100">
                <Spinner animation="border" />
                <span className="ms-2">Loading chats...</span>
              </div>
            ) : chats.length === 0 ? (
              <p className="text-muted">Select a session to view chats</p>
            ) : (
              <div
                className="chat-messages p-2"
                style={{ maxHeight: "70vh", overflowY: "auto" }}
              >
                {chats.map((chat, i) => (
                  <div
                    key={i}
                    className={`chat-message mb-3 p-2 rounded ${
                      chat.role === "user"
                        ? "bg-primary text-white text-end"
                        : "bg-light border text-start"
                    }`}
                  >
                    <div>{chat.message}</div>
                    <div className="small text-muted mt-1">
                      [{chat.role}] {new Date(chat.created_at).toLocaleString()} | UA:{" "}
                      {chat.user_agent}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
}
