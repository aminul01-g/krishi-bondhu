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
      <div className="feature-header">
        <h2>📈 Smart Market Intelligence</h2>
        <p>Real-time wholesale prices, trend predictions, and strategic selling advice tailored for your farm.</p>
      </div>

      <div className="feature-content-grid" style={{ display: 'grid', gap: '2rem' }}>
        <form onSubmit={fetchMarketAdvice} className="feature-form">
          <div className="input-group">
            <label style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block' }}>Which crop are you monitoring?</label>
            <input 
              type="text" 
              value={crop} 
              onChange={(e) => setCrop(e.target.value)} 
              placeholder="e.g., Potato, Rice, Tomato..." 
              style={{ padding: '1.25rem', borderRadius: '16px', border: '1px solid #e2e8f0', fontSize: '1rem', width: '100%' }}
              required
            />
          </div>
          <button type="submit" disabled={loading} className="vibrant-btn" style={{ width: '100%', marginTop: '1rem' }}>
            {loading ? 'Analyzing Trends...' : 'Fetch Market Advice'}
          </button>
        </form>

        {error && <div className="error-message">{error}</div>}

        {data && !loading && (
          <div className="result-card" style={{ background: '#f0fdf4', borderRadius: '24px', padding: '2rem', border: '1px solid #bbf7d0' }}>
            <div className="result-header" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ background: 'white', padding: '0.75rem', borderRadius: '12px', fontSize: '1.5rem', boxShadow: '0 4px 10px rgba(0,0,0,0.05)' }}>🌾</div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#064e3b' }}>Market Insight for: {data.crop}</h3>
                <span style={{ fontSize: '0.85rem', color: '#059669', fontWeight: 600 }}>Live Intelligence • Just Updated</span>
              </div>
            </div>
            <div className="market-advice-content" style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)', border: '1px solid #d1fae5' }}>
              <p style={{ margin: 0, lineHeight: 1.8, color: '#1f2937', fontSize: '1.05rem', whiteSpace: 'pre-wrap' }}>{data.advice}</p>
            </div>
            <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '0.75rem 1rem', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 700, color: '#059669' }}>
                🚀 Buy/Sell Index: Stable
              </div>
              <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '0.75rem 1rem', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 700, color: '#2563eb' }}>
                📊 Market Confidence: High
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
