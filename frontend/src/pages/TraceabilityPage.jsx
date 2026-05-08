import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postHarvestBatch, getHarvestBatch } from '../services/api';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

export default function TraceabilityPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState('register');
  const [crop, setCrop] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('kg');
  const [submitting, setSubmitting] = useState(false);
  const [batch, setBatch] = useState(null);
  const [lookupId, setLookupId] = useState('');
  const [lookupResult, setLookupResult] = useState(null);

  const handleRegister = async () => {
    if (!crop || !quantity) return;
    setSubmitting(true);
    try {
      const res = await postHarvestBatch({ crop, quantity: parseFloat(quantity), unit });
      setBatch(res);
    } catch { /* handled */ }
    finally { setSubmitting(false); }
  };

  const handleLookup = async () => {
    if (!lookupId.trim()) return;
    setSubmitting(true);
    try { setLookupResult(await getHarvestBatch(lookupId.trim())); }
    catch { setLookupResult(null); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {[['register', '📝 Register'], ['lookup', '🔍 Lookup']].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`flex-1 py-2 rounded-btn text-sm font-medium transition-all
              ${tab === k ? 'bg-primary text-white' : 'bg-surface border border-border text-text-secondary'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'register' ? (
        <div className="card-elevated space-y-3">
          <input value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="Crop name" className="input-field" />
          <div className="flex gap-2">
            <input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="Quantity" type="number" className="input-field flex-1" />
            <select value={unit} onChange={(e) => setUnit(e.target.value)} className="input-field w-24">
              <option value="kg">kg</option><option value="mon">মণ</option><option value="ton">ton</option>
            </select>
          </div>
          <button onClick={handleRegister} disabled={submitting || !crop}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {submitting && <Spinner size="sm" />} Register Batch
          </button>
          {batch && (
            <div className="bg-bg rounded-btn p-4 text-center space-y-2">
              <p className="text-sm font-medium text-primary">✅ Batch Registered</p>
              <p className="text-xs text-text-secondary break-all">Hash: {batch.current_hash}</p>
              <div className="inline-block bg-white p-3 rounded-btn shadow-card">
                <p className="text-xs text-text-secondary">QR: {batch.id}</p>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card-elevated space-y-3">
          <input value={lookupId} onChange={(e) => setLookupId(e.target.value)} placeholder="Enter Batch ID" className="input-field" />
          <button onClick={handleLookup} disabled={submitting || !lookupId.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {submitting && <Spinner size="sm" />} Lookup
          </button>
          {lookupResult && (
            <div className="bg-bg rounded-btn p-3 space-y-1 text-sm">
              <p><strong>Crop:</strong> {lookupResult.crop}</p>
              <p><strong>Qty:</strong> {lookupResult.quantity} {lookupResult.unit}</p>
              <p><strong>Status:</strong> {lookupResult.certification_status}</p>
              <p className="text-xs text-text-secondary break-all">Hash: {lookupResult.current_hash}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
