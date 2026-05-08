import React, { useState } from 'react';
import { postSoilAnalyze } from '../services/api';

const SoilHealth = ({ userId }) => {
    const [advice, setAdvice] = useState('');
    const [crop, setCrop] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleAnalyze = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await postSoilAnalyze({ user_id: userId, crop });
            setAdvice(res.advice);
        } catch (err) {
            setError(err.message || 'Failed to analyze soil.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="feature-container" data-testid="soil-health-section">
            <div className="feature-header" style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.8rem', color: '#064e3b', marginBottom: '0.5rem' }}>🌱 Soil Health Advisor</h2>
                <p style={{ color: '#64748b', fontSize: '1.1rem' }}>Analyze your soil's nutritional profile to optimize fertilizer use and maximize crop yields.</p>
            </div>
            
            <div className="feature-content-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div className="feature-form" style={{ background: 'white', padding: '2rem', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                    <div className="input-group" style={{ marginBottom: '1.5rem' }}>
                        <label style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.5rem', display: 'block', color: '#475569' }}>Enter the crop you plan to grow:</label>
                        <input 
                            className="vibrant-input" 
                            placeholder="e.g., Rice, Wheat, Corn..." 
                            value={crop} 
                            onChange={(e) => setCrop(e.target.value)} 
                            style={{ width: '100%', padding: '1.25rem', borderRadius: '16px', border: '1px solid #e2e8f0', fontSize: '1rem' }}
                            data-testid="soil-crop-input"
                        />
                    </div>
                    <button className="vibrant-btn" style={{ width: '100%' }} onClick={handleAnalyze} disabled={loading} data-testid="soil-analyze-btn">
                        {loading ? 'Analyzing Soil Data...' : 'Analyze Soil Health'}
                    </button>
                </div>

                {/* Error State */}
                {error && (
                    <div data-testid="soil-error" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #fca5a5', borderRadius: '24px', padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                        <span style={{ color: '#dc2626', fontWeight: 600 }}>⚠️ {error}</span>
                        <button onClick={handleAnalyze} className="vibrant-btn" style={{ padding: '0.5rem 1.5rem' }} data-testid="soil-retry-btn">Retry</button>
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div data-testid="soil-loading" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '24px' }}>
                        <div style={{ fontSize: '2.5rem', marginBottom: '1rem', animation: 'pulse 1.5s infinite' }}>🧪</div>
                        <p style={{ color: '#64748b', fontWeight: 600, textAlign: 'center' }}>Running 3-tier vision analysis on your soil profile...</p>
                    </div>
                )}

                {/* Empty State */}
                {!loading && !advice && !error && (
                    <div data-testid="soil-empty" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: '#94a3b8', borderRadius: '24px', border: '2px dashed #e2e8f0' }}>
                        <span style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔬</span>
                        <p style={{ textAlign: 'center' }}>Results will appear here after analysis.</p>
                    </div>
                )}
                
                {/* Results */}
                {advice && !loading && (
                    <div className="result-card" data-testid="soil-results" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '2rem', borderRadius: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>🧪</span>
                            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#064e3b' }}>Soil Analysis Result</h3>
                        </div>
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)', border: '1px solid #d1fae5', lineHeight: 1.8, color: '#1f2937', fontSize: '1.05rem', whiteSpace: 'pre-wrap' }}>
                            {advice}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SoilHealth;
