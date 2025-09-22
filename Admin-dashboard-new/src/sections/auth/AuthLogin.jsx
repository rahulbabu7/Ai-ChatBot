import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import MainCard from 'components/MainCard';

export default function AuthLogin({ className }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [log, setLog] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const API = 'http://localhost:8000';
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();

    if (!username || !password) {
      setLog('❌ Please fill Username & Password');
      return;
    }

    setIsLoading(true);
    setLog('Logging in...');

    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (data.success) {
        const { client_id, chatbot_key } = data;

        // Clear old credentials
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('clientId_') || key.startsWith('chatbotKey_')) localStorage.removeItem(key);
        });
        Object.keys(sessionStorage).forEach(key => {
          if (key.startsWith('clientId_') || key.startsWith('chatbotKey_')) sessionStorage.removeItem(key);
        });

        // Store credentials per client
        const storage = remember ? localStorage : sessionStorage;
        storage.setItem(`clientId_${client_id}`, client_id);
        storage.setItem(`chatbotKey_${client_id}`, chatbot_key);

        setLog('✅ Login successful! Redirecting...');
        setTimeout(() => {
          navigate(`/`, { replace: true });
        }, 500);
      } else {
        setLog(`❌ ${data.message || 'Login failed'}`);
      }
    } catch (err) {
      setLog(`❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="d-flex justify-content-center align-items-center min-vh-100">
      <MainCard className="w-100" style={{ maxWidth: '400px' }}>
        <Form onSubmit={handleLogin}>
          <h4 className={`text-center f-w-500 mt-4 mb-3 ${className}`}>Login</h4>

          <Form.Group className="mb-3" controlId="formUsername">
            <Form.Control
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </Form.Group>

          <Form.Group className="mb-3" controlId="formPassword">
            <Form.Control
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Form.Group>

          <div className="d-flex justify-content-between align-items-center mb-3">
            <Form.Check
              type="checkbox"
              label="Remember me"
              checked={remember}
              onChange={() => setRemember(!remember)}
            />
            <Link to="/forgot-password" className="text-primary">
              Forgot Password?
            </Link>
          </div>

          <Button type="submit" className="mt-3 w-100" disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Login'}
          </Button>

          {log && (
            <p
              className={`mt-3 text-center ${
                log.startsWith('✅') ? 'text-success' : 'text-danger'
              }`}
            >
              {log}
            </p>
          )}

          <div className="mt-3 text-center">
            New Client? 
            <Link to="/register" className="d-block">
              Register Here
            </Link>
          </div>
        </Form>
      </MainCard>
    </div>
  );
}

AuthLogin.propTypes = { className: PropTypes.string };
