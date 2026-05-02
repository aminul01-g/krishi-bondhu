import React, { useState } from 'react';
import './Auth.css';

export default function AuthPage({ onLogin }) {
  const [authMode, setAuthMode] = useState('login'); // Default to login for better UX
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Simulate API call
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      if (email && password.length >= 6) {
        localStorage.setItem('krishi_auth_token', 'mock_token_' + Math.random().toString(36).substr(2));
        onLogin();
      } else {
        setError('Please enter a valid email and password (min 6 characters).');
      }
    } catch (err) {
      setError('Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSocialLogin = async (provider) => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      localStorage.setItem('krishi_auth_token', `mock_token_${provider}_${Math.random().toString(36).substr(2)}`);
      onLogin();
    } catch (err) {
      setError(`${provider} login failed.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>{authMode === 'signup' ? 'Create Account' : 'Welcome Back'}</h2>
          <p>
            {authMode === 'signup' 
              ? 'Join KrishiBondhu to access intelligent farming tools.' 
              : 'Log in to continue managing your farm.'}
          </p>
        </div>

        {error && <div className="error-message" style={{ marginBottom: '1.5rem', textAlign: 'center' }}>{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              disabled={loading}
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
              disabled={loading}
              required 
            />
          </div>
          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? (authMode === 'signup' ? 'Creating...' : 'Logging in...') : (authMode === 'signup' ? 'Sign Up' : 'Log In')}
          </button>
        </form>

        <div className="auth-divider">
          <span>or continue with</span>
        </div>

        <div className="social-login-grid">
          <button onClick={() => handleSocialLogin('google')} className="social-btn" disabled={loading} title="Google">
            <span>G</span>
          </button>
          <button onClick={() => handleSocialLogin('apple')} className="social-btn" disabled={loading} title="Apple">
            <span></span>
          </button>
          <button onClick={() => handleSocialLogin('phone')} className="social-btn" disabled={loading} title="Phone">
            <span>📱</span>
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
