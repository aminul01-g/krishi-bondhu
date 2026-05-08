import { useTranslation } from 'react-i18next';
import { getSustainabilityScore, getSustainabilityOpportunities } from '../services/api';
import { useApi } from '../hooks/useApi';
import { Skeleton, EmptyState } from '../components/shared/LoadingStates';

export default function SustainabilityPage() {
  const { t } = useTranslation();
  const { data: scorecard, loading: scoreLoading } = useApi((s) => getSustainabilityScore(s), []);
  const { data: opps, loading: oppsLoading } = useApi((s) => getSustainabilityOpportunities(s), []);

  const score = scorecard?.data?.score || 0;
  const maxScore = 100;
  const pct = Math.min((score / maxScore) * 100, 100);

  return (
    <div className="space-y-4">
      {/* Score gauge */}
      {scoreLoading ? (
        <div className="card-elevated"><Skeleton lines={3} /></div>
      ) : (
        <div className="card-elevated text-center">
          <h3 className="font-semibold text-primary mb-4">🌿 {t('nav.sustainability')}</h3>
          <div className="relative w-32 h-32 mx-auto mb-4">
            <svg viewBox="0 0 36 36" className="w-full h-full">
              <path d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none" stroke="#E5E2DB" strokeWidth="3" />
              <path d="M18 2.0845a 15.9155 15.9155 0 0 1 0 31.831a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none" stroke="#2D6A4F" strokeWidth="3"
                strokeDasharray={`${pct}, 100`}
                className="transition-all duration-1000" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-primary">{score}</span>
            </div>
          </div>
          <p className="text-sm text-text-secondary">
            {score >= 70 ? '🌟 Excellent!' : score >= 40 ? '👍 Good progress' : '🌱 Getting started'}
          </p>

          {/* Practices */}
          {scorecard?.data?.practices && (
            <div className="flex flex-wrap justify-center gap-2 mt-4">
              {scorecard.data.practices.map((p, i) => (
                <span key={i} className="badge-success">{p.verified ? '✅' : '⬜'} {p.name}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Carbon market */}
      <h3 className="font-semibold text-text-primary">🌍 Carbon Market Opportunities</h3>
      {oppsLoading ? (
        <div className="card"><Skeleton lines={2} /></div>
      ) : opps?.opportunities?.length > 0 ? (
        <div className="space-y-3">
          {opps.opportunities.map((o, i) => (
            <div key={i} className="card hover:shadow-elevated transition-shadow">
              <h4 className="font-semibold text-text-primary text-sm">{o.name || o.program}</h4>
              <p className="text-xs text-text-secondary mt-1">{o.description || o.details}</p>
              {o.potential_earning && (
                <span className="badge-warning mt-2">💰 {o.potential_earning}</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon="🌍" title="Carbon Markets" message="Keep improving your score to unlock opportunities" />
      )}
    </div>
  );
}
