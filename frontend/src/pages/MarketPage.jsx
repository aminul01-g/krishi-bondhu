import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { getMarketAdvice, getMarketHistory } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

const CROPS = ['ধান', 'গম', 'ভুট্টা', 'আলু', 'পেঁয়াজ', 'রসুন', 'মরিচ', 'টমেটো', 'বেগুন', 'পাট'];

/* ─── Helpers ──────────────────────────────────────────────────── */

function formatDateBn(dateStr) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('bn-BD', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function formatPriceBn(value) {
  return `৳${Number(value).toFixed(0)}`;
}

function calcTrendInfo(advice) {
  const direction = advice?.trend_direction || 'flat';
  const percent = advice?.trend_percent ?? 0;
  const currentAvg = advice?.current_avg ?? 0;
  const predicted = advice?.predicted_7day ?? 0;
  return { direction, percent, currentAvg, predicted };
}

/* ─── Component 0: Loading Skeleton ───────────────────────────── */

function MarketSkeleton() {
  return (
    <div className="space-y-3">
      <div className="card" style={{ padding: 16 }}>
        <div
          className="animate-pulse"
          style={{ height: 14, width: '45%', background: 'rgba(255,255,255,0.1)', borderRadius: 6, marginBottom: 12 }}
        />
        <div
          className="animate-pulse"
          style={{ height: 200, width: '100%', background: 'rgba(255,255,255,0.05)', borderRadius: 10 }}
        />
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="animate-pulse"
            style={{ flex: 1, height: 64, background: 'rgba(255,255,255,0.05)', borderRadius: 12 }}
          />
        ))}
      </div>
      <div
        className="animate-pulse"
        style={{ height: 78, width: '100%', background: 'rgba(255,255,255,0.05)', borderRadius: 14 }}
      />
    </div>
  );
}

/* ─── Component 1: Price Trend Chart ──────────────────────────── */

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: 'var(--color-surface, #1e293b)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 10,
        padding: '8px 12px',
        fontSize: 12,
        color: '#e2e8f0',
      }}
    >
      <p style={{ fontWeight: 600, marginBottom: 2 }}>{formatDateBn(label)}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} style={{ color: entry.color || entry.stroke, margin: 0 }}>
          {entry.name}: {entry.value == null ? '—' : `${formatPriceBn(entry.value)}/কেজি`}
        </p>
      ))}
    </div>
  );
};

function PriceTrendChart({ history = [], forecast = [] }) {
  const today = new Date().toISOString().slice(0, 10);

  // Historical line: solid blue.
  const historyData = history.map((p) => ({
    date: p.date,
    historical: p.price,
  }));

  // Forecast continuation: dashed amber central line + shaded confidence band.
  const forecastData = forecast.map((p) => ({
    date: p.date,
    forecast: p.price,
    // Recharts renders a range area when the value is a [low, high] pair.
    band: [p.low ?? p.price, p.high ?? p.price],
  }));

  // Anchor the forecast back to the last known price so the dashed line and the
  // confidence band connect to the solid historical line (no broken gap).
  if (historyData.length && forecastData.length) {
    forecastData[0].historical = historyData[historyData.length - 1].historical;
  }

  const data = [...historyData, ...forecastData];

  return (
    <div className="card" style={{ padding: '16px 8px 8px 0' }}>
      <p
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: 'var(--color-text-secondary, #94a3b8)',
          marginBottom: 8,
          paddingLeft: 16,
        }}
      >
        📈 দামের প্রবণতা (গত ১৪ দিন + আগামী ৭ দিন)
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateBn}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            interval={3}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `৳${v}`}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
            width={40}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            x={today}
            stroke="rgba(255,255,255,0.25)"
            strokeDasharray="4 4"
            label={{
              value: 'আজ',
              position: 'insideTopRight',
              fontSize: 10,
              fill: '#94a3b8',
            }}
          />
          {/* Historical solid line + gradient fill */}
          <Area
            type="monotone"
            dataKey="historical"
            name="ঐতিহাসিক"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#histGrad)"
            dot={false}
            connectNulls={false}
          />
          {/* Forecast confidence band (low → high) */}
          <Area
            type="monotone"
            dataKey="band"
            name="অনুমান ব্যান্ড"
            stroke="transparent"
            strokeWidth={0}
            fill="#f59e0b"
            fillOpacity={0.16}
            dot={false}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          {/* Forecast central dashed line */}
          <Line
            type="monotone"
            dataKey="forecast"
            name="পূর্বাভাস"
            stroke="#f59e0b"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={{ r: 3, fill: '#f59e0b', strokeWidth: 0 }}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div
        style={{
          display: 'flex',
          gap: 16,
          paddingLeft: 16,
          marginTop: 6,
          fontSize: 11,
          color: '#64748b',
          flexWrap: 'wrap',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span
            style={{
              width: 24,
              height: 3,
              background: '#3b82f6',
              display: 'inline-block',
              borderRadius: 2,
            }}
          />
          ঐতিহাসিক দাম
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span
            style={{
              width: 24,
              height: 3,
              background: '#f59e0b',
              display: 'inline-block',
              borderRadius: 2,
              backgroundImage:
                'repeating-linear-gradient(90deg,#f59e0b 0,#f59e0b 6px,transparent 6px,transparent 9px)',
            }}
          />
          অনুমানিত দাম
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span
            style={{
              width: 24,
              height: 10,
              background: 'rgba(245,158,11,0.18)',
              border: '1px solid rgba(245,158,11,0.4)',
              display: 'inline-block',
              borderRadius: 2,
            }}
          />
          অনিশ্চয়তা ব্যান্ড
        </span>
      </div>
    </div>
  );
}

/* ─── Component 2: Sell/Hold Decision Badge ───────────────────── */

// Economics: if the forecast is LOWER than today → sell now (price falling).
// If the forecast is HIGHER → hold (price rising, wait for a better rate).
function decideAction(direction) {
  if (direction === 'down') return 'sell';
  if (direction === 'up') return 'hold';
  return 'neutral';
}

const DECISION_CONFIG = {
  sell: {
    bg: 'linear-gradient(135deg,#450a0a 0%,#7f1d1d 100%)',
    border: '#dc2626',
    iconBg: 'rgba(220,38,38,0.15)',
    icon: '🔻',
    title: 'এখনই বিক্রি করুন',
    subtitle: 'দাম কমছে — আরও পড়ার আগেই বিক্রি করে ফেলুন',
    textColor: '#f87171',
    badgeColor: '#ef4444',
  },
  hold: {
    bg: 'linear-gradient(135deg,#052e16 0%,#14532d 100%)',
    border: '#16a34a',
    iconBg: 'rgba(22,163,74,0.15)',
    icon: '📈',
    title: 'অপেক্ষা করুন (ধরে রাখুন)',
    subtitle: 'দাম বাড়ছে — কয়েকদিন অপেক্ষা করলে বেশি দাম পাবেন',
    textColor: '#4ade80',
    badgeColor: '#22c55e',
  },
  neutral: {
    bg: 'linear-gradient(135deg,#0f172a 0%,#1e293b 100%)',
    border: '#475569',
    iconBg: 'rgba(71,85,105,0.2)',
    icon: '📊',
    title: 'যেকোনো সময় বিক্রি করুন',
    subtitle: 'দাম তুলনামূলক স্থিতিশীল',
    textColor: '#94a3b8',
    badgeColor: '#64748b',
  },
};

function DecisionBadge({ direction, percent }) {
  const action = decideAction(direction);
  const cfg = DECISION_CONFIG[action];
  const arrow = action === 'sell' ? '↓' : action === 'hold' ? '↑' : '±';
  return (
    <div
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: 14,
        padding: '16px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
      }}
    >
      <div
        style={{
          width: 52,
          height: 52,
          borderRadius: '50%',
          background: cfg.iconBg,
          border: `2px solid ${cfg.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 22,
          flexShrink: 0,
        }}
      >
        {cfg.icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: cfg.textColor,
            margin: 0,
            lineHeight: 1.3,
          }}
        >
          {cfg.title}
        </p>
        <p style={{ fontSize: 12, color: '#94a3b8', margin: '3px 0 0', lineHeight: 1.4 }}>
          {cfg.subtitle}
        </p>
      </div>
      <div
        style={{
          background: cfg.iconBg,
          border: `1px solid ${cfg.border}`,
          borderRadius: 8,
          padding: '4px 10px',
          textAlign: 'center',
          flexShrink: 0,
        }}
      >
        <p style={{ fontSize: 16, fontWeight: 700, color: cfg.badgeColor, margin: 0 }}>
          {arrow}{Math.abs(percent).toFixed(1)}%
        </p>
        <p style={{ fontSize: 9, color: '#64748b', margin: 0 }}>৭ দিনে</p>
      </div>
    </div>
  );
}

/* ─── Component 3: Provenance Badge ───────────────────────────── */

// Honestly reflects where the numbers came from so a farmer is never misled.
// Primary signal is the backend `confidence` note; a real persisted mandi
// observation in the DB upgrades the badge to "partially real".
function ProvenanceBadge({ advice, history }) {
  const confidence = advice?.confidence || '';
  const realMandis =
    history && history.mandi_averages ? Object.keys(history.mandi_averages) : [];
  const hasRealDb = realMandis.length > 0;

  const looksSimulated =
    /simulat|seasonal|heuristic|calibrat|predict|model/i.test(confidence) ||
    (!hasRealDb && !confidence);

  let tone, label, icon;
  if (hasRealDb) {
    tone = {
      bg: 'rgba(245,158,11,0.15)',
      border: '#f59e0b',
      text: '#fbbf24',
    };
    label = 'আংশিক বাস্তব';
    icon = '🟡';
  } else if (looksSimulated) {
    tone = {
      bg: 'rgba(100,116,139,0.15)',
      border: '#64748b',
      text: '#94a3b8',
    };
    label = 'অনুমানিত';
    icon = '⚠️';
  } else {
    tone = {
      bg: 'rgba(34,197,94,0.15)',
      border: '#22c55e',
      text: '#4ade80',
    };
    label = 'বাস্তব';
    icon = '✅';
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flexWrap: 'wrap',
        fontSize: 11,
      }}
    >
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          background: tone.bg,
          border: `1px solid ${tone.border}`,
          color: tone.text,
          borderRadius: 999,
          padding: '3px 10px',
          fontWeight: 600,
          whiteSpace: 'nowrap',
        }}
      >
        {icon} {label}
      </span>
      {hasRealDb && (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            background: 'rgba(34,197,94,0.12)',
            border: '1px solid #22c55e',
            color: '#4ade80',
            borderRadius: 999,
            padding: '3px 10px',
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          🛒 {realMandis.length}টি মন্ডি থেকে বাস্তব তথ্য
        </span>
      )}
      <span style={{ color: '#64748b', lineHeight: 1.3 }}>
        {confidence || (hasRealDb ? 'ডেটাবেসে সংরক্ষিত বাস্তব মন্ডি পর্যবেক্ষণ' : 'উৎস সম্পর্কে তথ্য নেই')}
      </span>
    </div>
  );
}

/* ─── Component 4: Key Stats Row ──────────────────────────────── */

function StatCard({ label, value, sub, accent }) {
  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 12,
        padding: '12px 14px',
        flex: 1,
        minWidth: 0,
        textAlign: 'center',
      }}
    >
      <p style={{ fontSize: 10, color: '#64748b', margin: '0 0 4px', lineHeight: 1.2 }}>{label}</p>
      <p
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: accent || 'var(--color-text-primary, #f1f5f9)',
          margin: 0,
          lineHeight: 1.2,
        }}
      >
        {value}
      </p>
      {sub && (
        <p style={{ fontSize: 10, color: '#94a3b8', margin: '3px 0 0' }}>{sub}</p>
      )}
    </div>
  );
}

function KeyStatsRow({ advice }) {
  const { direction, percent, currentAvg, predicted } = calcTrendInfo(advice);
  const changeColor =
    direction === 'up' ? '#4ade80' : direction === 'down' ? '#f87171' : '#94a3b8';
  const changePrefix = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '±';

  return (
    <div style={{ display: 'flex', gap: 8 }}>
      <StatCard
        label="আজকের দাম"
        value={`৳${currentAvg.toFixed(0)}/কেজি`}
        sub="বাজার গড়"
        accent="#60a5fa"
      />
      <StatCard
        label="৭ দিনের পূর্বাভাস"
        value={`৳${predicted.toFixed(0)}/কেজি`}
        sub="অনুমানিত দাম"
        accent="#fbbf24"
      />
      <StatCard
        label="পরিবর্তন"
        value={`${changePrefix}${Math.abs(percent).toFixed(1)}%`}
        sub="৭ দিনে"
        accent={changeColor}
      />
    </div>
  );
}

/* ─── Component 5: Real Mandi Observations (from /history) ───── */

function RealMandiCard({ history }) {
  const mandis = history?.mandi_averages;
  if (!mandis || Object.keys(mandis).length === 0) return null;
  const best = history.best_price_mandi;
  const worst = history.worst_price_mandi;
  const bestAvg = mandis[best];
  const worstAvg = mandis[worst];
  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <p
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: '#94a3b8',
          margin: '0 0 10px',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        🛒 বাস্তব মন্ডি পর্যবেক্ষণ{' '}
        <span style={{ fontSize: 10, color: '#64748b' }}>
          (গত {history.period_days} দিন, ডেটাবেস থেকে)
        </span>
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 120 }}>
          <p style={{ fontSize: 11, color: '#4ade80', margin: 0 }}>সর্বোচ্চ দাম</p>
          <p style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9', margin: '2px 0 0' }}>
            {best}
          </p>
          <p style={{ fontSize: 14, fontWeight: 700, color: '#4ade80', margin: '2px 0 0' }}>
            ৳{bestAvg}/কেজি
          </p>
        </div>
        <div style={{ flex: 1, minWidth: 120 }}>
          <p style={{ fontSize: 11, color: '#f87171', margin: 0 }}>সর্বনিম্ন দাম</p>
          <p style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9', margin: '2px 0 0' }}>
            {worst}
          </p>
          <p style={{ fontSize: 14, fontWeight: 700, color: '#f87171', margin: '2px 0 0' }}>
            ৳{worstAvg}/কেজি
          </p>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Page ───────────────────────────────────────────────── */

export default function MarketPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [crop, setCrop] = useState(CROPS[0]); // load a default crop on mount
  const [advice, setAdvice] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  // Fetch both the advisory and the persisted history with a single
  // AbortController so unmount / crop-change cancels in-flight requests.
  useEffect(() => {
    if (!crop) return;
    const ctrl = new AbortController();
    let active = true;
    setLoading(true);
    setError('');

    Promise.all([
      getMarketAdvice(crop, lat, lon, ctrl.signal),
      getMarketHistory(crop, 14, ctrl.signal),
    ])
      .then(([adv, hist]) => {
        if (!active) return;
        setAdvice(adv);
        setHistory(hist);
      })
      .catch((err) => {
        if (!active || err.name === 'AbortError') return;
        setError(err?.message || t('common.error'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      ctrl.abort();
    };
  }, [crop, lat, lon, reloadKey, t]);

  const hasChartData =
    advice &&
    Array.isArray(advice.price_history) &&
    advice.price_history.length > 0;

  const selectCrop = (selectedCrop) => {
    if (selectedCrop === crop) return;
    setCrop(selectedCrop);
  };

  const retry = () => {
    setError('');
    setReloadKey((k) => k + 1);
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
              onClick={() => selectCrop(c)}
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

      {/* Loading skeleton */}
      {loading && <MarketSkeleton />}

      {/* Error */}
      {error && !loading && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center">
          {error}
          <button
            onClick={retry}
            className="block mx-auto mt-2 text-primary font-medium"
          >
            {t('common.retry')}
          </button>
        </div>
      )}

      {/* Visual Results */}
      {advice && !loading && !error && (
        <div className="space-y-3">
          {/* Section header + provenance */}
          <div className="flex items-center gap-2">
            <span className="badge-success">📊 {t('market.advice')}</span>
            <span className="text-sm font-semibold text-primary">{advice.crop}</span>
            <span style={{ marginLeft: 'auto' }}>
              <ProvenanceBadge advice={advice} history={history} />
            </span>
          </div>

          {/* Component 1: Chart */}
          {hasChartData && (
            <PriceTrendChart
              history={advice.price_history}
              forecast={advice.price_forecast || []}
            />
          )}

          {/* Component 2: Decision badge */}
          {advice.trend_direction && (
            <DecisionBadge
              direction={advice.trend_direction}
              percent={advice.trend_percent ?? 0}
            />
          )}

          {/* Component 3: Stats row */}
          {advice.current_avg != null && <KeyStatsRow advice={advice} />}

          {/* Real persisted mandi observations */}
          {history && !history.error && !history.message && (
            <RealMandiCard history={history} />
          )}

          {/* Fallback: AI advice text */}
          {advice.advice && (
            <div className="card-elevated">
              <p className="text-xs font-semibold text-text-secondary mb-2">
                🤖 AI পরামর্শ
              </p>
              <div className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
                {advice.advice}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state (only when no crop is selected) */}
      {!crop && !loading && (
        <EmptyState
          icon="🌾"
          title={t('market.select_crop')}
          message={t('market.no_data')}
        />
      )}
    </div>
  );
}
