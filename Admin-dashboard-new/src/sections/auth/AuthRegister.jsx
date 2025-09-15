import { useState } from 'react';
import PropTypes from 'prop-types';
import { useNavigate, Link } from 'react-router-dom';

// react-bootstrap
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';

// project-imports
import MainCard from 'components/MainCard';

const API = "http://localhost:8000"; // Change this to your API if needed

export default function AuthRegister({ link }) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    password: '',
    mobile: '',
    email: ''
  });
  const [log, setLog] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    const { name, username, password, mobile, email } = formData;

    if (!name || !username || !password || !mobile || !email) {
      setLog('❌ Please fill all fields');
      return;
    }

    try {
      const res = await fetch(`${API}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: 'client', name, username, password, mobile, email })
      });

      const data = await res.json();

      if (data.success) {
        setLog('✅ Signup successful! Redirecting to login...');
        setTimeout(() => navigate(link || '/login'), 1500);
      } else {
        setLog(`❌ ${data.message || 'Signup failed'}`);
      }
    } catch (err) {
      setLog(`❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <MainCard className="mb-0">
      <h4 className="text-center f-w-500 mt-4 mb-3">Sign up</h4>
      <Form onSubmit={handleSignup}>
        <Form.Group className="mb-3">
          <Form.Control
            type="text"
            name="name"
            placeholder="Full Name"
            value={formData.name}
            onChange={handleChange}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Control
            type="text"
            name="username"
            placeholder="Username"
            value={formData.username}
            onChange={handleChange}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Control
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleChange}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Control
            type="tel"
            name="mobile"
            placeholder="Mobile Number"
            value={formData.mobile}
            onChange={handleChange}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Control
            type="email"
            name="email"
            placeholder="Email"
            value={formData.email}
            onChange={handleChange}
          />
        </Form.Group>

        <div className="text-center mt-3">
          <Button type="submit" className="shadow px-sm-4">Sign up</Button>
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
          Already have an account? <Link to={link || '/login'} className="link-primary">Login</Link>
        </p>
      </Form>
    </MainCard>
  );
}

AuthRegister.propTypes = {
  link: PropTypes.string
};
