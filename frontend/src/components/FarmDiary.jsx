import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api';

export default function FarmDiary() {
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [message, setMessage] = useState('');
  
  // Hardcoded for demo, normally fetched from auth context
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
    try {
      const response = await fetch(`${API_BASE}/diary/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, transcript })
      });
      
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Failed to add entry');
      
      setMessage(result.message || 'Entry successfully recorded!');
      setTranscript('');
      fetchReport(); // Refresh report
    } catch (err) {
      setMessage(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feature-container">
      <div className="feature-header glassmorphism">
        <h2>📒 Digital Farm Diary</h2>
        <p>Log your expenses, incomes, and yields using natural language. The AI will parse and categorize it automatically.</p>
      </div>

      <div className="main-content">
        <div className="feature-form glassmorphism fade-in">
          <h3>Log a new transaction</h3>
          <form onSubmit={handleAddEntry}>
            <div className="input-group">
              <label>What did you spend or earn today?</label>
              <textarea 
                value={transcript} 
                onChange={(e) => setTranscript(e.target.value)} 
                placeholder="e.g., I bought 10kg of Urea fertilizer for 500 Taka (আজ ৫০০ টাকার সার কিনলাম)" 
                className="vibrant-input"
                rows="4"
                required
              />
            </div>
            <button type="submit" disabled={loading} className="vibrant-btn glow-effect">
              {loading ? 'Processing...' : 'Save to Diary'}
            </button>
          </form>
          {message && (
            <div className={`status-message ${message.includes('❌') ? 'error' : 'success'} scale-in`}>
              {message}
            </div>
          )}
        </div>

        <div className="report-card glassmorphism fade-in">
          <h3>📊 Profit & Loss Summary</h3>
          {reportLoading ? (
             <div className="spinner-small"></div>
          ) : report ? (
            <div className="report-stats">
              <div className="stat-box income">
                <span className="stat-label">Total Income</span>
                <span className="stat-value">৳{report.totals.income.toFixed(2)}</span>
              </div>
              <div className="stat-box expense">
                <span className="stat-label">Total Expenses</span>
                <span className="stat-value">৳{report.totals.expense.toFixed(2)}</span>
              </div>
              <div className={`stat-box ${report.net_profit >= 0 ? 'profit' : 'loss'}`}>
                <span className="stat-label">Net Profit</span>
                <span className="stat-value">৳{report.net_profit.toFixed(2)}</span>
              </div>
              <div className="status-badge">
                Status: <strong>{report.status}</strong>
              </div>
            </div>
          ) : (
            <p>No data available yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
