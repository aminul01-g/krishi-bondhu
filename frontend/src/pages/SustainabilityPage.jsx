import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import {
  getSustainabilityScore,
  getCarbonFootprint,
  getSustainabilityOpportunities,
} from '../services/api';
import { useApi } from '../hooks/useApi';
import { Skeleton, EmptyState } from '../components/shared/LoadingStates';

/* ─── Helpers ──────────────────────────────────────────────────── */

const GRADE_STYLE = {
  A: { ring: '#16a34a', badge: 'bg-emerald-100 text-emerald-700', label: 'Excellent' },
  B: { ring: '#d97706', badge: 'bg-amber-100 text-amber-700', label: 'Good progress' },
  C: { ring: '#ea580c', badge: 'bg-orange-100 text-orange-700', label: 'Getting started' },
};

const fmt = (n, digits = 1) =>
  typeof n === 'number' && !Number.isNaN(n) ? n.toFixed(digits) : '—';

function SectionError({ message }) {
  return (
    <div className="card border border-danger-light bg-danger-light/40">
      <p className="text-sm text-danger">{message || 'Something went wrong.'}</p>
    </div>
  );
}

/* ─── Score gauge ──────────────────────────────────────────────── */

function ScoreGauge({ score, grade }) {
  const style = GRADE_STYLE[grade] || GRADE_STYLE.C;
  const maxScore = 100;
  const pct = Math.min((score / maxScore) * 100, 100);
  return (
    <div className="relative w-32 h-32 mx-auto mb-3">
      <svg viewBox="0 0 36 36" className="w-full h-full">
        <path d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none" stroke="#E5E2DB" strokeWidth="3" />
        <path d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none" stroke={style.ring} strokeWidth="3"
          strokeDasharray={`${pct}, 100`}
          className="transition-all duration-1000" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-primary">{fmt(score, 1)}</span>
        <span className={`text-xs font-bold ${style.badge.replace('bg-', 'text-').split(' ')[0]}`}>
          {grade}
        </span>
      </div>
    </div>
  );
}

/* ─── Emissions vs offsets bar list ────────────────────────────── */

function EmissionsOffsetsBars({ emissionBreakdown, sequestrationBreakdown }) {
  const rows = [
    ...(emissionBreakdown || []).map((e) => ({
      key: `e-${e.type}`,
      label: e.type,
      value: e.emission_kg,
      color: '#dc2626',
    })),
    ...(sequestrationBreakdown || []).map((s) => ({
      key: `s-${s.practice}`,
      label: s.practice,
      value: s.co2_offset_kg,
      color: '#16a34a',
    })),
  ];

  if (rows.length === 0) {
    return (
      <p className="text-xs text-text-secondary">
        No emission or sequestration entries detected yet. Add inputs and
        sustainable practices to your farm diary to populate this view.
      </p>
    );
  }

  const maxVal = Math.max(...rows.map((r) => Math.abs(r.value)), 0.0001);

  return (
    <div className="breakdown-bars mt-2">
      {rows.map((r, i) => {
        const pct = Math.max(2, Math.round((Math.abs(r.value) / maxVal) * 100));
        return (
          <div key={r.key} className="breakdown-row">
            <div className="breakdown-label">
              <span>{r.color === '#dc2626' ? '🔥' : '🌱'}</span>
              <span className="capitalize">{r.label.replace(/_/g, ' ')}</span>
            </div>
            <div className="breakdown-bar-track">
              <div
                className="breakdown-bar-fill"
                style={{
                  width: `${pct}%`,
                  '--bar-color': r.color,
                  animationDelay: `${i * 0.12}s`,
                }}
              />
            </div>
            <span className="breakdown-amount">{fmt(r.value, 1)} kg</span>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Page ─────────────────────────────────────────────────────── */

export default function SustainabilityPage() {
  const { t } = useTranslation();
  const {
    data: scorecard,
    loading: scoreLoading,
    error: scoreError,
  } = useApi((s) => getSustainabilityScore(s), []);
  const {
    data: footprint,
    loading: fpLoading,
    error: fpError,
  } = useApi((s) => getCarbonFootprint(s), []);
  const {
    data: opps,
    loading: oppsLoading,
    error: oppsError,
  } = useApi((s) => getSustainabilityOpportunities(s), []);

  const opportunities = Array.isArray(opps) ? opps : [];
  const grade = scorecard?.grade && GRADE_STYLE[scorecard.grade] ? scorecard.grade : 'C';
  const style = GRADE_STYLE[grade];
  const net = scorecard?.net_kg;
  const hasNet = typeof net === 'number';

  return (
    <div className="space-y-4">
      {/* ── Scorecard header ── */}
      <h3 className="font-semibold text-text-primary text-lg">🌿 {t('nav.sustainability')}</h3>

      {scoreError ? (
        <SectionError message={scoreError} />
      ) : scoreLoading ? (
        <div className="card-elevated"><Skeleton lines={4} /></div>
      ) : (
        <div className="card-elevated text-center">
          <ScoreGauge score={scorecard?.score ?? 0} grade={grade} />

          <span className={`badge ${style.badge}`}>
            Grade {grade} · {style.label}
          </span>

          {/* Net + emissions vs offsets summary */}
          <div className="grid grid-cols-3 gap-2 mt-4">
            <div className="bg-bg rounded-btn p-2">
              <p className="text-[10px] text-text-secondary uppercase tracking-wide">Net CO₂</p>
              <p className={`text-sm font-bold ${hasNet && net >= 0 ? 'text-primary' : 'text-danger'}`}>
                {hasNet ? `${net >= 0 ? '+' : ''}${fmt(net)}` : '—'} kg
              </p>
            </div>
            <div className="bg-bg rounded-btn p-2">
              <p className="text-[10px] text-text-secondary uppercase tracking-wide">Emissions</p>
              <p className="text-sm font-bold text-danger">
                {fmt(scorecard?.total_emissions_kg ?? footprint?.total_emissions_kg)} kg
              </p>
            </div>
            <div className="bg-bg rounded-btn p-2">
              <p className="text-[10px] text-text-secondary uppercase tracking-wide">Offsets</p>
              <p className="text-sm font-bold text-primary">{fmt(scorecard?.co2_offset_kg)} kg</p>
            </div>
          </div>
          <p className="text-[11px] text-text-secondary mt-2">
            {hasNet && net >= 0
              ? 'Your farm is a net carbon sink this period. 🌍'
              : 'Your farm is a net emitter this period — offsets can help close the gap.'}
          </p>
        </div>
      )}

      {/* ── Emissions vs offsets breakdown ── */}
      <div className="card">
        <h4 className="font-semibold text-text-primary text-sm mb-1">
          🔥 Emissions vs 🌱 Offsets
        </h4>
        {fpError && !scorecard ? null : (
          scoreLoading || fpLoading ? (
            <Skeleton lines={3} />
          ) : (
            <EmissionsOffsetsBars
              emissionBreakdown={scorecard?.emission_breakdown || footprint?.breakdown || []}
              sequestrationBreakdown={scorecard?.sequestration_breakdown || []}
            />
          )
        )}
        {fpError && (
          <p className="text-xs text-danger mt-2">Carbon footprint unavailable: {fpError}</p>
        )}
        {footprint?.unparsed_cost_entries > 0 && (
          <p className="text-[11px] text-text-secondary mt-2">
            ⚠️ {footprint.unparsed_cost_entries} diary cost entr
            {footprint.unparsed_cost_entries === 1 ? 'y' : 'ies'} could not be converted to
            quantities, so their emissions are not counted (estimates only).
          </p>
        )}
      </div>

      {/* ── Verified practices ── */}
      {!scoreLoading && scorecard?.verified_practices?.length > 0 && (
        <div className="card">
          <h4 className="font-semibold text-text-primary text-sm mb-2">✅ Verified Practices</h4>
          <div className="flex flex-wrap gap-2">
            {scorecard.verified_practices.map((p, i) => (
              <span key={i} className="badge-success">{p.replace(/_/g, ' ')}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── Score components (explainability) ── */}
      {!scoreLoading && scorecard?.components && (
        <div className="card">
          <h4 className="font-semibold text-text-primary text-sm mb-2">🧮 How your score is built</h4>
          <div className="space-y-1 text-xs text-text-secondary">
            <p>Base score: <strong className="text-text-primary">{fmt(scorecard.components.base_score, 0)}</strong></p>
            <p>Practice bonus: <strong className="text-primary">+{fmt(scorecard.components.practice_bonus)}</strong></p>
            <p>Emission penalty: <strong className="text-danger">−{fmt(scorecard.components.emission_penalty)}</strong></p>
          </div>
        </div>
      )}

      {/* ── Recommendation ── */}
      {!scoreLoading && scorecard?.recommendation && (
        <div className="card-elevated bg-primary/5">
          <h4 className="font-semibold text-text-primary text-sm mb-1">💡 Recommendation</h4>
          <div className="prose prose-sm max-w-none text-sm leading-relaxed text-text-primary">
            <ReactMarkdown>{scorecard.recommendation}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* ── Carbon market opportunities ── */}
      <h3 className="font-semibold text-text-primary text-lg">🌍 Carbon Market Opportunities</h3>
      {oppsError ? (
        <SectionError message={oppsError} />
      ) : oppsLoading ? (
        <div className="card"><Skeleton lines={3} /></div>
      ) : opportunities.length > 0 ? (
        <div className="space-y-3">
          {opportunities.map((o, i) => (
            <div key={i} className="card hover:shadow-elevated transition-shadow">
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-semibold text-text-primary text-sm">{o.name}</h4>
                <span className="badge bg-bg text-text-secondary shrink-0">{o.type}</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">{o.benefit}</p>
              <div className="mt-2 flex items-center gap-2">
                {o.eligible ? (
                  <span className="badge-success">✅ Eligible</span>
                ) : (
                  <span className="badge bg-bg text-text-secondary">⏳ Not yet eligible</span>
                )}
              </div>
              {o.rationale && (
                <p className="text-[11px] text-text-secondary mt-2 italic">{o.rationale}</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon="🌍" title="Carbon Markets" message="Keep improving your score to unlock opportunities" />
      )}

      {/* ── Provenance disclaimer ── */}
      <p className="text-[11px] text-text-secondary leading-relaxed border-t border-border pt-3">
        📋 These figures are <strong>estimates</strong> derived from your farm diary using
        IPCC Tier-1 emission factors and rule-based practice detection — they are not
        certified measurements. Use them as guidance, not for formal carbon accounting.
      </p>
    </div>
  );
}
