import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getDailyAlert } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

export default function TipsPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [crop, setCrop] = useState('rice');
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchAlert = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getDailyAlert(crop, lat, lon);
      setAlert(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="card flex items-center gap-2">
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className="input-field flex-1 !py-2">
          {['rice', 'wheat', 'potato', 'maize', 'jute', 'onion'].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button onClick={fetchAlert} disabled={loading} className="btn-primary !py-2.5 flex items-center gap-1">
          {loading ? <Spinner size="sm" /> : '🔍'} {t('common.search')}
        </button>
      </div>

      {error && <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center">{error}</div>}

      {alert && !loading && (
        <>
          <div className="card-elevated border-l-4 border-primary">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">💡</span>
              <h3 className="font-semibold text-primary">{t('tips.today_tip')}</h3>
            </div>
            <p className="text-sm text-text-primary leading-relaxed">{alert.tip_bn}</p>
            {alert.audio_url && (
              <button onClick={() => new Audio(alert.audio_url).play()}
                className="mt-3 text-sm text-primary font-medium flex items-center gap-1 hover:underline">
                🔊 {t('tips.play_audio')}
              </button>
            )}
          </div>

          <div className="card-elevated border-l-4 border-danger">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">⚠️</span>
              <h3 className="font-semibold text-danger">{t('tips.pest_alert')}</h3>
            </div>
            <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
              {alert.pest_risk_alert}
            </p>
          </div>
        </>
      )}

      {!alert && !loading && <EmptyState icon="💡" title={t('tips.title')} message={t('tips.no_tips')} />}
    </div>
  );
}
