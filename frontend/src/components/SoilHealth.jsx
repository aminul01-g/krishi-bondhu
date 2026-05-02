import React, { useState } from 'react';
import { postSoilAnalyze } from '../services/api';

const SoilHealth = ({ userId }) => {
    const [advice, setAdvice] = useState('');
    const [crop, setCrop] = useState('');
    const [loading, setLoading] = useState(false);

    const handleAnalyze = async () => {
        setLoading(true);
        try {
            const res = await postSoilAnalyze({ user_id: userId, crop });
            setAdvice(res.advice);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="feature-container">
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
                        />
                    </div>
                    <button className="vibrant-btn" style={{ width: '100%' }} onClick={handleAnalyze} disabled={loading}>
                        {loading ? 'Analyzing Soil Data...' : 'Analyze Soil Health'}
                    </button>
                </div>
                
                {advice && (
                    <div className="result-card" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '2rem', borderRadius: '24px' }}>
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
