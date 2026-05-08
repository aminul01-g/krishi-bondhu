import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postSubsidySchemes, getCreditReport, postInsuranceQuote } from '../services/api';
import { useApi } from '../hooks/useApi';
import { Spinner, Skeleton } from '../components/shared/LoadingStates';

export default function FinancePage() {
  const { t } = useTranslation();
  const { data: credit, loading: creditLoading } = useApi((s) => getCreditReport(s), []);
  const [tab, setTab] = useState('subsidy');
  const [subsidyResult, setSubsidyResult] = useState(null);
  const [insuranceResult, setInsuranceResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [crop, setCrop] = useState('Rice');
  const [landSize, setLandSize] = useState('100');

  const fetchSubsidy = async () => {
    setLoading(true);
    try { setSubsidyResult(await postSubsidySchemes(crop, parseFloat(landSize))); }
    catch { /* handled */ } finally { setLoading(false); }
  };

  const fetchInsurance = async () => {
    setLoading(true);
    try { setInsuranceResult(await postInsuranceQuote(crop, parseFloat(landSize))); }
    catch { /* handled */ } finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      {/* Credit score */}
      {creditLoading ? <div className="card"><Skeleton lines={2} /></div> : credit && (
        <div className="card-elevated text-center">
          <p className="text-xs text-text-secondary mb-1">Credit Readiness Score</p>
          <p className="text-4xl font-bold text-primary">{credit.credit_score}</p>
          <p className="text-sm text-text-secondary mt-1">{credit.recommendation}</p>
        </div>
      )}

      {/* Tab selector */}
      <div className="flex gap-2">
        {[['subsidy', '🏛️ Subsidies'], ['insurance', '🛡️ Insurance']].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`flex-1 py-2 rounded-btn text-sm font-medium transition-all
              ${tab === k ? 'bg-primary text-white' : 'bg-surface text-text-secondary border border-border'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* Input fields */}
      <div className="card flex gap-2">
        <input value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="Crop" className="input-field flex-1 !py-2" />
        <input value={landSize} onChange={(e) => setLandSize(e.target.value)} placeholder="Land (decimal)" type="number" className="input-field w-28 !py-2" />
        <button onClick={tab === 'subsidy' ? fetchSubsidy : fetchInsurance} disabled={loading}
          className="btn-primary !py-2 !px-4 flex items-center gap-1">
          {loading ? <Spinner size="sm" /> : '→'}
        </button>
      </div>

      {/* Results */}
      {(tab === 'subsidy' && subsidyResult) && (
        <div className="card-elevated"><p className="text-sm whitespace-pre-wrap">{subsidyResult.advice}</p></div>
      )}
      {(tab === 'insurance' && insuranceResult) && (
        <div className="card-elevated"><p className="text-sm whitespace-pre-wrap">{insuranceResult.quote}</p></div>
      )}
    </div>
  );
}
