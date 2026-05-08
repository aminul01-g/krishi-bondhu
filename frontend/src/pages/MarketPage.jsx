import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getMarketAdvice, getMarketHistory } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

const CROPS = ['ধান', 'গম', 'ভুট্টা', 'আলু', 'পেঁয়াজ', 'রসুন', 'মরিচ', 'টমেটো', 'বেগুন', 'পাট'];

export default function MarketPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [crop, setCrop] = useState('');
  const [advice, setAdvice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchAdvice = async (selectedCrop) => {
    setCrop(selectedCrop);
    if (!selectedCrop) return;
    setLoading(true);
    setError('');
    try {
      const data = await getMarketAdvice(selectedCrop, lat, lon);
      setAdvice(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Crop selector */}
      <div className="card">
        <label className="block text-sm font-medium text-text-primary mb-2">
          🌾 {t('market.select_crop')}
        </label>
        <div className="flex flex-wrap gap-2">
          {CROPS.map((c) => (
            <button
              key={c}
              onClick={() => fetchAdvice(c)}
              className={`px-3 py-1.5 rounded-pill text-sm font-medium transition-all
                ${crop === c
                  ? 'bg-primary text-white shadow-card'
                  : 'bg-bg text-text-secondary hover:bg-primary/10 hover:text-primary'}`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {loading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" className="text-primary" />
        </div>
      )}

      {error && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center">
          {error}
          <button onClick={() => fetchAdvice(crop)} className="block mx-auto mt-2 text-primary font-medium">
            {t('common.retry')}
          </button>
        </div>
      )}

      {advice && !loading && (
        <div className="card-elevated space-y-3">
          <div className="flex items-center gap-2">
            <span className="badge-success">📊 {t('market.advice')}</span>
            <span className="text-sm font-semibold text-primary">{advice.crop}</span>
          </div>
          <div className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
            {advice.advice}
          </div>
        </div>
      )}

      {!crop && !loading && (
        <EmptyState icon="🌾" title={t('market.select_crop')} message={t('market.no_data')} />
      )}
    </div>
  );
}
