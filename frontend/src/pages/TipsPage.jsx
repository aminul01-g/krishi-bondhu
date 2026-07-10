import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import { getRecommendations } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';

/* ─── Source chip metadata ───────────────────────────────────
 * Maps the backend `source` field to a label, icon and color so each
 * advisory in the feed is visually attributable to the signal it came from.
 */
const SOURCE_META = {
  soil_test:       { label: 'Soil Test',       icon: '🌱', cls: 'bg-[#E6F4EA] text-[#1B7A3D] border-[#9BD3AE]' },
  water_balance:   { label: 'Water Balance',   icon: '💧', cls: 'bg-[#E6F1FB] text-[#1C5FA8] border-[#9CC4EC]' },
  irrigation_log:  { label: 'Irrigation Log',  icon: '🚿', cls: 'bg-[#E6F1FB] text-[#1C5FA8] border-[#9CC4EC]' },
  pest_risk_model: { label: 'Pest Risk Model', icon: '🐛', cls: 'bg-[#FDECEC] text-[#C2303A] border-[#F3A9AE]' },
  market_forecast: { label: 'Market Forecast', icon: '📈', cls: 'bg-[#F1ECFB] text-[#6B3FA0] border-[#CDB8EC]' },
  diary:           { label: 'Diary',           icon: '📔', cls: 'bg-[#FFF6E0] text-[#9A6A00] border-[#E9C46A]' },
};
const sourceMeta = (s) =>
  SOURCE_META[s] || { label: s || 'Advisory', icon: '⭐', cls: 'bg-border text-text-secondary border-border' };

/* ─── Priority pill metadata ───────────────────────────────── */
const PRIORITY_META = {
  1: { label: 'Urgent · জরুরি',     cls: 'bg-danger-light text-danger' },
  2: { label: 'High · গুরুত্বপূর্ণ', cls: 'bg-[#FFF6E0] text-[#9A6A00]' },
  3: { label: 'Medium · মাঝারি',    cls: 'bg-[#E6F1FB] text-[#1C5FA8]' },
  4: { label: 'Low · সাধারণ',       cls: 'bg-border text-text-secondary' },
};
const priorityMeta = (p) => PRIORITY_META[p] || PRIORITY_META[4];

function priorityColor(p) {
  return { 1: '#E63946', 2: '#D4A017', 3: '#1C5FA8', 4: '#6B7280' }[p] || '#6B7280';
}

function SourceChip({ source }) {
  const m = sourceMeta(source);
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-pill text-[11px] font-semibold border ${m.cls}`}>
      <span>{m.icon}</span>{m.label}
    </span>
  );
}

function AdvisoryCard({ adv }) {
  const pri = priorityMeta(adv.priority);
  const border = priorityColor(adv.priority);
  return (
    <article
      className="card-elevated border-l-4"
      style={{ borderLeftColor: border }}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center px-2.5 py-1 rounded-pill text-[11px] font-bold ${pri.cls}`}>
            {pri.label}
          </span>
          <SourceChip source={adv.source} />
        </div>
        {adv.due && (
          <span className="text-[11px] text-text-secondary">⏳ {adv.due}</span>
        )}
      </div>

      <h3 className="font-semibold text-text-primary mt-3 leading-snug">{adv.title}</h3>
      {adv.detail && (
        <p className="text-sm text-text-primary mt-1.5 leading-relaxed">{adv.detail}</p>
      )}
      {adv.reason && (
        <div className="mt-3 bg-bg rounded-card p-3">
          <p className="text-[11px] font-semibold text-text-secondary mb-1">কেন / Why</p>
          <p className="text-xs text-text-secondary leading-relaxed">{adv.reason}</p>
        </div>
      )}
    </article>
  );
}

/* ─── Page ─────────────────────────────────────────────────── */
export default function TipsPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // getRecommendations wraps the service output under `data`.
      const res = await getRecommendations(lat, lon, 'bn');
      setData(res.data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [lat, lon]);

  // Load on mount (and whenever GPS first resolves).
  useEffect(() => { load(); }, [load]);

  const advisories = data?.advisories || [];
  const sorted = [...advisories].sort((a, b) => (a.priority ?? 9) - (b.priority ?? 9));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card-elevated bg-primary text-white border-none">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold">💡 {t('tips.title', 'Advisory Feed')}</h1>
            <p className="text-sm text-white/80 mt-1">
              {t('tips.subtitle', 'Personalized, prioritized farming advice from your farm signals.')}
            </p>
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="shrink-0 bg-white/15 hover:bg-white/25 text-white rounded-btn px-3 py-2 text-sm font-medium flex items-center gap-1"
          >
            {loading ? <Spinner size="sm" /> : '↻'} {t('common.refresh', 'Refresh')}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center">{error}</div>
      )}

      {loading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card-elevated"><Skeleton lines={3} /></div>
          ))}
        </div>
      )}

      {!loading && !error && sorted.length === 0 && (
        <EmptyState
          icon="💡"
          title={t('tips.no_tips', 'No advisories right now')}
          message={t('tips.no_tips_msg', 'Your farm signals look healthy. Check back after logging activities.')}
        />
      )}

      {!loading && !error && sorted.length > 0 && (
        <>
          {/* Narrative summary */}
          {data.personalized_advice && (
            <div className="card-elevated border-l-4 border-primary">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">📝</span>
                <h3 className="font-semibold text-primary">{t('tips.summary', 'Your Plan')}</h3>
              </div>
              <div className="text-sm text-text-primary leading-relaxed">
                <ReactMarkdown>{data.personalized_advice}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Advisory cards */}
          <div className="space-y-3">
            {sorted.map((adv, i) => (
              <AdvisoryCard key={`${adv.source}-${i}`} adv={adv} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
