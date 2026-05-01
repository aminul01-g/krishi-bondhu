import React, { useState } from 'react';
import { API_BASE } from '../api';

export default function MarketIntelligence() {
  const [crop, setCrop] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const fetchMarketAdvice = async (e) => {
    e.preventDefault();
    if (!crop.trim()) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/market/advice?crop=${encodeURIComponent(crop)}`);
      if (!response.ok) throw new Error('Failed to fetch market data');
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
        <h2>📈 Smart Market Intelligence</h2>
        <p>Get real-time wholesale prices, trend predictions, and the best advice on whether to sell now or wait.</p>
      </div>

      <form onSubmit={fetchMarketAdvice} className="feature-form glassmorphism fade-in">
        <div className="input-group">
          <label>Which crop do you want to check?</label>
          <input 
            type="text" 
            value={crop} 
            onChange={(e) => setCrop(e.target.value)} 
            placeholder="e.g., Potato, Rice, Tomato (আলু, ধান...)" 
            className="vibrant-input"
            required
          />
        </div>
        <button type="submit" disabled={loading} className="vibrant-btn glow-effect">
          {loading ? 'Analyzing Market...' : 'Analyze Market'}
        </button>
      </form>

      {error && <div className="error-message scale-in">{error}</div>}

      {data && !loading && (
        <div className="result-card glassmorphism scale-in">
          <div className="result-header">
            <h3>Result for: <span className="highlight">{data.crop}</span></h3>
          </div>
          <div className="market-advice-content">
            <p className="whitespace-pre-wrap">{data.advice}</p>
          </div>
        </div>
      )}
    </div>
  );
}
