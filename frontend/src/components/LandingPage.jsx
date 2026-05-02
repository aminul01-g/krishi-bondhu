import React, { useState } from 'react';
import AuthPage from './AuthPage';
import './Landing.css';

export default function LandingPage({ onAuthSuccess }) {
  const [showAuth, setShowAuth] = useState(false);

  if (showAuth) {
    return <AuthPage onLogin={onAuthSuccess} />;
  }

  return (
    <div className="landing-layout">
      <nav className="landing-nav">
        <div className="nav-brand">
          <span className="brand-icon">🌾</span>
          KrishiBondhu
        </div>
        <div className="nav-links">
          <button className="nav-link">Research</button>
          <button className="nav-link">Capabilities</button>
          <button className="nav-link">Company</button>
        </div>
        <button className="nav-cta" onClick={() => setShowAuth(true)}>Try KrishiBondhu</button>
      </nav>

      <main className="landing-main">
        <section className="hero-section">
          <div className="hero-content">
            <h1 className="hero-title">
              Intelligence for the <span>modern farm.</span>
            </h1>
            <p className="hero-subtitle">
              KrishiBondhu is an advanced AI system designed to empower farmers. 
              We build intelligent, multimodal tools that analyze soil, predict markets, 
              and diagnose crop diseases in real-time.
            </p>
            <div className="hero-actions">
              <button className="primary-btn" onClick={() => setShowAuth(true)}>Get Started Free</button>
              <button className="secondary-btn">Read the research</button>
            </div>
          </div>
          <div className="hero-visual">
            <div className="visual-blob"></div>
            <div className="demo-window">
              <div className="demo-header">
                <span className="dot red"></span>
                <span className="dot yellow"></span>
                <span className="dot green"></span>
                <span className="demo-title">KrishiBondhu AI — Terminal</span>
              </div>
              <div className="demo-body">
                <div className="demo-message user">
                  <p>Can you analyze this leaf? It has yellow spots.</p>
                  <div className="demo-image-placeholder">
                    <span>📷</span> rice-leaf-sample.jpg
                  </div>
                </div>
                <div className="demo-message ai">
                  <p>Based on the image, this appears to be <strong>Brown Spot disease</strong>. I recommend ensuring proper potassium application and applying a fungicide if the infection persists.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="capabilities-section">
          <div className="section-header">
            <span className="section-tag">Capabilities</span>
            <h2>Built for the future of agriculture</h2>
          </div>
          <div className="capabilities-grid">
            <div className="capability-card">
              <span className="capability-icon">👁️</span>
              <h3>Multimodal Understanding</h3>
              <p>Capture images of crops or speak directly to the AI. Our models understand visual anomalies, agricultural context, and native dialects seamlessly.</p>
            </div>
            <div className="capability-card">
              <span className="capability-icon">📊</span>
              <h3>Predictive Intelligence</h3>
              <p>Leverage historical data, live market pricing, and hyper-local weather forecasts to optimize your yield and maximize profitability.</p>
            </div>
            <div className="capability-card">
              <span className="capability-icon">📶</span>
              <h3>Offline Resilience</h3>
              <p>Built for the field. KrishiBondhu securely queues your queries and synchronizes insights as soon as connectivity is restored.</p>
            </div>
          </div>
        </section>

        <section className="mission-section">
          {/* Add a mission statement or call to action */}
        </section>
      </main>

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand-info">
            <div className="footer-logo">🌾 KrishiBondhu</div>
            <p className="footer-tagline">Empowering farmers with world-class AI intelligence for a sustainable future.</p>
          </div>
          <div className="footer-nav">
            <div className="footer-col">
              <h4>Research</h4>
              <ul>
                <li><a href="#models">Models</a></li>
                <li><a href="#safety">Safety</a></li>
                <li><a href="#papers">Papers</a></li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Platform</h4>
              <ul>
                <li><a href="#api">API</a></li>
                <li><a href="#enterprise">Enterprise</a></li>
                <li><a href="#pricing">Pricing</a></li>
              </ul>
            </div>
            <div className="footer-col">
              <h4>Company</h4>
              <ul>
                <li><a href="#about">About</a></li>
                <li><a href="#careers">Careers</a></li>
                <li><a href="#contact">Contact</a></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© 2026 KrishiBondhu AI. All rights reserved.</p>
          <div className="footer-bottom-links">
            <a href="#terms">Terms</a>
            <a href="#privacy">Privacy</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
