import PropTypes from 'prop-types';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import InputGroup from 'react-bootstrap/InputGroup';
import MainCard from 'components/MainCard';

export default function AuthLogin({ className }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [log, setLog] = useState('');

  const API = 'http://localhost:8000';

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setLog('❌ Please fill Username & Password');
      return;
    }

    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();

      if (data.success) {
        const id = data.client_id;
        if (remember) localStorage.setItem('client_id', id);
        else sessionStorage.setItem('client_id', id);

        // 🔹 Redirect to Datta Able dashboard
        window.location.href = '/demos/admin-templates/datta-able/react/free/';
      } else {
        setLog(`❌ ${data.message || 'Login failed'}`);
      }
    } catch (err) {
      setLog(`❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <MainCard className="mb-0">
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
          <InputGroup>
            <Form.Control
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </InputGroup>
        </Form.Group>

        {/* Remember me + Forgot Password */}
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

        <Button type="submit" className="mt-3 w-100">
          Login
        </Button>

        {log && (
          <p className={`mt-3 text-center ${log.startsWith('✅') ? 'text-success' : 'text-danger'}`}>
            {log}
          </p>
        )}

        {/* New Client register link */}
        <div className="mt-3 text-center">
          New Client? 
          <Link to="/register" className="d-block">
            Register Here
          </Link>
        </div>
      </Form>
    </MainCard>
  );
}

AuthLogin.propTypes = { className: PropTypes.string };
