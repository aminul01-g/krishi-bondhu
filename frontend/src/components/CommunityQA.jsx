import React, { useState } from 'react';
import './CommunityQA.css';

export default function CommunityQA() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([
    { id: 1, text: "How do I treat leaf curl virus in tomatoes?", author: "Rahman P.", date: "2h ago", answer: "Use neem oil spray and remove infected leaves." },
    { id: 2, text: "Best fertilizer for Aman rice?", author: "Kashem S.", date: "5h ago", answer: "Apply Urea in three split doses for better nitrogen efficiency." }
  ]);
  
  const handleSearch = (e) => {
    e.preventDefault();
    // Simulate search
  };

  return (
    <div className="community-qa">
      <div className="community-layout">
        <div className="qa-section">
          <form onSubmit={handleSearch} className="community-search-box glassmorphism">
            <input 
              type="text" 
              value={query} 
              onChange={(e) => setQuery(e.target.value)} 
              placeholder="Search conversations or ask a new question..."
            />
            <button type="submit">Ask</button>
          </form>
          
          <div className="qa-list">
            {results.map(r => (
              <div key={r.id} className="qa-card glassmorphism">
                <div className="qa-meta">
                  <span className="qa-author">{r.author}</span>
                  <span className="qa-date">{r.date}</span>
                </div>
                <h4>{r.text}</h4>
                <p className="qa-answer"><strong>Expert Advice:</strong> {r.answer}</p>
                <div className="qa-actions">
                  <button className="text-btn">👍 12 Helpful</button>
                  <button className="text-btn">💬 4 Comments</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <aside className="community-sidebar">
          <div className="outbreak-map-card glassmorphism">
            <h3>⚠️ Regional Outbreak Heatmap</h3>
            <p>Anonymized real-time pest alerts in your district.</p>
            <div className="heatmap-placeholder">
              <div className="heatmap-circle high"></div>
              <div className="heatmap-circle medium"></div>
              <div className="heatmap-circle low"></div>
              <span className="map-label">Pabna District</span>
            </div>
            <ul className="alert-list">
              <li className="high-risk">🦗 Locust Alert (High Risk)</li>
              <li className="medium-risk">🐛 Stem Borer (Medium Risk)</li>
            </ul>
            <button className="vibrant-btn small">Report Outbreak</button>
          </div>

          <div className="expert-card glassmorphism">
            <h3>🎓 Expert Consultation</h3>
            <p>Can't find an answer? Escalate to a government extension officer.</p>
            <button className="vibrant-btn secondary">Connect with Expert</button>
          </div>
        </aside>
      </div>
    </div>
  );
}
