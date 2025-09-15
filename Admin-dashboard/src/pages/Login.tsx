import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Auth.css";

const API = "http://localhost:8000";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [log, setLog] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    // Check if the user is already logged in from storage
    const storedClientId = localStorage.getItem("client_id") || sessionStorage.getItem("client_id");
    if (storedClientId) {
      navigate(`/dashboard/${storedClientId}`);
    }
  }, [navigate]);

  const handleLogin = async () => {
    if (!username || !password) {
      setLog("❌ Please fill Username & Password");
      return;
    }
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
        }),
      });
      const data = await res.json();

      if (data.success) {
        const id = data.client_id;
        if (remember) {
          localStorage.setItem("client_id", id);
        } else {
          sessionStorage.setItem("client_id", id);
        }
        navigate(`/dashboard/${id}`); // ✅ redirect with clientId in URL
      } else {
        setLog(`❌ ${data.message || "Login failed"}`);
      }
    } catch (err: any) {
      setLog(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div className="auth-container">
      {/* Client Login Card */}
      <div className="auth-card">
        <h2 className="auth-title">Client Login</h2>

        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          placeholder="Enter username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="Enter password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <div className="auth-options">
          <label>
            <input
              type="checkbox"
              checked={remember}
              onChange={() => setRemember(!remember)}
            />
            Remember Me
          </label>
          <Link to="/forgot-password" className="forgot-link">
            Forgot Password?
          </Link>
        </div>

        <button className="auth-btn" onClick={handleLogin}>
          Login
        </button>
      </div>

      {/* New User Signup Card */}
      <div className="auth-card">
        <h2 className="auth-title">New Client?</h2>
        <p className="switch-link">Sign up and create your account</p>
        <Link to="/signup">
          <button className="auth-btn">Sign Up Here!</button>
        </Link>
      </div>

      {log && <p className="auth-log">{log}</p>}
    </div>
  );
};

export default Login;
