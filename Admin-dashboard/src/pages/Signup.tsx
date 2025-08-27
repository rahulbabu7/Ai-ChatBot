// src/pages/Signup.tsx
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Auth.css";

const API = "http://localhost:8000";

const Signup = () => {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mobile, setMobile] = useState("");
  const [email, setEmail] = useState("");
  const [log, setLog] = useState("");
  const navigate = useNavigate();

  const handleSignup = async () => {
    if (!name || !username || !password || !mobile || !email) {
      setLog("❌ Please fill all fields");
      return;
    }

    try {
      const res = await fetch(`${API}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: "client", // Always signup as client
          name,
          username,
          password,
          mobile,
          email
        }),
      });
      const data = await res.json();

      if (data.success) {
        setLog("✅ Signup successful! Please login.");
        navigate("/login");
      } else {
        setLog(`❌ ${data.message || "Signup failed"}`);
      }
    } catch (err: any) {
      setLog(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">User Sign Up</h2>

        {/* Name */}
        <label htmlFor="name">Name</label>
        <input
          id="name"
          type="text"
          placeholder="Full Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        {/* Username */}
        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          placeholder="Choose a username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        {/* Password */}
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="Enter password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {/* Mobile */}
        <label htmlFor="mobile">Mobile No</label>
        <input
          id="mobile"
          type="tel"
          placeholder="Enter mobile number"
          value={mobile}
          onChange={(e) => setMobile(e.target.value)}
        />

        {/* Email */}
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          placeholder="Enter email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <button className="auth-btn" onClick={handleSignup}>
          Signup
        </button>

        <p className="switch-link">
          Already have an account? <Link to="/login">Login</Link>
        </p>

        {log && <p className="auth-log">{log}</p>}
      </div>
    </div>
  );
};

export default Signup;
