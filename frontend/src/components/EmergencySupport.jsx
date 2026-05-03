
import React, { useState } from 'react';
import { postEmergencyReport, postHelplineCall } from '../services/api';

export default function EmergencySupport({ userId }) {
  const [reportId, setReportId] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleReport = async () => {
    setLoading(true);
    try {
      // Real report generation
      const payload = {
        farmer_id: userId || "anonymous",
        crop_type: "Rice",
        lat: 23.8,
        lon: 90.4,
        damage_cause: "Flood",
        damage_estimate_percent: 50.0,
        yield_loss_estimate_percent: 40.0
      };
      const res = await postEmergencyReport(payload);
      setReportId(res.id);
    } catch (err) {
      console.error("Report failed:", err);
      alert("Failed to file report. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleHelpline = async () => {
    try {
        await postHelplineCall({
            farmer_id: userId || "anonymous",
            status: "initiated"
        });
        alert("Calling National Helpline (3331)...");
    } catch (err) {
        console.error("Helpline log failed:", err);
        alert("Helpline is currently busy. Please dial 3331 directly.");
    }
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
          disabled={loading}
          style={{ padding: '15px 30px', borderRadius: '8px', background: '#d32f2f', color: 'white', border: 'none', fontWeight: 'bold', cursor: 'pointer', opacity: loading ? 0.7 : 1 }}>
          {loading ? 'Filing Report...' : 'File Damage Report'}
        </button>
        <button 
          onClick={handleHelpline}
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
