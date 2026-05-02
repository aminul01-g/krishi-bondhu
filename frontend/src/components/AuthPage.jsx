import React, { useState } from 'react';
import './Auth.css';

export default function AuthPage({ onLogin }) {
  const [authMode, setAuthMode] = useState('signup'); // 'signup' or 'login'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simulate successful login
    localStorage.setItem('krishi_auth_token', 'mock_token_123');
    onLogin();
  };

  const handleSocialLogin = (provider) => {
    // Simulate social login
    localStorage.setItem('krishi_auth_token', `mock_token_${provider}`);
    onLogin();
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>{authMode === 'signup' ? 'Create your account' : 'Welcome back'}</h2>
          <p>
            {authMode === 'signup' 
              ? 'Join KrishiBondhu to access intelligent farming tools.' 
              : 'Log in to continue managing your farm.'}
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Email address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="farmer@example.com"
              required 
            />
          </div>
          <div className="input-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required 
            />
          </div>
          <button type="submit" className="auth-submit-btn">
            {authMode === 'signup' ? 'Sign up' : 'Log in'}
          </button>
        </form>

        <div className="auth-divider">
          <span>or continue with</span>
        </div>

        <div className="social-login-grid">
          <button onClick={() => handleSocialLogin('google')} className="social-btn">
            <span className="social-icon">G</span> Google
          </button>
          <button onClick={() => handleSocialLogin('apple')} className="social-btn">
            <span className="social-icon"></span> Apple
          </button>
          <button onClick={() => handleSocialLogin('phone')} className="social-btn phone-btn">
            <span className="social-icon">📱</span> Phone Number
          </button>
        </div>

        <div className="auth-footer">
          {authMode === 'signup' ? (
            <p>Already have an account? <button onClick={() => setAuthMode('login')} className="text-btn">Log in</button></p>
          ) : (
            <p>Don't have an account? <button onClick={() => setAuthMode('signup')} className="text-btn">Sign up</button></p>
          )}
        </div>
      </div>
    </div>
  );
}
