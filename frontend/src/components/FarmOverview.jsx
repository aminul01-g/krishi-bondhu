import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './FarmOverview.css';

// Fix for default marker icons in Leaflet + React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const FarmOverview = ({ userId }) => {
  const [data, setData] = useState({ history: [], facts: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Default coordinates (e.g., Pabna, Bangladesh)
  const [position, setPosition] = useState([24.0063, 89.2493]);

  const fetchMemory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/memory/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch farm memory');
      const result = await response.json();
      setData(result);
      
      // Attempt to extract lat/lon from memory facts if available
      const latFact = result.facts.find(f => f.key.toLowerCase().includes('lat'));
      const lonFact = result.facts.find(f => f.key.toLowerCase().includes('lon'));
      if (latFact && lonFact) {
        setPosition([parseFloat(latFact.value), parseFloat(lonFact.value)]);
      }
    } catch (err) {
      console.error('Error fetching memory:', err);
      setError('Could not load farm intelligence.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, [userId]);

  const [lowDataMode, setLowDataMode] = useState(localStorage.getItem('low_data_mode') === 'true');

  const toggleLowData = () => {
    const newState = !lowDataMode;
    setLowDataMode(newState);
    localStorage.setItem('low_data_mode', newState);
  };

  if (loading) return <div className="overview-loading">Analyzing farm intelligence...</div>;

  const { insights } = data;

  return (
    <div className="farm-overview">
      {/* Predictive Intelligence Bar */}
      <div className="predictive-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Farm Intelligence</h3>
        <button 
          onClick={toggleLowData} 
          className={`low-data-toggle ${lowDataMode ? 'active' : ''}`}
          title="Disable satellite imagery to save data"
        >
          {lowDataMode ? '📡 High Data Mode' : '📉 Low Data Mode'}
        </button>
      </div>

      {insights && (
        <div className="predictive-banner glassmorphism">
          <div className="stage-prediction">
            <span className="label">Current Predicted Stage:</span>
            <span className="value">{insights.predicted_stage}</span>
          </div>
          <div className="risk-alerts">
            {insights.risks.map((risk, idx) => (
              <div key={idx} className={`risk-pill ${risk.level.toLowerCase()}`}>
                ⚠️ {risk.type}: {risk.factor} ({risk.level})
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="overview-grid">
        {/* Memory Facts Section */}
        <div className="overview-card memory-facts">
          <h3>🧠 Farm Knowledge Base</h3>
          <p className="card-subtitle">Insights extracted from your conversations.</p>
          <div className="facts-list">
            {data.facts.length > 0 ? (
              data.facts.map((fact, idx) => (
                <div key={idx} className="fact-item glassmorphism">
                  <div className="fact-header">
                    <span className="fact-category">{fact.category}</span>
                    <span className="fact-confidence">{(fact.confidence * 100).toFixed(0)}% Match</span>
                  </div>
                  <div className="fact-content">
                    <strong>{fact.key}:</strong> {fact.value}
                  </div>
                </div>
              ))
            ) : (
              <div className="no-facts">
                No insights extracted yet. Keep chatting to grow your farm memory!
              </div>
            )}
          </div>
        </div>

        {/* Satellite & GPS Section */}
        <div className="overview-card satellite-status">
          <h3>🛰️ Field Grounding</h3>
          <p className="card-subtitle">Real-time environmental and GPS status.</p>
          <div className="status-grid">
            <div className="status-item glassmorphism">
              <div className="status-icon">📍</div>
              <div className="status-label">Location</div>
              <div className="status-value">{position[0].toFixed(3)}, {position[1].toFixed(3)}</div>
            </div>
            <div className="status-item glassmorphism">
              <div className="status-icon">💧</div>
              <div className="status-label">Moisture</div>
              <div className="status-value">22% (Moderate)</div>
            </div>
            <div className="status-item glassmorphism">
              <div className="status-icon">🌱</div>
              <div className="status-label">NDVI (Health)</div>
              <div className="status-value">0.65 (Healthy)</div>
            </div>
            <div className="status-item glassmorphism">
              <div className="status-icon">🌡️</div>
              <div className="status-label">Temp</div>
              <div className="status-value">31°C</div>
            </div>
          </div>
          
          <div className="map-container-wrapper glassmorphism">
            <MapContainer center={position} zoom={15} scrollWheelZoom={false} style={{ height: '100%', width: '100%', borderRadius: '24px' }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {!lowDataMode && (
                <TileLayer
                  attribution='Imagery &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EBP, and the GIS User Community'
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                />
              )}
              <Marker position={position}>
                <Popup>
                  <strong>Your Registered Farm Plot</strong><br />
                  Health: 0.65 (Healthy)
                </Popup>
              </Marker>
              <Circle 
                center={position} 
                radius={200} 
                pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 0.2 }} 
              />
            </MapContainer>
          </div>
        </div>
      </div>

      {/* Recent History Section */}
      <div className="overview-card recent-timeline">
        <h3>🕰️ Agricultural Timeline</h3>
        <p className="card-subtitle">Chronological record of your farm's journey.</p>
        <div className="timeline">
          {data.history.length > 0 ? (
            data.history.slice(0, 5).map((item, idx) => (
              <div key={idx} className="timeline-item">
                <div className="timeline-dot"></div>
                <div className="timeline-content glassmorphism">
                  <div className="timeline-date">{new Date(item.timestamp).toLocaleDateString()}</div>
                  <p>{item.summary}</p>
                </div>
              </div>
            ))
          ) : (
            <p>Your agricultural journey starts here.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default FarmOverview;
