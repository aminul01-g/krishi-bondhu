import React, { useState } from 'react';

export default function EmergencySupport() {
  const [reportId, setReportId] = useState(null);

  const handleReport = () => {
    // Mock report generation
    setReportId("REP-999-XYZ");
  };

  return (
    <div className="emergency-container">
      <div style={{ textAlign: 'center', marginBottom: '30px' }}>
        <div style={{ display: 'inline-block', background: 'rgba(244, 67, 54, 0.1)', padding: '20px', borderRadius: '50%', marginBottom: '15px' }}>
          <span style={{ fontSize: '40px' }}>🚨</span>
        </div>
        <h3 style={{ margin: '0 0 10px 0', color: '#ff9800' }}>Emergency & Disaster Relief</h3>
        <p style={{ color: '#ccc' }}>Report crop damage for insurance or call the national helpline.</p>
      </div>

      <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
        <button 
          onClick={handleReport}
          style={{ padding: '15px 30px', borderRadius: '8px', background: '#d32f2f', color: 'white', border: 'none', fontWeight: 'bold', cursor: 'pointer' }}>
          File Damage Report
        </button>
        <button 
          onClick={() => alert("Calling 3331...")}
          style={{ padding: '15px 30px', borderRadius: '8px', background: 'transparent', color: '#ff9800', border: '2px solid #ff9800', fontWeight: 'bold', cursor: 'pointer' }}>
          Call Helpline (3331)
        </button>
      </div>

      {reportId && (
        <div style={{ marginTop: '30px', padding: '20px', background: 'rgba(76, 175, 80, 0.1)', border: '1px solid #4caf50', borderRadius: '8px', textAlign: 'center' }}>
          <h4 style={{ color: '#4caf50', margin: '0 0 10px 0' }}>Report Filed Successfully!</h4>
          <p style={{ margin: 0 }}>Your Report ID is: <strong>{reportId}</strong></p>
          <p style={{ fontSize: '0.9em', color: '#aaa', marginTop: '10px' }}>An SMS has been sent to your phone with further instructions.</p>
        </div>
      )}
    </div>
  );
}
