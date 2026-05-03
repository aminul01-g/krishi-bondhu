import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api';
import { saveToQueue } from '../services/offlineQueue';

export default function FarmDiary() {
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [message, setMessage] = useState('');
  
  const userId = "farmer_001";

  const fetchReport = async () => {
    setReportLoading(true);
    try {
      const response = await fetch(`${API_BASE}/diary/report?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setReport(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  const handleAddEntry = async (e) => {
    e.preventDefault();
    if (!transcript.trim()) return;
    
    setLoading(true);
    setMessage('');

    const payload = { user_id: userId, transcript };
    const url = `${API_BASE}/diary/add`;

    try {
      if (!navigator.onLine) {
        // Create a fake FormData for the queue (as current queue expects FormData)
        const fd = new FormData();
        fd.append('user_id', userId);
        fd.append('transcript', transcript);
        
        await saveToQueue(url, fd);
        setMessage('⏳ Offline: Entry saved locally. It will sync automatically when you have signal.');
        setTranscript('');
        return;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Failed to add entry');
      
      setMessage('✅ Entry successfully recorded!');
      setTranscript('');
      fetchReport();
    } catch (err) {
      setMessage(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feature-container">
      <div className="feature-header">
        <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#1e293b', marginBottom: '0.5rem' }}>📒 Digital Farm Diary</h2>
        <p style={{ color: '#64748b', fontSize: '1.1rem', maxWidth: '600px' }}>Log your expenses, incomes, and yields using natural language. Our AI handles the categorization for you.</p>
      </div>

      <div className="feature-content-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
        <div className="feature-form-section">
          <form onSubmit={handleAddEntry} className="feature-form" style={{ background: 'white', padding: '2rem', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: '1.25rem', color: '#0f172a' }}>Log New Transaction</h3>
            <div className="input-group">
              <label style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.75rem', display: 'block', color: '#475569' }}>Tell us what happened today...</label>
              <textarea 
                value={transcript} 
                onChange={(e) => setTranscript(e.target.value)} 
                placeholder="e.g., I sold 20kg of potatoes for 1200 Taka or I bought fertilizer for 500 Taka." 
                style={{ width: '100%', padding: '1.25rem', borderRadius: '16px', border: '1px solid #e2e8f0', minHeight: '140px', fontSize: '1rem', outline: 'none' }}
                required
              />
            </div>
            <button type="submit" disabled={loading} className="vibrant-btn" style={{ width: '100%', marginTop: '1.5rem' }}>
              {loading ? 'Processing Entry...' : 'Save Entry'}
            </button>
            {message && (
              <div style={{ marginTop: '1rem', padding: '1rem', borderRadius: '12px', background: message.includes('✅') ? '#f0fdf4' : '#fef2f2', color: message.includes('✅') ? '#166534' : '#991b1b', fontSize: '0.9rem', fontWeight: 600 }}>
                {message}
              </div>
            )}
          </form>
        </div>

        <div className="report-section">
          <div className="report-card" style={{ background: 'white', padding: '2rem', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', height: '100%' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: '1.2rem' }}>📊 Profit & Loss Summary</h3>
            {reportLoading ? (
               <p style={{ color: '#64748b' }}>Calculating summary...</p>
            ) : report ? (
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div style={{ padding: '1.25rem', borderRadius: '16px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>Total Income</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#10b981' }}>৳{report.totals.income.toFixed(2)}</div>
                </div>
                <div style={{ padding: '1.25rem', borderRadius: '16px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>Total Expenses</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ef4444' }}>৳{report.totals.expense.toFixed(2)}</div>
                </div>
                <div style={{ padding: '1.5rem', borderRadius: '16px', background: report.net_profit >= 0 ? '#f0fdf4' : '#fef2f2', border: '1px solid ' + (report.net_profit >= 0 ? '#bbf7d0' : '#fecaca') }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: report.net_profit >= 0 ? '#166534' : '#991b1b', textTransform: 'uppercase' }}>Net Profit</div>
                  <div style={{ fontSize: '2rem', fontWeight: 900, color: report.net_profit >= 0 ? '#059669' : '#b91c1c' }}>৳{report.net_profit.toFixed(2)}</div>
                </div>
                <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>
                  Financial Status: <span style={{ color: '#10b981' }}>{report.status}</span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>No financial data yet. Log an entry to see your summary!</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
