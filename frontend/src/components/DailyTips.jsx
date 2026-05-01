import React, { useState } from 'react';
import { API_BASE } from '../api';

export default function DailyTips() {
  const [crop, setCrop] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const fetchDailyTip = async (e) => {
    e.preventDefault();
    if (!crop.trim()) return;
    
    setLoading(true);
    setError(null);
    try {
      // Mock coordinates for demo
      const lat = 23.8103;
      const lon = 90.4125;
      const userId = "farmer_001";
      
      const response = await fetch(`${API_BASE}/alerts/daily?user_id=${userId}&crop=${encodeURIComponent(crop)}&lat=${lat}&lon=${lon}`);
      if (!response.ok) throw new Error('Failed to fetch daily tip and alerts');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feature-container">
      <div className="feature-header glassmorphism">
        <h2>💡 Daily Tips & Pest Alerts</h2>
        <p>Get proactive daily farming tips and predictive alerts about impending diseases based on the local weather.</p>
      </div>

      <form onSubmit={fetchDailyTip} className="feature-form glassmorphism fade-in">
        <div className="input-group">
          <label>What crop are you currently growing?</label>
          <input 
            type="text" 
            value={crop} 
            onChange={(e) => setCrop(e.target.value)} 
            placeholder="e.g., Rice, Brinjal, Potato..." 
            className="vibrant-input"
            required
          />
        </div>
        <button type="submit" disabled={loading} className="vibrant-btn glow-effect">
          {loading ? 'Checking Risks...' : 'Get Daily Alert'}
        </button>
      </form>

      {error && <div className="error-message scale-in">{error}</div>}

      {data && !loading && (
        <div className="alert-grid fade-in">
          <div className="alert-card glassmorphism">
            <h3>🌱 Today's Crop Tip</h3>
            <div className="tip-content">
              <p>{data.tip_bn}</p>
            </div>
            {data.audio_url && (
              <audio controls className="audio-player mt-2">
                <source src={data.audio_url} type="audio/mp3" />
              </audio>
            )}
          </div>

          <div className="alert-card warning glassmorphism">
            <h3>⚠️ Proactive Pest Risk Alert</h3>
            <div className="risk-content">
              <p className="whitespace-pre-wrap">{data.pest_risk_alert}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
