import AuthLoginForm from 'sections/auth/AuthLogin';

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

const API = "http://localhost:8000";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [log, setLog] = useState("");

  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!username || !password) {
      setLog("❌ Please fill Username & Password");
      return;
    }

    try {
      const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();

      if (data.success) {
        const id = data.client_id;
        if (remember) localStorage.setItem("client_id", id);
        else sessionStorage.setItem("client_id", id);

        // 🔹 Redirect to dashboard
        window.location.href = "/demos/admin-templates/datta-able/react/free#!";
        // or using React Router (if you want SPA style navigation)
        // navigate("/demos/admin-templates/datta-able/react/free", { replace: true });
      } else {
        setLog(`❌ ${data.message || "Login failed"}`);
      }
    } catch (err) {
      setLog(`❌ Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  return (
    <div className="auth-main">
      <div className="auth-wrapper v1">
        <div className="auth-form">
          <div className="position-relative">
            <div className="auth-bg">
              <span className="r"></span>
              <span className="r s"></span>
              <span className="r s"></span>
              <span className="r"></span>
            </div>

            <div className="card shadow">
              <div className="card-body">
                <h3 className="mb-4 text-center">Client Login</h3>

                <div className="form-group mb-3">
                  <label htmlFor="username">Username</label>
                  <input
                    id="username"
                    type="text"
                    className="form-control"
                    placeholder="Enter username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>

                <div className="form-group mb-3">
                  <label htmlFor="password">Password</label>
                  <input
                    id="password"
                    type="password"
                    className="form-control"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                <div className="d-flex justify-content-between align-items-center mb-3">
                  <div className="form-check">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      id="remember"
                      checked={remember}
                      onChange={() => setRemember((v) => !v)}
                    />
                    <label className="form-check-label" htmlFor="remember">
                      Remember Me
                    </label>
                  </div>
                  <Link to="/forgot-password" className="text-primary">
                    Forgot Password?
                  </Link>
                </div>

                <button className="btn btn-primary w-100" onClick={handleLogin}>
                  Login
                </button>

                {log && (
                  <p
                    className={`mt-3 text-center ${
                      log.startsWith("✅") ? "text-success" : "text-danger"
                    }`}
                  >
                    {log}
                  </p>
                )}

                <hr />

                <div className="text-center">
                  <p className="mb-2">New Client?</p>
                  <Link to="/register">
                    <button className="btn btn-outline-primary w-100">
                      Sign Up Here!
                    </button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}