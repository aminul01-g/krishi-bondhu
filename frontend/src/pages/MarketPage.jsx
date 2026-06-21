import { useState } from 'react';
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
import { getMarketAdvice } from '../services/api';
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
        <p key={entry.dataKey} style={{ color: entry.color, margin: 0 }}>
          {entry.name}: {formatPriceBn(entry.value)}/কেজি
        </p>
      ))}
    </div>
  );
};

function PriceTrendChart({ history = [], forecast = [] }) {
  const today = new Date().toISOString().slice(0, 10);

  // Merge into a unified dataset
  const historyData = history.map((p) => ({
    date: p.date,
    historical: p.price,
    forecast: undefined,
  }));
  const forecastData = forecast.map((p) => ({
    date: p.date,
    historical: undefined,
    forecast: p.price,
  }));
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
      <ResponsiveContainer width="100%" height={200}>
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
      </div>
    </div>
  );
}

/* ─── Component 2: Sell/Wait Decision Badge ───────────────────── */

const DECISION_CONFIG = {
  up: {
    bg: 'linear-gradient(135deg,#052e16 0%,#14532d 100%)',
    border: '#16a34a',
    iconBg: 'rgba(22,163,74,0.15)',
    title: 'এখন বিক্রি করুন ✅',
    subtitle: 'দাম আরও বাড়তে পারে',
    textColor: '#4ade80',
    badgeColor: '#22c55e',
  },
  down: {
    bg: 'linear-gradient(135deg,#450a0a 0%,#7f1d1d 100%)',
    border: '#dc2626',
    iconBg: 'rgba(220,38,38,0.15)',
    title: 'অপেক্ষা করুন ⏳',
    subtitle: 'দাম কমার সম্ভাবনা আছে',
    textColor: '#f87171',
    badgeColor: '#ef4444',
  },
  flat: {
    bg: 'linear-gradient(135deg,#0f172a 0%,#1e293b 100%)',
    border: '#475569',
    iconBg: 'rgba(71,85,105,0.2)',
    title: 'যেকোনো সময় বিক্রি করুন',
    subtitle: 'দাম তুলনামূলক স্থিতিশীল',
    textColor: '#94a3b8',
    badgeColor: '#64748b',
  },
};

function DecisionBadge({ direction, percent }) {
  const cfg = DECISION_CONFIG[direction] || DECISION_CONFIG.flat;
  const sign = direction === 'up' ? '+' : direction === 'down' ? '-' : '±';
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
        {direction === 'up' ? '📈' : direction === 'down' ? '📉' : '📊'}
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
          {sign}{Math.abs(percent).toFixed(1)}%
        </p>
        <p style={{ fontSize: 9, color: '#64748b', margin: 0 }}>৭ দিনে</p>
      </div>
    </div>
  );
}

/* ─── Component 3: Key Stats Row ──────────────────────────────── */

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

/* ─── Main Page ───────────────────────────────────────────────── */

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

  const hasChartData =
    advice &&
    Array.isArray(advice.price_history) &&
    advice.price_history.length > 0;

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

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" className="text-primary" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center">
          {error}
          <button
            onClick={() => fetchAdvice(crop)}
            className="block mx-auto mt-2 text-primary font-medium"
          >
            {t('common.retry')}
          </button>
        </div>
      )}

      {/* Visual Results */}
      {advice && !loading && (
        <div className="space-y-3">
          {/* Section header */}
          <div className="flex items-center gap-2">
            <span className="badge-success">📊 {t('market.advice')}</span>
            <span className="text-sm font-semibold text-primary">{advice.crop}</span>
            {advice.confidence && (
              <span
                style={{
                  fontSize: 10,
                  color: '#64748b',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 6,
                  padding: '2px 7px',
                  marginLeft: 'auto',
                }}
              >
                {advice.confidence}
              </span>
            )}
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
          {advice.current_avg != null && (
            <KeyStatsRow advice={advice} />
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

      {/* Empty state */}
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
