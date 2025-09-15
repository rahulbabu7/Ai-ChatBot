// react
import { useEffect, useState } from "react";
import axios from "axios";

// react-bootstrap
import Col from "react-bootstrap/Col";
import Row from "react-bootstrap/Row";
import Card from "react-bootstrap/Card";
import Spinner from "react-bootstrap/Spinner";
import ListGroup from "react-bootstrap/ListGroup";

export default function DefaultPage() {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState("");
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [visitorCount, setVisitorCount] = useState(0);

  // fetch clients
  useEffect(() => {
    axios
      .get("http://localhost:8000/admin/clients")
      .then((res) => setClients(res.data.clients || []))
      .catch(() => setClients([]));
  }, []);

  // fetch sessions on client select
  useEffect(() => {
    if (selectedClient) {
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
    } else {
      setVisitorCount(0);
      setSessions([]);
      setChats([]);
      setSelectedSession("");
    }
  }, [selectedClient]);

  // fetch chats on session select
  useEffect(() => {
    if (selectedClient && selectedSession) {
      setLoading(true);
      axios
        .get(
          `http://localhost:8000/client/${selectedClient}/chats?session_id=${selectedSession}`
        )
        .then((res) => setChats(res.data.chats || []))
        .catch(() => setChats([]))
        .finally(() => setLoading(false));
    }
  }, [selectedClient, selectedSession]);

  return (
    <Row>
      {/* Sidebar (Clients + sessions) */}
      <Col md={4} xl={3}>
        <Card className="shadow-sm h-100">
          <Card.Header>
            <h5 className="mb-0">Clients</h5>
          </Card.Header>
          <Card.Body>
            <select
              id="clientSelect"
              className="form-select mb-3"
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
            >
              <option value="">-- Choose Client --</option>
              {clients.map((c) => (
                <option key={c.client_id} value={c.client_id}>
                  {c.name} ({c.username})
                </option>
              ))}
            </select>

            {selectedClient && (
              <Card
                className={`mb-3 text-center shadow-sm border-0 ${
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

            {sessions.length > 0 && (
              <>
                <h6 className="mb-2">Chat Sessions</h6>
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
              </>
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
                      [{chat.role}] {new Date(chat.created_at).toLocaleString()}{" "}
                      | UA: {chat.user_agent}
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
