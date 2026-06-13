import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postWaterAdvice } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

export default function WaterPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [crop, setCrop] = useState('Rice');
  const [advice, setAdvice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchAdvice = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await postWaterAdvice(lat || 23.81, lon || 90.41, crop);
      setAdvice(data);
    } catch (err) {
      setError('Unable to get irrigation advice. Check your connection.');
    }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      {/* Error alert */}
      {error && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center font-semibold">
          ⚠️ {error}
        </div>
      )}

      <div className="card flex items-center gap-2">
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className="input-field flex-1 !py-2">
          {['Rice', 'Wheat', 'Potato', 'Maize', 'Jute'].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button onClick={fetchAdvice} disabled={loading} className="btn-primary !py-2.5 flex items-center gap-1">
          {loading ? <Spinner size="sm" /> : '💧'} {t('common.search')}
        </button>
      </div>

      {advice && !loading && (
        <div className="card-elevated border-l-4 border-sky">
          <h3 className="font-semibold text-sky mb-2 flex items-center gap-2">💧 {t('nav.water')}</h3>
          {advice.moisture_index != null && (
            <div className="bg-sky/10 rounded-btn p-3 mb-3 text-center">
              <p className="text-xs text-text-secondary">Moisture Index</p>
              <p className="text-2xl font-bold text-sky">{(advice.moisture_index * 100).toFixed(0)}%</p>
            </div>
          )}
          <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">{advice.advice}</p>
        </div>
      )}

      {!advice && !loading && <EmptyState icon="💧" title={t('nav.water')} message="Get irrigation advice for your crop" />}
    </div>
  );
}
