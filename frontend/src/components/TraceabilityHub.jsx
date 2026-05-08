import React, { useState } from 'react';
import { API_BASE } from '../api';

export default function TraceabilityHub() {
  const [crop, setCrop] = useState('rice');
  const [qty, setQty] = useState('');
  const [inputs, setInputs] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentBatch, setCurrentBatch] = useState(null);
  const [scanId, setScanId] = useState('');
  const [scanResult, setScanResult] = useState(null);

  const handleRegisterBatch = async () => {
    if (!qty || !inputs) {
      alert('Please provide quantity and inputs used.');
      return;
    }
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/traceability/register-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          crop: crop,
          quantity: parseFloat(qty),
          inputs_used: inputs.split(',').map(i => i.trim())
        })
      });
      if (resp.ok) {
        const data = await resp.json();
        setCurrentBatch(data);
      }
    } catch (err) {
      alert('Failed to register batch.');
    } finally {
      setLoading(false);
    }
  };

  const handleScanBatch = async () => {
    if (!scanId) return;
    try {
      const resp = await fetch(`${API_BASE}/traceability/scan/${scanId}`);
      if (resp.ok) {
        const data = await resp.json();
        setScanResult(data);
      } else {
        alert('Invalid or tampered batch ID.');
      }
    } catch (err) {
      alert('Error verifying batch.');
    }
  };

  return (
    <div className="feature-container">
      <div className="feature-header">
        <h2 style={{ margin: 0 }}>🛡️ Harvest Traceability Hub</h2>
        <p>Create immutable "Farm-to-Table" stories for your produce to command premium prices.</p>
      </div>

      <div className="feature-content-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Registration Section */}
        <div style={{ padding: '2rem', background: 'white', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
          <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.1rem' }}>Register New Batch</h3>
          <div style={{ display: 'grid', gap: '1rem' }}>
            <div className="input-group">
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#64748b', marginBottom: '0.4rem' }}>Crop</label>
              <select value={crop} onChange={e => setCrop(e.target.value)} style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                <option value="rice">Rice</option>
                <option value="wheat">Wheat</option>
                <option value="potato">Potato</option>
                <option value="mango">Mango</option>
              </select>
            </div>
            <div className="input-group">
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#64748b', marginBottom: '0.4rem' }}>Quantity (kg)</label>
              <input type="number" value={qty} onChange={e => setQty(e.target.value)} placeholder="e.g. 500" style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1px solid #e2e8f0' }} />
            </div>
            <div className="input-group">
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#64748b', marginBottom: '0.4rem' }}>Inputs Used (comma separated)</label>
              <textarea value={inputs} onChange={e => setInputs(e.target.value)} placeholder="e.g. Organic Urea, Neem Oil" style={{ width: '100%', padding: '0.8rem', borderRadius: '12px', border: '1px solid #e2e8f0', resize: 'none' }} rows="3" />
            </div>
            <button onClick={handleRegisterBatch} disabled={loading} className="vibrant-btn" style={{ width: '100%', padding: '1rem', borderRadius: '12px', border: 'none', background: '#10b981', color: 'white', fontWeight: 700, cursor: 'pointer' }}>
              {loading ? 'Hashing...' : 'Generate Immutable QR Code'}
            </button>
          </div>

          {currentBatch && (
            <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#f0fdf4', borderRadius: '20px', border: '1px solid #bbf7d0', textAlign: 'center' }}>
              <div style={{ fontWeight: 800, color: '#166534', marginBottom: '1rem' }}>✅ Batch Registered Successfully!</div>
              <img src={currentBatch.qr_url} alt="Batch QR" style={{ width: '180px', height: '180px', borderRadius: '12px', border: '4px solid white', boxShadow: 'var(--shadow-sm)' }} />
              <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: '#64748b', wordBreak: 'break-all' }}>
                <strong>Ledger Hash:</strong> {currentBatch.hash}
              </div>
            </div>
          )}
        </div>

        {/* Verification Section */}
        <div style={{ padding: '2rem', background: '#f8fafc', borderRadius: '24px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.1rem' }}>Verify Produce Story</h3>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <input
              type="text"
              value={scanId}
              onChange={e => setScanId(e.target.value)}
              placeholder="Enter Batch ID from QR scan..."
              style={{ flex: 1, padding: '0.8rem', borderRadius: '12px', border: '1px solid #e2e8f0' }}
            />
            <button onClick={handleScanBatch} className="vibrant-btn" style={{ padding: '0.8rem 1.5rem', borderRadius: '12px', border: 'none', background: '#3b82f6', color: 'white', fontWeight: 700, cursor: 'pointer' }}>
              Verify
            </button>
          </div>

          {scanResult ? (
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '20px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#16a34a', fontWeight: 800, marginBottom: '1rem' }}>
                <span>✅</span> Verified Authentic Batch
              </div>
              <div style={{ display: 'grid', gap: '0.75rem', fontSize: '0.95rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#64748b' }}>Crop:</span> <span style={{ fontWeight: 600 }}>{scanResult.story.crop}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#64748b' }}>Quantity:</span> <span style={{ fontWeight: 600 }}>{scanResult.story.quantity} kg</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.5rem' }}>
                  <span style={{ color: '#64748b' }}>Harvest Date:</span> <span style={{ fontWeight: 600 }}>{new Date(scanResult.story.harvest_date).toLocaleDateString()}</span>
                </div>
                <div style={{ marginTop: '1rem' }}>
                  <span style={{ color: '#64748b', fontSize: '0.85rem' }}>Inputs Used:</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
                    {scanResult.story.inputs.map((inp, i) => (
                      <span key={i} style={{ background: '#f1f5f9', padding: '0.3rem 0.7rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 600, color: '#475569', border: '1px solid #e2e8f0' }}>{inp}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ height: '200px', display: 'grid', placeItems: 'center', textAlign: 'center', color: '#94a3b8' }}>
              <div>
                <div style={{ fontSize: '3rem' }}>📦</div>
                <p>Enter a Batch ID to reveal the farm-to-table journey.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
