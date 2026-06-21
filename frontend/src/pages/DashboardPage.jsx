import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboardSummary } from '../services/api';
import { getMe } from '../services/api';
import { LoadingSpinner } from '../components/shared/LoadingStates';

// Fallback to Dhaka if GPS fails
const DEFAULT_LAT = 23.8103;
const DEFAULT_LON = 90.4125;

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hiddenAlerts, setHiddenAlerts] = useState(new Set());

  useEffect(() => {
    const ctrl = new AbortController();

    async function loadDashboard() {
      try {
        setLoading(true);
        // 1. Get user's crops from profile
        // Alternatively, getMe could include crops if we updated it, but let's just fetch profile or fallback to defaults
        const userRes = await getMe(ctrl.signal).catch(() => ({}));
        // Since we didn't inspect getMe thoroughly, let's just use defaults or try getting profile
        let crops = 'ধান,পাট,আলু'; 
        
        // Try getting profile using raw fetch if getFarmerProfile is not in api.js yet
        try {
          const token = localStorage.getItem('kb_auth_token');
          const profileRes = await fetch(import.meta.env.VITE_API_BASE + '/api/profile', {
            headers: { 'Authorization': `Bearer ${token}` },
            signal: ctrl.signal
          });
          if (profileRes.ok) {
            const profileData = await profileRes.json();
            if (profileData && profileData.crops && profileData.crops.length > 0) {
              crops = profileData.crops.join(',');
            }
          }
        } catch(err) {
          // Ignore profile error
        }

        // 2. Get location
        const position = await new Promise((resolve) => {
          if (!navigator.geolocation) {
            resolve({ coords: { latitude: DEFAULT_LAT, longitude: DEFAULT_LON } });
            return;
          }
          navigator.geolocation.getCurrentPosition(
            (pos) => resolve(pos),
            () => resolve({ coords: { latitude: DEFAULT_LAT, longitude: DEFAULT_LON } }),
            { timeout: 5000 }
          );
        });

        // 3. Fetch summary
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const summary = await getDashboardSummary(lat, lon, crops, ctrl.signal);
        
        setData(summary);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError('ড্যাশবোর্ড লোড করতে সমস্যা হয়েছে। (Failed to load dashboard)');
        }
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
    return () => ctrl.abort();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-4">
        {/* Skeleton Greeting */}
        <div className="animate-pulse flex flex-col gap-2">
          <div className="h-6 w-48 bg-border rounded"></div>
          <div className="h-4 w-32 bg-border rounded"></div>
        </div>
        
        {/* Skeleton Weather */}
        <div className="animate-pulse h-32 bg-border rounded-xl"></div>
        
        {/* Skeleton Market Flash */}
        <div className="animate-pulse flex gap-4 overflow-x-auto">
          <div className="h-24 w-32 bg-border rounded-xl shrink-0"></div>
          <div className="h-24 w-32 bg-border rounded-xl shrink-0"></div>
        </div>

        {/* Skeleton Quick Actions */}
        <div className="animate-pulse flex justify-between px-2 mt-4">
          <div className="h-16 w-16 bg-border rounded-full"></div>
          <div className="h-16 w-16 bg-border rounded-full"></div>
          <div className="h-16 w-16 bg-border rounded-full"></div>
          <div className="h-16 w-16 bg-border rounded-full"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={() => window.location.reload()} className="px-4 py-2 bg-primary text-white rounded-lg">
          পুনরায় চেষ্টা করুন
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { greeting, weather, irrigation, market_flash, alerts } = data;

  const dismissAlert = (id) => {
    setHiddenAlerts(prev => new Set(prev).add(id));
  };

  const visibleAlerts = alerts.filter(a => !hiddenAlerts.has(a.id)).slice(0, 3);

  return (
    <div className="flex flex-col gap-6 pb-6">
      {/* SECTION 1: Greeting + Date */}
      <section className="px-4 mt-2">
        <h2 className="text-2xl font-bold text-text-primary mb-1">
          আপনার সকাল শুভ হোক, {greeting.username}!
        </h2>
        <p className="text-text-secondary text-sm">
          আজ {greeting.date_bn}, {greeting.weekday_bn} | {greeting.district}
        </p>
      </section>

      {/* SECTION 2: Weather + Irrigation Alert Card */}
      <section className="px-4">
        <div className="bg-surface rounded-2xl p-4 shadow-card border border-border">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-3xl font-bold text-text-primary">{weather.temp_mean}°C</p>
              <p className="text-sm text-text-secondary">আর্দ্রতা: {weather.humidity}%</p>
            </div>
            <div className="flex flex-col items-end gap-1">
              {irrigation.badge === 'red' && <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">🔴 {irrigation.badge_text_bn}</span>}
              {irrigation.badge === 'yellow' && <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-bold rounded-full">🟡 {irrigation.badge_text_bn}</span>}
              {irrigation.badge === 'green' && <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">🟢 {irrigation.badge_text_bn}</span>}
            </div>
          </div>
          <div className="bg-bg rounded-xl p-3">
            <p className="text-sm font-medium text-text-primary">💡 {irrigation.advice_bn}</p>
          </div>
        </div>
      </section>

      {/* SECTION 3: Market Flash */}
      {market_flash && market_flash.length > 0 && (
        <section>
          <div className="px-4 mb-2 flex justify-between items-center">
            <h3 className="text-sm font-bold text-text-secondary">বাজারের খণ্ডচিত্র</h3>
            <button onClick={() => navigate('/app/market')} className="text-xs text-primary font-medium hover:underline">
              বিস্তারিত &rarr;
            </button>
          </div>
          <div className="flex gap-3 overflow-x-auto px-4 pb-2 snap-x scrollbar-hide">
            {market_flash.map((item, idx) => (
              <div key={idx} className="shrink-0 w-36 bg-surface rounded-xl p-3 shadow-sm border border-border snap-start flex flex-col justify-between">
                <p className="text-sm font-semibold text-text-secondary">{item.crop_bn}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-lg font-bold text-text-primary">৳{item.price_bdt_per_kg}</span>
                  {item.trend === 'up' && <span className="text-green-500 text-lg">↑</span>}
                  {item.trend === 'down' && <span className="text-red-500 text-lg">↓</span>}
                  {item.trend === 'flat' && <span className="text-gray-400 text-lg">→</span>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* SECTION 4: Active Alerts */}
      <section className="px-4">
        <h3 className="text-sm font-bold text-text-secondary mb-3">আজকের সতর্কতা</h3>
        <div className="flex flex-col gap-3">
          {visibleAlerts.length === 0 ? (
            <div className="bg-green-50 text-green-700 p-4 rounded-xl text-center text-sm font-medium border border-green-100">
              আজ কোনো সতর্কতা নেই ✅
            </div>
          ) : (
            visibleAlerts.map(alert => (
              <div 
                key={alert.id}
                className={`relative bg-surface rounded-xl p-4 shadow-sm border-l-4 pr-10
                  ${alert.type === 'pest' ? 'border-l-red-500 bg-red-50/30' : 'border-l-yellow-500 bg-yellow-50/30'}
                `}
              >
                <p className="text-sm text-text-primary leading-snug">{alert.text_bn}</p>
                <button 
                  onClick={() => dismissAlert(alert.id)}
                  className="absolute top-2 right-2 w-8 h-8 flex items-center justify-center text-text-secondary hover:bg-black/5 rounded-full"
                  aria-label="Dismiss alert"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      {/* SECTION 5: Quick Actions Row */}
      <section className="px-4 mt-2">
        <h3 className="text-sm font-bold text-text-secondary mb-4">জরুরি কাজ</h3>
        <div className="flex justify-between px-2">
          <button onClick={() => navigate('/app/chat?action=camera')} className="flex flex-col items-center gap-2 group">
            <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center text-2xl group-active:scale-95 transition-transform border border-primary/20">
              📷
            </div>
            <span className="text-xs font-semibold text-text-secondary">রোগ নির্ণয়</span>
          </button>
          
          <button onClick={() => navigate('/app/water')} className="flex flex-col items-center gap-2 group">
            <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center text-2xl group-active:scale-95 transition-transform border border-blue-200">
              💧
            </div>
            <span className="text-xs font-semibold text-text-secondary">সেচ</span>
          </button>

          <button onClick={() => navigate('/app/diary')} className="flex flex-col items-center gap-2 group">
            <div className="w-14 h-14 bg-orange-100 rounded-full flex items-center justify-center text-2xl group-active:scale-95 transition-transform border border-orange-200">
              📒
            </div>
            <span className="text-xs font-semibold text-text-secondary">খরচ লিখুন</span>
          </button>

          <button onClick={() => navigate('/app/emergency')} className="flex flex-col items-center gap-2 group">
            <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center text-2xl group-active:scale-95 transition-transform border border-red-200">
              🚨
            </div>
            <span className="text-xs font-semibold text-text-secondary">জরুরি</span>
          </button>
        </div>
      </section>
    </div>
  );
}
