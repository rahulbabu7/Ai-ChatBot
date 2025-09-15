// src/views/auth/forgot-password/ForgotPassword.jsx

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

// react-bootstrap
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';

// project-imports
import MainCard from 'components/MainCard';

const API = "http://localhost:8000"; // replace with your API if needed

export default function AuthForgotPassword({ link }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [log, setLog] = useState('');

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!email) {
      setLog('❌ Please enter your email');
      return;
    }

    try {
      const res = await fetch(`${API}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      const data = await res.json();

      if (data.success) {
        setLog('✅ Password reset link sent! Check your email.');
      } else {
        setLog(`❌ ${data.message || 'Failed to send reset link'}`);
      }
    } catch (err) {
      setLog(`❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="auth-main">
      <div className="auth-wrapper v1">
        <div className="auth-form">
          <div className="position-relative">

            {/* Decorative background shapes */}
            <div className="auth-bg">
              <span className="r"></span>
              <span className="r s"></span>
              <span className="r s"></span>
              <span className="r"></span>
            </div>

            {/* Forgot Password Card */}
            <MainCard className="mb-0">
              <h4 className="text-center f-w-500 mt-4 mb-3">Forgot Password</h4>
              <Form onSubmit={handleForgotPassword}>
                <Form.Group className="mb-3">
                  <Form.Control
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </Form.Group>

                <div className="text-center mt-3">
                  <Button type="submit" className="shadow px-sm-4">Send Reset Link</Button>
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
                  Remembered your password? <Link to={link || '/login'} className="link-primary">Login</Link>
                </p>
              </Form>
            </MainCard>

          </div>
        </div>
      </div>
    </div>
  );
}
