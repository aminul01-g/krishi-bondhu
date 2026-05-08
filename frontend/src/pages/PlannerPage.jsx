import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postGeneratePlan, getMyPlans, getYieldForecast } from '../services/api';
import { useApi } from '../hooks/useApi';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';

export default function PlannerPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const { data: plans, loading: plansLoading, refetch } = useApi((s) => getMyPlans(s), []);
  const [crop, setCrop] = useState('Rice');
  const [generating, setGenerating] = useState(false);
  const [newPlan, setNewPlan] = useState(null);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await postGeneratePlan(crop, lat || 23.81, lon || 90.41);
      setNewPlan(res);
      refetch();
    } catch { /* handled */ }
    finally { setGenerating(false); }
  };

  return (
    <div className="space-y-4">
      {/* Generate plan */}
      <div className="card-elevated">
        <h3 className="font-semibold text-primary mb-3">📋 {t('nav.planner')}</h3>
        <div className="flex gap-2">
          <select value={crop} onChange={(e) => setCrop(e.target.value)} className="input-field flex-1 !py-2">
            {['Rice', 'Wheat', 'Potato', 'Maize', 'Jute', 'Onion', 'Tomato'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button onClick={handleGenerate} disabled={generating}
            className="btn-primary !py-2 flex items-center gap-1">
            {generating ? <Spinner size="sm" /> : '🚀'} Generate
          </button>
        </div>
      </div>

      {/* New plan result */}
      {newPlan && (
        <div className="card-elevated border-l-4 border-accent">
          <h4 className="font-semibold text-accent mb-2">✨ New Plan Generated</h4>
          <p className="text-sm text-text-primary whitespace-pre-wrap">{newPlan.ai_strategy}</p>
        </div>
      )}

      {/* Existing plans */}
      <h3 className="font-semibold text-text-primary">📚 My Plans</h3>
      {plansLoading ? (
        <div className="space-y-3">{[1,2].map((i) => <div key={i} className="card"><Skeleton lines={2} /></div>)}</div>
      ) : (Array.isArray(plans) && plans.length > 0) ? (
        <div className="space-y-3">
          {plans.map((p) => (
            <div key={p.id} className="card hover:shadow-elevated transition-shadow">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-text-primary">{p.crop}</span>
                <span className="badge-success">{p.status || 'active'}</span>
              </div>
              {p.predicted_yield && (
                <p className="text-sm text-text-secondary">Yield: {p.predicted_yield} | Confidence: {p.confidence}</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon="📋" title="No Plans Yet" message="Generate your first seasonal plan" />
      )}
    </div>
  );
}
