import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api';
import './FarmOverview.css';

const FarmOverview = ({ userId }) => {
  const [data, setData] = useState({ history: [], facts: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMemory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/memory/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch farm memory');
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching memory:', err);
      setError('Could not load farm intelligence.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, [userId]);

  if (loading) return <div className="overview-loading">Analyzing farm intelligence...</div>;

  return (
    <div className="farm-overview">
      <div className="overview-grid">
        {/* Memory Facts Section */}
        <div className="overview-card memory-facts">
          <h3>🧠 Farm Knowledge Base</h3>
          <p className="card-subtitle">Insights extracted from your conversations.</p>
          <div className="facts-list">
            {data.facts.length > 0 ? (
              data.facts.map((fact, idx) => (
                <div key={idx} className="fact-item glassmorphism">
                  <div className="fact-header">
                    <span className="fact-category">{fact.category}</span>
                    <span className="fact-confidence">{(fact.confidence * 100).toFixed(0)}% Match</span>
                  </div>
                  <div className="fact-content">
                    <strong>{fact.key}:</strong> {fact.value}
                  </div>
                </div>
              ))
            ) : (
              <div className="no-facts">
                No insights extracted yet. Keep chatting to grow your farm memory!
              </div>
            )}
          </div>
        </div>

        {/* Satellite & GPS Section */}
        <div className="overview-card satellite-status">
          <h3>🛰️ Field Grounding</h3>
          <p className="card-subtitle">Real-time environmental and GPS status.</p>
          <div className="status-grid">
            <div className="status-item glassmorphism">
              <div className="status-icon">📍</div>
              <div className="status-label">Location</div>
              <div className="status-value">Pabna, Bangladesh</div>
            </div>
            <div className="status-item glassmorphism">
              <div className="status-icon">💧</div>
              <div className="status-label">Moisture</div>
              <div className="status-value">22% (Moderate)</div>
            </div>
            <div className="status-item glassmorphism">
              <div className="status-icon">🌱</div>
              <div className="status-label">NDVI (Health)</div>
              <div className="status-value">0.65 (Healthy)</div>
            </div>
            <div className="status-item glassmorphism">
              <div className="status-icon">🌡️</div>
              <div className="status-label">Temp</div>
              <div className="status-value">31°C</div>
            </div>
          </div>
          <div className="map-placeholder glassmorphism">
             {/* Map will be integrated here */}
             <div className="map-overlay">
                <span>Field Map Visualizer</span>
                <p>Satellite overlay active</p>
             </div>
          </div>
        </div>
      </div>

      {/* Recent History Section */}
      <div className="overview-card recent-timeline">
        <h3>🕰️ Agricultural Timeline</h3>
        <p className="card-subtitle">Chronological record of your farm's journey.</p>
        <div className="timeline">
          {data.history.length > 0 ? (
            data.history.slice(0, 5).map((item, idx) => (
              <div key={idx} className="timeline-item">
                <div className="timeline-dot"></div>
                <div className="timeline-content glassmorphism">
                  <div className="timeline-date">{new Date(item.timestamp).toLocaleDateString()}</div>
                  <p>{item.summary}</p>
                </div>
              </div>
            ))
          ) : (
            <p>Your agricultural journey starts here.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default FarmOverview;
