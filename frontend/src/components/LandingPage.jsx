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
        <div className="nav-brand">KrishiBondhu</div>
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
              Intelligence for the modern farm.
            </h1>
            <p className="hero-subtitle">
              KrishiBondhu is an advanced AI system designed to empower farmers. 
              We build intelligent, multimodal tools that analyze soil, predict markets, 
              and diagnose crop diseases in real-time.
            </p>
            <div className="hero-actions">
              <button className="primary-btn" onClick={() => setShowAuth(true)}>Try KrishiBondhu</button>
              <button className="secondary-btn">Read the research</button>
            </div>
          </div>
        </section>

        <section className="capabilities-section">
          <div className="capabilities-grid">
            <div className="capability-card">
              <h3>Multimodal Understanding</h3>
              <p>Capture images of your crops or speak directly to the AI. Our models seamlessly understand visual anomalies, agricultural context, and native dialects.</p>
            </div>
            <div className="capability-card">
              <h3>Predictive Intelligence</h3>
              <p>Leverage historical data, live market pricing, and hyper-local weather forecasts to optimize your yield and maximize profitability.</p>
            </div>
            <div className="capability-card">
              <h3>Offline Resilience</h3>
              <p>Built for the field. KrishiBondhu securely queues your queries and synchronizes insights as soon as connectivity is restored.</p>
            </div>
          </div>
        </section>

        <section className="demo-section">
          <div className="demo-window">
            <div className="demo-header">
              <span className="dot red"></span>
              <span className="dot yellow"></span>
              <span className="dot green"></span>
            </div>
            <div className="demo-body">
              <div className="demo-message user">
                <p>Can you analyze this leaf? It has yellow spots.</p>
                <div className="demo-image-placeholder">📷 Attached: rice-leaf.jpg</div>
              </div>
              <div className="demo-message ai">
                <p>Based on the image, this appears to be Brown Spot disease. I recommend ensuring proper potassium application and applying a fungicide like Tricyclazole if the infection is severe.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">KrishiBondhu © 2026</div>
          <div className="footer-links">
            <span>Terms</span>
            <span>Privacy</span>
            <span>Research</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
