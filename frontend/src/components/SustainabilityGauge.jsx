import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api';

export default function SustainabilityGauge() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [opportunities, setOpportunities] = useState([]);

  const fetchSustainabilityData = async () => {
    setLoading(true);
    try {
      const scoreResp = await fetch(`${API_BASE}/sustainability/scorecard`);
      const scoreData = await scoreResp.json();

      const oppsResp = await fetch(`${API_BASE}/sustainability/opportunities`);
      const oppsData = await oppsResp.json();

      setMetrics(scoreData.data);
      setOpportunities(oppsData.opportunities);
    } catch (err) {
      console.error('Sustainability fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSustainabilityData();
  }, []);

  // Calculate gauge rotation based on score
  const getRotation = (score) => {
    if (!score) return 0;
    return (score / 100) * 180 - 90;
  };

  return (
    <<divdiv className="feature-container">
      <<divdiv className="feature-header">
        <<hh2 style={{ margin: 0 }}>🌿 Sustainability & Carbon Hub</h2>
        <<pp>Track your eco-footprint and earn rewards for sustainable farming practices.</p>
      </div>

      <<divdiv className="feature-content-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Scorecard Section */}
        <<divdiv style={{ padding: '2rem', background: 'white', borderRadius: '24px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', textAlign: 'center' }}>
          <<hh3 style={{ marginTop: 0, marginBottom: '2rem', fontSize: '1.1rem' }}>Your Green Scorecard</h3>

          <<divdiv style={{ position: 'relative', width: '200px', height: '100px', margin: '0 auto', overflow: 'hidden' }}>
            {/* Gauge Background */}
            <<divdiv style={{
              width: '200px', height: '200px', borderRadius: '100%',
              background: 'conic-gradient(from 180deg, #fee2e2, #fde68a, #bbf7d0)',
              position: 'absolute', top: '0', left: '0'
            }} />
            {/* Gauge Mask */}
            <<divdiv style={{
              position: 'absolute', width: '160px', height: '160px', borderRadius: '100%',
              background: 'white', top: '20px', left: '20px', zIndex: 1
            }} />
            {/* Needle */}
            <<divdiv style={{
              position: 'absolute', width: '4px', height: '80px', background: '#1e293b',
              bottom: '0', left: '50%', transformOrigin: 'bottom center',
              transform: `rotate(${getRotation(metrics?.score)}deg)`,
              transition: 'transform 1s ease-out', zIndex: 2,
              borderRadius: '2px'
            }} />
          </div>

          <<divdiv style={{ marginTop: '1rem', fontSize: '2.5rem', fontWeight: 900, color: '#166534' }}>
            {loading ? '...' : `${metrics?.score || 0} / 100`}
          </div>
          <<divdiv style={{ fontSize: '1rem', fontWeight: 700, color: '#64748b', marginBottom: '1.5rem' }}>
            Grade: {metrics?.grade || 'N/A'}
          </div>

          <<divdiv style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '2rem' }}>
            <<divdiv style={{ padding: '1rem', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
              <<divdiv style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>CO₂ OFFSET</div>
              <<divdiv style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10b981' }}>{metrics?.co2_offset_kg || 0} kg</div>
            </div>
            <<divdiv style={{ padding: '1rem', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
              <<divdiv style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>STATUS</div>
              <<divdiv style={{ fontSize: '1.25rem', fontWeight: 800, color: '#3b82f6' }}>{metrics?.verified_practices?.length || 0} Badges</div>
            </div>
          </div>

          <<divdiv style={{ marginTop: '2rem', padding: '1rem', background: '#f0fdf4', borderRadius: '16px', border: '1px solid #bbf7d0', fontSize: '0.9rem', color: '#166534', fontWeight: 500 }}>
            {metrics?.recommendation || "Keep recording your farm practices to unlock your scorecard!"}
          </div>
        </div>

        {/* Opportunities Section */}
        <<divdiv style={{ padding: '2rem', background: '#f8fafc', borderRadius: '24px', border: '1px solid #e2e8f0' }}>
          <<hh3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.1rem' }}>Carbon Market Opportunities</h3>
          <<pp style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1.5rem' }}>Based on your current score, you qualify for these green incentives.</p>

          <<divdiv style={{ display: 'grid', gap: '1rem' }}>
            {opportunities.length > 0 ? opportunities.map((opp, i) => (
              <<divdiv key={i} style={{ padding: '1.25rem', background: 'white', borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <<divdiv style={{ fontWeight: 800, color: '#1e293b' }}>{opp.name}</div>
                  <<divdiv style={{ fontSize: '0.8rem', color: '#64748b' }}>{opp.type} • {opp.benefit}</div>
                </div>
                <<buttonbutton className="vibrant-btn small" style={{ background: '#10b981', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 700 }}>Learn More</button>
              </div>
            )) : (
              <<divdiv style={{ textAlign: 'center', padding: '3rem 0', color: '#94a3b8' }}>
                <<divdiv style={{ fontSize: '2rem' }}>📉</div>
                <<pp>Improve your score to unlock carbon credit opportunities.</p>
              </div>
            )}
          </div>

          <<divdiv style={{ marginTop: '2rem', padding: '1.25rem', background: 'white', borderRadius: '20px', border: '1px solid #e2e8f0' }}>
            <<hh4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#1e293b' }}>How it works?</h4>
            <<pp style={{ fontSize: '0.8rem', color: '#64748b', margin: 0, lineHeight: '1.5' }}>
              We analyze your diary for sustainable practices like <strong>No-Till</strong> or <strong>Organic Composting</strong>.
              These practices sequester carbon in the soil, which can be sold as credits to companies offsetting their emissions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
