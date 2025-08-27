import { useState } from "react";
import { Link } from "react-router-dom";
import "./Auth.css";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [log, setLog] = useState("");

  const handleSubmit = () => {
    if (!email.trim()) {
      setLog("❌ Please enter your email");
      return;
    }
    setLog("✅ If this email exists, password reset instructions will be sent.");
    setEmail("");
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">Forgot Password</h2>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <button className="auth-btn" onClick={handleSubmit}>
          Send Reset Link
        </button>

        <p className="switch-link">
          Remembered your password? <Link to="/login">Login</Link>
        </p>

        {log && (
          <p
            className={`auth-log ${
              log.startsWith("✅") ? "log-success" : log.startsWith("❌") ? "log-error" : ""
            }`}
          >
            {log}
          </p>
        )}
      </div>
    </div>
  );
};

export default ForgotPassword;
