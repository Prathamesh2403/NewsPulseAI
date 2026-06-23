import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { setToken, getToken, removeToken } from '../utils/auth';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const PulseIcon = ({ size = 40 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="32" height="32" rx="8" fill="#3B82F6" />
    <path
      d="M7 16h3.5l2.5-6 3.5 12 2.5-8 2.5 4H25"
      stroke="white"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const SpinnerIcon = () => (
  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/';

  useEffect(() => {
    const checkToken = async () => {
      const token = getToken();
      if (!token) return;

      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/verify`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (res.ok) {
          navigate(from, { replace: true });
        } else {
          removeToken();
        }
      } catch (err) {
        console.error("Token verification failed", err);
        removeToken();
      }
    };
    
    checkToken();
  }, [navigate, from]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Invalid credentials');
        }
        throw new Error('An error occurred during login');
      }

      const data = await res.json();
      setToken(data.access_token);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <style>{`
        .login-container {
          width: 100vw;
          height: 100vh;
          display: flex;
          flex-direction: row;
          overflow: hidden;
          background: #0a0a0f;
          font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .left-panel {
          width: 60%;
          height: 100%;
          position: relative;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          padding: 60px;
          z-index: 1;
        }
        .left-bg {
          position: absolute;
          inset: 0;
          background-image: url("/assets/login_bg.jpg");
          background-size: cover;
          background-position: center;
          z-index: -2;
        }
        .left-overlay {
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(6, 10, 35, 0.75) 0%, rgba(15, 25, 70, 0.65) 50%, rgba(6, 10, 35, 0.80) 100%);
          z-index: -1;
        }
        .left-top {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .left-top-text {
          font-size: 32px;
          color: white;
          font-weight: 700;
        }
        .left-middle {
          margin-top: auto;
          margin-bottom: auto;
        }
        .left-headline {
          font-size: 48px;
          color: white;
          font-weight: 700;
          line-height: 1.2;
          white-space: pre-line;
        }
        .left-subtitle {
          font-size: 16px;
          color: rgba(255,255,255,0.65);
          margin-top: 16px;
          max-width: 480px;
          line-height: 1.5;
        }
        .left-bottom {
          margin-top: auto;
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .feature-pill {
          background: rgba(255,255,255,0.1);
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 999px;
          padding: 8px 16px;
          font-size: 13px;
          color: rgba(255,255,255,0.8);
          display: inline-flex;
          align-items: center;
        }
        .right-panel {
          width: 40%;
          height: 100%;
          background: #0f0f1a;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 48px;
        }
        .login-card {
          width: 100%;
          max-width: 380px;
          display: flex;
          flex-direction: column;
        }
        .right-top {
          margin-bottom: 36px;
        }
        .right-title {
          font-size: 24px;
          color: white;
          font-weight: 600;
          margin-top: 12px;
        }
        .right-subtitle {
          font-size: 14px;
          color: rgba(255,255,255,0.5);
          margin-top: 4px;
        }
        .form-section {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .field-group {
          display: flex;
          flex-direction: column;
        }
        .field-label {
          font-size: 12px;
          color: rgba(255,255,255,0.6);
          font-weight: 500;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .input-field {
          width: 100%;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 10px;
          padding: 14px 16px;
          font-size: 15px;
          color: white;
          outline: none;
          transition: border-color 0.2s, background 0.2s;
          box-sizing: border-box;
        }
        .input-field:focus {
          border-color: #3B82F6;
          background: rgba(59, 130, 246, 0.08);
        }
        .input-field::placeholder {
          color: rgba(255,255,255,0.25);
        }
        .submit-btn {
          width: 100%;
          padding: 14px;
          background: #2563EB;
          color: white;
          font-size: 15px;
          font-weight: 600;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          transition: background 0.2s, transform 0.1s;
          margin-top: 8px;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 8px;
          box-sizing: border-box;
        }
        .submit-btn:hover:not(:disabled) {
          background: #1D4ED8;
        }
        .submit-btn:active:not(:disabled) {
          transform: scale(0.99);
        }
        .submit-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        .error-msg {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          padding: 10px 14px;
          color: #FCA5A5;
          font-size: 13px;
          text-align: center;
          animation: fadeIn 0.3s ease-in-out;
          margin-bottom: 20px;
        }
        .bottom-footer {
          margin-top: 40px;
          text-align: center;
          font-size: 12px;
          color: rgba(255,255,255,0.2);
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 768px) {
          .left-panel {
            display: none;
          }
          .right-panel {
            width: 100vw;
            position: relative;
            background: transparent;
          }
          .right-panel::before {
            content: "";
            position: absolute;
            inset: 0;
            background-image: url("/assets/login_bg.jpg");
            background-size: cover;
            background-position: center;
            filter: blur(8px);
            z-index: -2;
          }
          .right-panel::after {
            content: "";
            position: absolute;
            inset: 0;
            background: rgba(10, 10, 20, 0.88);
            z-index: -1;
          }
        }
      `}</style>
      <div className="login-container">
        <div className="left-panel">
          <div className="left-bg" />
          <div className="left-overlay" />
          
          <div className="left-top">
            <PulseIcon size={40} />
            <span className="left-top-text">NewsPulse AI</span>
          </div>

          <div className="left-middle">
            <div className="left-headline">
              {`Your AI-Powered\nTech Intelligence\nPlatform`}
            </div>
            <div className="left-subtitle">
              Stay ahead with real-time AI and tech news, community insights, and intelligent analysis.
            </div>
          </div>

          <div className="left-bottom">
            <div className="feature-pill">⚡ Real-time News</div>
            <div className="feature-pill">🤖 AI Chat Assistant</div>
            <div className="feature-pill">📊 Trend Analytics</div>
          </div>
        </div>

        <div className="right-panel">
          <div className="login-card">
            <div className="right-top">
              <PulseIcon size={32} />
              <div className="right-title">Welcome back</div>
              <div className="right-subtitle">Sign in to your dashboard</div>
            </div>

            {error && <div className="error-msg">{error}</div>}

            <form className="form-section" onSubmit={handleSubmit}>
              <div className="field-group">
                <label className="field-label" htmlFor="username">
                  Username
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="input-field"
                  placeholder="Enter admin username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="input-field"
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <button type="submit" disabled={loading} className="submit-btn">
                {loading && <SpinnerIcon />}
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="bottom-footer">
              © 2026 NewsPulse AI · All rights reserved
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default LoginPage;
