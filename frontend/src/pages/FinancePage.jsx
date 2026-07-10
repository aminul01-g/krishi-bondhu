import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import {
  postInsuranceQuote,
  postSimulatePayout,
  getSubsidies,
  getCreditReport,
} from '../services/api';
import { useApi } from '../hooks/useApi';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';

const CROPS = ['Rice', 'Wheat', 'Potato', 'Onion', 'Tomato', 'Brinjal', 'Chili', 'Mango', 'Jute'];
const REGION_RISKS = ['low', 'moderate', 'high'];
const SCENARIOS = [
  { value: 'drought', label: '🌵 Drought / খরা' },
  { value: 'flood', label: '🌊 Flood / বন্যা' },
];

/* ─── Inline helpers ─────────────────────────────────────────── */

const RISK_META = {
  low:      { label: 'Low · নিম্ন',       cls: 'bg-[#E6F4EA] text-[#1B7A3D] border-[#9BD3AE]' },
  moderate: { label: 'Moderate · মাঝারি', cls: 'bg-[#FFF6E0] text-[#9A6A00] border-[#E9C46A]' },
  high:     { label: 'High · উচ্চ',         cls: 'bg-danger-light text-danger border-[#F3A9AE]' },
};
const riskMeta = (c) => RISK_META[c] || RISK_META.moderate;

function RiskBadge({ risk }) {
  const m = riskMeta(risk);
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-pill text-xs font-semibold border ${m.cls}`}>
      {m.label}
    </span>
  );
}

function MetricBar({ label, value, max, color }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-text-secondary font-medium">{label}</span>
        <span className="text-text-primary font-semibold">{value} / {max}</span>
      </div>
      <div className="h-2 rounded-pill bg-border overflow-hidden">
        <div className="h-full rounded-pill transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function scoreColor(score) {
  if (score >= 80) return '#1B7A3D';
  if (score >= 60) return '#2D6A4F';
  if (score >= 40) return '#D4A017';
  return '#E63946';
}

function ErrorBox({ message }) {
  return (
    <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center">
      {message || 'Something went wrong. Please try again.'}
    </div>
  );
}

function fmt(n, unit = '') {
  if (n == null || Number.isNaN(n)) return '—';
  return `${Number(n).toLocaleString('en-IN')}${unit}`;
}

/* ─── Page ──────────────────────────────────────────────────── */

export default function FinancePage() {
  const { t } = useTranslation();

  // Credit report loads automatically (uses the auth'd user's diary data).
  const { data: credit, loading: creditLoading, error: creditError } =
    useApi((s) => getCreditReport(s), []);

  // Shared inputs
  const [crop, setCrop] = useState('Rice');
  const [landSize, setLandSize] = useState('100');
  const [regionRisk, setRegionRisk] = useState('moderate');
  const [lossRatio, setLossRatio] = useState('0');

  // Insurance quote
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState('');

  // Payout simulator
  const [scenario, setScenario] = useState('drought');
  const [severity, setSeverity] = useState(0.5);
  const [payout, setPayout] = useState(null);
  const [payoutLoading, setPayoutLoading] = useState(false);
  const [payoutError, setPayoutError] = useState('');

  // Subsidies
  const [subsidies, setSubsidies] = useState(null);
  const [subLoading, setSubLoading] = useState(false);
  const [subError, setSubError] = useState('');

  const fetchInsurance = async () => {
    setQuoteLoading(true);
    setQuoteError('');
    try {
      // NOTE: the api client forwards crop + landSize; regionRisk / lossRatio are
      // accepted by the backend endpoint but not yet forwarded by the client, so
      // they are passed along and used by the payout simulator below.
      const res = await postInsuranceQuote(
        crop,
        parseFloat(landSize),
        regionRisk,
        parseFloat(lossRatio || '0'),
      );
      setQuote(res);
    } catch (e) {
      setQuoteError(e.message);
    } finally {
      setQuoteLoading(false);
    }
  };

  const fetchPayout = async () => {
    setPayoutLoading(true);
    setPayoutError('');
    try {
      const res = await postSimulatePayout(
        crop,
        parseFloat(landSize),
        scenario,
        parseFloat(severity),
        regionRisk,
      );
      setPayout(res.data);
    } catch (e) {
      setPayoutError(e.message);
    } finally {
      setPayoutLoading(false);
    }
  };

  const fetchSubsidies = async () => {
    setSubLoading(true);
    setSubError('');
    try {
      const res = await getSubsidies(crop, parseFloat(landSize));
      setSubsidies(res);
    } catch (e) {
      setSubError(e.message);
    } finally {
      setSubLoading(false);
    }
  };

  // ---- Credit report ----
  const breakdown = credit?.breakdown || {};
  const creditScore = credit?.credit_score ?? null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="card-elevated bg-primary text-white border-none">
        <h1 className="text-xl font-bold">🪙 {t('finance.title', 'Farm Finance')}</h1>
        <p className="text-sm text-white/80 mt-1">
          {t('finance.subtitle', 'Insurance, credit readiness, payout simulation & government schemes.')}
        </p>
      </div>

      {/* ── Credit Readiness ── */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary mb-2 px-1">
          {t('finance.credit', 'Credit Readiness')}
        </h2>
        {creditLoading ? (
          <div className="card-elevated"><Skeleton lines={3} /></div>
        ) : creditError ? (
          <ErrorBox message={creditError} />
        ) : credit ? (
          <div className="card-elevated">
            <div className="flex items-center gap-4">
              <div
                className="w-20 h-20 rounded-full flex flex-col items-center justify-center shrink-0"
                style={{ background: `${scoreColor(creditScore)}1A`, color: scoreColor(creditScore) }}
              >
                <span className="text-2xl font-bold leading-none">{creditScore}</span>
                <span className="text-[10px] font-medium mt-0.5">/ 100</span>
              </div>
              <div className="flex-1 space-y-2">
                <MetricBar label="Consistency · নিয়মিত" value={breakdown.consistency ?? 0} max={40} color="#2D6A4F" />
                <MetricBar label="Profitability · লাভজনক" value={breakdown.profitability ?? 0} max={30} color="#D4A017" />
                <MetricBar label="Completeness · সম্পূর্ণতা" value={breakdown.completeness ?? 0} max={30} color="#40916C" />
              </div>
            </div>
            {credit.recommendation && (
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs font-semibold text-text-secondary mb-1">
                  {t('finance.recommendation', 'Recommendation')}
                </p>
                <div className="text-sm text-text-primary leading-relaxed">
                  <ReactMarkdown>{credit.recommendation}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </section>

      {/* ── Insurance Quote ── */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary mb-2 px-1">
          🛡️ {t('finance.insurance', 'Crop Insurance Quote')}
        </h2>
        <div className="card-elevated space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <select value={crop} onChange={(e) => setCrop(e.target.value)} className="input-field !py-2.5">
              {CROPS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input
              type="number" min="0" value={landSize}
              onChange={(e) => setLandSize(e.target.value)}
              placeholder="Land (decimal)" className="input-field !py-2.5"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select value={regionRisk} onChange={(e) => setRegionRisk(e.target.value)} className="input-field !py-2.5">
              {REGION_RISKS.map((r) => <option key={r} value={r}>Region risk: {r}</option>)}
            </select>
            <input
              type="number" min="0" max="1" step="0.05" value={lossRatio}
              onChange={(e) => setLossRatio(e.target.value)}
              placeholder="Loss ratio (0–1)" className="input-field !py-2.5"
              title="Historical loss ratio — advanced input used by the backend where supported."
            />
          </div>
          <button onClick={fetchInsurance} disabled={quoteLoading} className="btn-primary w-full flex items-center justify-center gap-2">
            {quoteLoading ? <Spinner size="sm" /> : '📋'} {t('finance.get_quote', 'Get Quote')}
          </button>
          <p className="text-[11px] text-text-secondary">
            {t('finance.region_note', 'Region risk also drives the payout simulator below.')}
          </p>
        </div>

        {quoteError && <div className="mt-3"><ErrorBox message={quoteError} /></div>}

        {quote && !quoteLoading && (
          <div className="mt-3 space-y-3">
            <div className="card-elevated border-l-4 border-primary">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className="font-semibold text-primary">{t('finance.quote_summary', 'Quote Summary')}</h3>
                <RiskBadge risk={quote.details?.crop_risk_class} />
              </div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="bg-bg rounded-card p-3">
                  <p className="text-xs text-text-secondary">Sum Insured · সর্বমোট বীমা</p>
                  <p className="text-lg font-bold text-text-primary">৳ {fmt(quote.details?.sum_insured)}</p>
                </div>
                <div className="bg-bg rounded-card p-3">
                  <p className="text-xs text-text-secondary">Premium · প্রিমিয়াম</p>
                  <p className="text-lg font-bold text-primary">৳ {fmt(quote.details?.premium)}</p>
                  <p className="text-[11px] text-text-secondary">
                    rate {((quote.details?.premium_rate ?? 0) * 100).toFixed(2)}%
                  </p>
                </div>
              </div>

              {/* Explainable premium drivers */}
              <div className="mt-4">
                <p className="text-xs font-semibold text-text-secondary mb-2">
                  {t('finance.premium_drivers', 'Why this premium? (premium drivers)')}
                </p>
                <ul className="space-y-1.5 text-sm">
                  <li className="flex items-center justify-between">
                    <span className="text-text-secondary">Crop risk class</span>
                    <RiskBadge risk={quote.details?.premium_drivers?.crop_risk_class} />
                  </li>
                  <li className="flex items-center justify-between">
                    <span className="text-text-secondary">Region multiplier</span>
                    <span className="font-semibold text-text-primary">× {quote.details?.premium_drivers?.region_multiplier ?? '—'}</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span className="text-text-secondary">Loss multiplier</span>
                    <span className="font-semibold text-text-primary">× {quote.details?.premium_drivers?.loss_multiplier ?? '—'}</span>
                  </li>
                </ul>
                <p className="text-[11px] text-text-secondary mt-2">
                  Base rate 4% × crop risk × region × loss multipliers.
                </p>
              </div>

              {/* Triggers */}
              {Array.isArray(quote.details?.triggers) && quote.details.triggers.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-text-secondary mb-2">
                    {t('finance.triggers', 'Payout Triggers')}
                  </p>
                  <ul className="space-y-1.5">
                    {quote.details.triggers.map((tg, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-text-primary">
                        <span className="text-danger mt-0.5">⚠</span>
                        <span>{tg}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Narrative from agent (Bengali/English) */}
              {quote.quote && (
                <div className="mt-4 pt-4 border-t border-border text-sm text-text-primary leading-relaxed">
                  <ReactMarkdown>{quote.quote}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Payout Simulator ── */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary mb-2 px-1">
          🧮 {t('finance.simulator', 'Payout Simulator')}
        </h2>
        <div className="card-elevated space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <select value={scenario} onChange={(e) => setScenario(e.target.value)} className="input-field !py-2.5">
              {SCENARIOS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <select value={regionRisk} onChange={(e) => setRegionRisk(e.target.value)} className="input-field !py-2.5">
              {REGION_RISKS.map((r) => <option key={r} value={r}>Region: {r}</option>)}
            </select>
          </div>
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-text-secondary font-medium">Severity · তীব্রতা</span>
              <span className="text-text-primary font-semibold">{Math.round(severity * 100)}%</span>
            </div>
            <input
              type="range" min="0" max="1" step="0.05" value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full accent-primary"
            />
          </div>
          <button onClick={fetchPayout} disabled={payoutLoading} className="btn-primary w-full flex items-center justify-center gap-2">
            {payoutLoading ? <Spinner size="sm" /> : '🔎'} {t('finance.simulate', 'Simulate Payout')}
          </button>
        </div>

        {payoutError && <div className="mt-3"><ErrorBox message={payoutError} /></div>}

        {payout && !payoutLoading && (
          <div className="mt-3 card-elevated bg-bg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-text-primary capitalize">
                {payout.scenario} · {Math.round((payout.severity ?? 0) * 100)}% severity
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-card p-3 bg-surface">
                <p className="text-xs text-text-secondary">Est. Payout · অনুমানিত</p>
                <p className="text-xl font-bold text-primary">৳ {fmt(payout.estimated_payout)}</p>
              </div>
              <div className="rounded-card p-3 bg-surface">
                <p className="text-xs text-text-secondary">Net after premium · নিট</p>
                <p className={`text-xl font-bold ${(payout.net_after_premium ?? 0) >= 0 ? 'text-primary' : 'text-danger'}`}>
                  ৳ {fmt(payout.net_after_premium)}
                </p>
              </div>
            </div>
            <p className="text-[11px] text-text-secondary mt-2">
              Sum insured ৳ {fmt(payout.sum_insured)} · payout capped at sum insured.
            </p>
          </div>
        )}
      </section>

      {/* ── Subsidies ── */}
      <section>
        <h2 className="text-sm font-semibold text-text-secondary mb-2 px-1">
          🏛️ {t('finance.subsidies', 'Eligible Schemes')}
        </h2>
        <div className="card-elevated space-y-3">
          <p className="text-xs text-text-secondary">
            {t('finance.subsidy_note', 'Find government subsidies & schemes for your crop and land size.')}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <select value={crop} onChange={(e) => setCrop(e.target.value)} className="input-field !py-2.5">
              {CROPS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input
              type="number" min="0" value={landSize}
              onChange={(e) => setLandSize(e.target.value)}
              placeholder="Land (decimal)" className="input-field !py-2.5"
            />
          </div>
          <button onClick={fetchSubsidies} disabled={subLoading} className="btn-outline w-full flex items-center justify-center gap-2">
            {subLoading ? <Spinner size="sm" /> : '🔍'} {t('finance.check_schemes', 'Check Schemes')}
          </button>
        </div>

        {subError && <div className="mt-3"><ErrorBox message={subError} /></div>}

        {subsidies && !subLoading && (
          <div className="mt-3 space-y-3">
            {Array.isArray(subsidies.subsidies) && subsidies.subsidies.length > 0 ? (
              subsidies.subsidies.map((s) => (
                <div key={s.id} className="card-elevated border-l-4 border-accent">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-text-primary">{s.name_en}</h3>
                      <p className="text-sm text-text-secondary">{s.name_bn}</p>
                    </div>
                    <span className="badge bg-accent-light/30 text-soil shrink-0">{s.category}</span>
                  </div>
                  {s.description_bn && (
                    <p className="text-sm text-text-primary mt-2 leading-relaxed">{s.description_bn}</p>
                  )}
                  <div className="mt-2 text-[11px] text-text-secondary">
                    {Array.isArray(s.eligibility_criteria?.crops)
                      ? `Crops: ${s.eligibility_criteria.crops.join(', ')}`
                      : null}
                    {typeof s.eligibility_criteria?.min_land === 'number'
                      ? ` · Min land: ${s.eligibility_criteria.min_land} decimal`
                      : ''}
                  </div>
                  {s.how_to_apply_bn && (
                    <p className="text-xs text-text-secondary mt-2 whitespace-pre-wrap">
                      <span className="font-semibold">আবেদন:</span> {s.how_to_apply_bn}
                    </p>
                  )}
                  {s.apply_link && (
                    <a
                      href={s.apply_link} target="_blank" rel="noreferrer"
                      className="inline-block mt-2 text-sm text-primary font-medium hover:underline"
                    >
                      {t('finance.apply_link', 'Official link')} ↗
                    </a>
                  )}
                </div>
              ))
            ) : (
              <EmptyState icon="🏛️" title={t('finance.no_schemes', 'No schemes found')}
                message={t('finance.no_schemes_msg', 'Try a different crop or larger land size.')} />
            )}
          </div>
        )}
      </section>
    </div>
  );
}
