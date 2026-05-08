import React, { useState } from 'react';
import { postWaterAdvice } from '../services/api';

const WaterIrrigation = ({ userId }) => {
    const [advice, setAdvice] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleGetAdvice = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await postWaterAdvice({ user_id: userId, lat: 23.81, lon: 90.41, crop: "Rice" });
            setAdvice(res.advice);
        } catch (err) {
            setError(err.message || 'Failed to fetch irrigation advice.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card glassmorphism fade-in" data-testid="water-irrigation-section">
            <div className="feature-header">
                <h2>💧 Water & Irrigation (সেচ ও পানি ব্যবস্থাপনা)</h2>
                <p className="section-description">Precision irrigation based on real-time satellite moisture data and Hargreaves-Samani ET₀ model.</p>
            </div>

            <div className="feature-form">
                <button
                    className="vibrant-btn glow-effect"
                    onClick={handleGetAdvice}
                    disabled={loading}
                    data-testid="water-get-advice-btn"
                >
                    {loading ? 'Calculating...' : 'Get Daily Advice'}
                </button>
            </div>

            {/* Error State */}
            {error && (
                <div data-testid="water-error" style={{ marginTop: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #fca5a5', borderRadius: '12px', padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ color: '#dc2626' }}>⚠️ {error}</span>
                    <button onClick={handleGetAdvice} style={{ background: '#dc2626', color: 'white', border: 'none', borderRadius: '8px', padding: '0.5rem 1rem', cursor: 'pointer', fontWeight: 600 }} data-testid="water-retry-btn">Retry</button>
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div data-testid="water-loading" style={{ marginTop: '1.5rem', textAlign: 'center', padding: '2rem' }}>
                    <div style={{ fontSize: '2rem', marginBottom: '0.75rem', animation: 'pulse 1.5s infinite' }}>💧</div>
                    <p style={{ color: '#64748b', fontWeight: 600 }}>Fetching satellite data & computing water balance...</p>
                </div>
            )}

            {/* Empty State */}
            {!loading && !advice && !error && (
                <div data-testid="water-empty" style={{ marginTop: '1.5rem', textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                    <p>Click "Get Daily Advice" to receive satellite-based irrigation guidance for your farm.</p>
                </div>
            )}

            {/* Results */}
            {advice && !loading && (
                <div className="result-card fade-in" data-testid="water-results" style={{ marginTop: '1.5rem', background: 'rgba(59, 130, 246, 0.05)', borderRadius: '16px', padding: '1.5rem', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                    <div style={{ whiteSpace: 'pre-wrap', color: '#1e293b', fontWeight: 500, lineHeight: 1.8, fontSize: '1.05rem' }}>{advice}</div>
                </div>
            )}
        </div>
    );
};

export default WaterIrrigation;
