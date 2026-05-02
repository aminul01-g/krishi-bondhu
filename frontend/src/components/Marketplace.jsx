import React, { useState } from 'react';

export default function Marketplace() {
  const [barcode, setBarcode] = useState('');
  const [status, setStatus] = useState(null);

  const handleVerify = () => {
    // Mocking verification
    if (barcode.includes('123')) {
      setStatus({ type: 'success', msg: 'Product Verified! Authentic Dealer.' });
    } else {
      setStatus({ type: 'error', msg: 'Warning: Product barcode not recognized.' });
    }
  };

  return (
    <div className="marketplace-container">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div style={{ padding: '20px', background: 'rgba(255,255,255,0.05)', borderRadius: '10px' }}>
          <h3>🔍 Verify Product</h3>
          <p style={{ fontSize: '0.9em', color: '#ccc' }}>Enter barcode or scan label to check authenticity.</p>
          <input 
            type="text" 
            value={barcode} 
            onChange={(e) => setBarcode(e.target.value)} 
            placeholder="e.g. 123456789"
            style={{ width: '100%', padding: '10px', marginBottom: '10px', borderRadius: '5px', border: '1px solid #ccc' }}
          />
          <button onClick={handleVerify} style={{ width: '100%', padding: '10px', borderRadius: '5px', background: '#2e7d32', color: 'white', border: 'none' }}>Verify</button>
          
          {status && (
            <div style={{ marginTop: '15px', padding: '10px', borderRadius: '5px', background: status.type === 'success' ? 'rgba(76, 175, 80, 0.2)' : 'rgba(244, 67, 54, 0.2)', color: status.type === 'success' ? '#4caf50' : '#f44336' }}>
              {status.msg}
            </div>
          )}
        </div>
        
        <div style={{ padding: '20px', background: 'rgba(255,255,255,0.05)', borderRadius: '10px' }}>
          <h3>🏪 Nearby Dealers</h3>
          <p style={{ fontSize: '0.9em', color: '#ccc' }}>Find verified local sellers for inputs.</p>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <li style={{ padding: '10px', background: 'rgba(0,0,0,0.2)', borderRadius: '5px' }}>Rahim Seeds (1.2km)</li>
            <li style={{ padding: '10px', background: 'rgba(0,0,0,0.2)', borderRadius: '5px' }}>Krishi Bitan (2.5km)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
