import React, { useState } from 'react';
import { postFinanceSchemes, getFinanceCreditReport } from '../services/api';

const FinanceHub = ({ userId }) => {
    const [subsidies, setSubsidies] = useState('');
    const [report, setReport] = useState('');
    const [loading, setLoading] = useState(null); // 'subsidies' or 'report'

    const fetchSubsidies = async () => {
        setLoading('subsidies');
        try {
            const res = await postFinanceSchemes({ user_id: userId, crop: "Rice", land_size: 1.0 });
            setSubsidies(res.advice);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(null);
        }
    };

    const fetchReport = async () => {
        setLoading('report');
        try {
            const res = await getFinanceCreditReport(userId);
            setReport(res.report);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="feature-container">
            <div className="feature-header">
                <h2>💰 Finance & Subsidies</h2>
                <p>Access government support and evaluate your credit readiness for farm expansions.</p>
            </div>

            <div className="feature-content-grid" style={{ display: 'grid', gap: '2rem' }}>
                <div className="feature-form" style={{ background: 'white', padding: '2rem', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', display: 'flex', gap: '1rem' }}>
                    <button className="vibrant-btn" style={{ flex: 1 }} onClick={fetchSubsidies} disabled={loading === 'subsidies'}>
                        {loading === 'subsidies' ? 'Searching Subsidies...' : '🔍 View Subsidies'}
                    </button>
                    <button className="vibrant-btn" style={{ flex: 1, background: '#10b981' }} onClick={fetchReport} disabled={loading === 'report'}>
                        {loading === 'report' ? 'Generating Report...' : '📊 Credit Readiness'}
                    </button>
                </div>

                <div style={{ display: 'grid', gap: '1.5rem' }}>
                    {subsidies && (
                        <div className="result-card" style={{ background: '#f0fdf4', border: '1px solid #dcfce7', padding: '1.5rem', borderRadius: '20px' }}>
                            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#065f46', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                📑 Available Schemes
                            </h3>
                            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', fontSize: '0.95rem', color: '#064e3b', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{subsidies}</div>
                        </div>
                    )}
                    
                    {report && (
                        <div className="report-card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '1.5rem', borderRadius: '20px' }}>
                            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                💳 Credit Snapshot
                            </h3>
                            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '16px', fontSize: '0.95rem', color: '#334155', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{report}</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FinanceHub;
