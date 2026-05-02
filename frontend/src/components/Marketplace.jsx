import React, { useState } from 'react';

export default function Marketplace() {
  const [barcode, setBarcode] = useState('');
  const [status, setStatus] = useState(null);

  const handleVerify = () => {
    if (barcode.includes('123')) {
      setStatus({ type: 'success', msg: 'Product Verified! Authentic Dealer.' });
    } else {
      setStatus({ type: 'error', msg: 'Warning: Product barcode not recognized.' });
    }
  };

  return (
    <div className="feature-container">
      <div className="feature-header">
        <h2>🏪 Input Marketplace & Verification</h2>
        <p>Buy seeds and fertilizers from verified dealers or check product authenticity instantly.</p>
      </div>

      <div className="feature-content-grid" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '2rem' }}>
        <div style={{ padding: '2rem', background: 'white', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1.1rem', color: '#1e293b' }}>🔍 Authenticity Check</h3>
          <p style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1.5rem' }}>Verify your seeds or fertilizers by entering the manufacturer's barcode.</p>
          <div className="input-group" style={{ marginBottom: '1rem' }}>
            <input 
              type="text" 
              value={barcode} 
              onChange={(e) => setBarcode(e.target.value)} 
              placeholder="Enter product barcode..."
              style={{ width: '100%', padding: '1rem', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#f8fafc', fontSize: '1rem', outline: 'none' }}
            />
          </div>
          <button onClick={handleVerify} className="vibrant-btn" style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: 'none', background: '#10b981', color: 'white', fontWeight: 700, cursor: 'pointer' }}>Verify Product</button>
          
          {status && (
            <div style={{ marginTop: '1.5rem', padding: '1.25rem', borderRadius: '16px', background: status.type === 'success' ? '#f0fdf4' : '#fef2f2', border: '1px solid ' + (status.type === 'success' ? '#bbf7d0' : '#fecaca'), color: status.type === 'success' ? '#166534' : '#991b1b', fontWeight: 600, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.2rem' }}>{status.type === 'success' ? '✅' : '🚨'}</span>
              {status.msg}
            </div>
          )}
        </div>
        
        <div style={{ padding: '2rem', background: '#f8fafc', borderRadius: '24px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1.1rem', color: '#1e293b' }}>📍 Nearby Verified Dealers</h3>
          <p style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1.5rem' }}>Find trusted local sellers approved by KrishiBondhu.</p>
          <div style={{ display: 'grid', gap: '1rem' }}>
            <div style={{ padding: '1rem', background: 'white', borderRadius: '16px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <div style={{ fontWeight: 800, color: '#1e293b' }}>Rahim Seed Store</div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>1.2km away • Verified</div>
                </div>
                <button className="text-btn" style={{ color: '#10b981', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}>Call</button>
            </div>
            <div style={{ padding: '1rem', background: 'white', borderRadius: '16px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <div style={{ fontWeight: 800, color: '#1e293b' }}>Mayer Doa Fertilizer</div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>2.5km away • Verified</div>
                </div>
                <button className="text-btn" style={{ color: '#10b981', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}>Call</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
