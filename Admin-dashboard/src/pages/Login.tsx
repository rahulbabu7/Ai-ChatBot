// src/pages/Login.tsx
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Auth.css";

const API = "http://localhost:8000";

const Login = () => {
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [adminRemember, setAdminRemember] = useState(false);
  const [log, setLog] = useState("");
  const navigate = useNavigate();

  // Handle Admin login
  const handleAdminLogin = async () => {
    if (!adminUsername || !adminPassword) {
      setLog("❌ Please fill Admin Username & Password");
      return;
    }
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: "admin",
          username: adminUsername,
          password: adminPassword,
        }),
      });
      const data = await res.json();

      if (data.token) {
        if (adminRemember) {
          localStorage.setItem("token", data.token);
          localStorage.setItem("role", "admin");
        } else {
          sessionStorage.setItem("token", data.token);
          sessionStorage.setItem("role", "admin");
        }
        navigate("/admin");
      } else {
        setLog(`❌ ${data.message || "Admin login failed"}`);
      }
    } catch (err: any) {
      setLog(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div className="auth-container">
      {/* Admin Login Card */}
      <div className="auth-card">
        <h2 className="auth-title">Admin Login</h2>

        <label htmlFor="adminUsername">Username</label>
        <input
          id="adminUsername"
          type="text"
          placeholder="Enter admin username"
          value={adminUsername}
          onChange={(e) => setAdminUsername(e.target.value)}
        />

        <label htmlFor="adminPassword">Password</label>
        <input
          id="adminPassword"
          type="password"
          placeholder="Enter admin password"
          value={adminPassword}
          onChange={(e) => setAdminPassword(e.target.value)}
        />

        <div className="auth-options">
          <label>
            <input
              type="checkbox"
              checked={adminRemember}
              onChange={() => setAdminRemember(!adminRemember)}
            />
            Remember Me
          </label>
          <Link to="/forgot-password" className="forgot-link">
            Forgot Password?
          </Link>
        </div>

        <button className="auth-btn" onClick={handleAdminLogin}>
          Login as Admin
        </button>
      </div>

      {/* New User Signup Card */}
      <div className="auth-card">
        <h2 className="auth-title">New User?</h2>
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
