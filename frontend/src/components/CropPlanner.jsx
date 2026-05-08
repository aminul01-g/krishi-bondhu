import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api';

export default function CropPlanner() {
  const [crop, setCrop] = useState('rice');
  const [loading, setLoading] = useState(false);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [history, setHistory] = useState([]);

  const fetchPlans = async () => {
    try {
      const resp = await fetch(`${API_BASE}/planner/my-plans`);
      if (resp.ok) {
        const data = await resp.json();
        setHistory(data);
      }
    } catch (err) {
      console.error('Error fetching plans:', err);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleGeneratePlan = async () => {
    setLoading(true);
    try {
      // Using default Dhaka coordinates for the demo; in real app, we'd use navigator.geolocation
      const resp = await fetch(`${API_BASE}/planner/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          crop: crop,
          lat: 23.8103,
          lon: 90.4125
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setCurrentPlan(data.details);
        await fetchPlans();
      }
    } catch (err) {
      alert('Failed to generate plan. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feature-container">
      <div className="feature-header">
        <h2 style={{ margin: 0 }}>🌾 Seasonal Crop Planner</h2>
        <p>AI-driven yield forecasting and planting roadmaps for your land.</p>
      </div>

      <div className="feature-content-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '2rem' }}>
        {/* Control Panel */}
        <div style={{ padding: '2rem', background: 'white', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
          <h3 style={{ marginTop: 0, fontSize: '1.1rem' }}>Generate New Plan</h3>
          <div className="input-group" style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: '#64748b', marginBottom: '0.5rem' }}>Target Crop</label>
            <select
              value={crop}
              onChange={(e) => setCrop(e.target.value)}
              style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#f8fafc' }}
            >
              <option value="rice">Rice (ধান)</option>
              <option value="wheat">Wheat (গম)</option>
              <option value="potato">Potato (আলু)</option>
              <option value="mango">Mango (আম)</option>
            </select>
          </div>
          <button
            onClick={handleGeneratePlan}
            disabled={loading}
            className="vibrant-btn"
            style={{ width: '100%', padding: '1rem', borderRadius: '12px', border: 'none', background: '#10b981', color: 'white', fontWeight: 700, cursor: 'pointer' }}
          >
            {loading ? 'Calculating...' : 'Generate Season Plan'}
          </button>

          <div style={{ marginTop: '2rem' }}>
            <h4 style={{ fontSize: '0.9rem', color: '#64748b' }}>Previous Plans</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {history.map(p => (
                <div key={p.id} onClick={() => setCurrentPlan(p.details)} style={{ padding: '0.75rem', background: '#f1f5f9', borderRadius: '12px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, border: '1px solid transparent' }}>
                  {p.crop} ({p.year}) - {p.predicted_yield} t/b
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Plan Display */}
        <div style={{ padding: '2rem', background: '#f8fafc', borderRadius: '24px', border: '1px solid #e2e8f0' }}>
          {currentPlan ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ margin: 0 }}>📋 Your Seasonal Roadmap</h3>
                <div style={{ background: 'white', padding: '0.5rem 1rem', borderRadius: '99px', border: '1px solid #10b981', color: '#10b981', fontWeight: 800, fontSize: '0.85rem' }}>
                  Predicted: {currentPlan.prediction.predicted_yield} Tons/Bigha
                </div>
              </div>

              <div style={{ display: 'grid', gap: '1rem' }}>
                {currentPlan.roadmap.map((step, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '1rem', background: 'white', padding: '1rem', borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
                    <div style={{ background: '#10b981', color: 'white', width: '28px', height: '28px', borderRadius: '50%', display: 'grid', placeItems: 'center', fontWeight: 800, fontSize: '0.8rem', flexShrink: 0 }}>
                      {idx + 1}
                    </div>
                    <div>
                      <div style={{ fontWeight: 800, color: '#1e293b' }}>{step.phase}</div>
                      <div style={{ fontSize: '0.9rem', color: '#475569' }}>{step.action}</div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>⏱️ {step.timing}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: '2rem', padding: '1.25rem', background: '#fef2f2', borderRadius: '16px', border: '1px solid #fee2e2' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#991b1b', fontSize: '0.9rem' }}>⚠️ Risk Factors to Watch</h4>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.85rem', color: '#b91c1c' }}>
                  {currentPlan.risk_factors.map((risk, i) => <li key={i}>{risk}</li>)}
                </ul>
              </div>
            </div>
          ) : (
            <div style={{ height: '100%', display: 'grid', placeItems: 'center', textAlign: 'center', color: '#94a3b8' }}>
              <div>
                <div style={{ fontSize: '3rem' }}>🌾</div>
                <p>Select a crop and generate a plan to see your roadmap.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
