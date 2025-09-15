import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// react-bootstrap
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';

// project-imports
import MainCard from 'components/MainCard';

const API = "http://localhost:8000"; // Change if needed

export default function AuthForgotPassword({ link }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [log, setLog] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!email) {
      setLog('❌ Please enter your email');
      return;
    }

    try {
      const res = await fetch(`${API}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();

      if (data.success) {
        setLog('✅ Password reset link sent! Check your email.');
        setTimeout(() => navigate(link || '/login'), 2000);
      } else {
        setLog(`❌ ${data.message || 'Failed to send reset link'}`);
      }
    } catch (err) {
      setLog(`❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <MainCard className="mb-0">
      <h4 className="text-center f-w-500 mt-4 mb-3">Forgot Password</h4>
      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-3">
          <Form.Control
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Form.Group>

        <div className="text-center mt-3">
          <Button type="submit" className="shadow px-sm-4">
            Send Reset Link
          </Button>
        </div>

        {log && (
          <p
            className="mt-3 text-center"
            style={{ color: log.startsWith('✅') ? '#16a34a' : '#e11d48' }}
          >
            {log}
          </p>
        )}

        <p className="mt-3 text-center">
          Remembered your password? <a href={link || '/login'} className="link-primary">Login</a>
        </p>
      </Form>
    </MainCard>
  );
}
