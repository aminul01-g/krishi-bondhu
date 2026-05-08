import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getDealers, postScanProduct } from '../services/api';
import { useApi } from '../hooks/useApi';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';

export default function MarketplacePage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const { data: dealers, loading } = useApi((s) => getDealers(lat, lon, s), [lat, lon]);
  const [scanMode, setScanMode] = useState(false);
  const [barcode, setBarcode] = useState('');
  const [scanResult, setScanResult] = useState(null);
  const [scanning, setScanning] = useState(false);

  const handleScan = async () => {
    if (!barcode.trim()) return;
    setScanning(true);
    try {
      const res = await postScanProduct({ barcode: barcode.trim(), lat, lon });
      setScanResult(res);
    } catch { /* handled */ }
    finally { setScanning(false); }
  };

  return (
    <div className="space-y-4">
      {/* Scan toggle */}
      <div className="flex gap-2">
        <button onClick={() => setScanMode(false)}
          className={`flex-1 py-2 rounded-btn text-sm font-medium transition-all
            ${!scanMode ? 'bg-primary text-white' : 'bg-surface border border-border text-text-secondary'}`}>
          🏪 Dealers
        </button>
        <button onClick={() => setScanMode(true)}
          className={`flex-1 py-2 rounded-btn text-sm font-medium transition-all
            ${scanMode ? 'bg-primary text-white' : 'bg-surface border border-border text-text-secondary'}`}>
          🔍 Verify Product
        </button>
      </div>

      {scanMode ? (
        <div className="card-elevated space-y-3">
          <input value={barcode} onChange={(e) => setBarcode(e.target.value)}
            placeholder="Enter barcode or product ID..." className="input-field" />
          <button onClick={handleScan} disabled={scanning || !barcode.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {scanning ? <Spinner size="sm" /> : '🔎'} Verify
          </button>
          {scanResult && (
            <div className="bg-bg rounded-btn p-3 space-y-2">
              <p className="text-sm font-medium">{scanResult.ai_verdict ? '✅' : '⚠️'} Verdict</p>
              <p className="text-sm text-text-primary whitespace-pre-wrap">{scanResult.ai_verdict || 'Unknown'}</p>
            </div>
          )}
        </div>
      ) : (
        <>
          {loading ? (
            <div className="space-y-3">{[1,2,3].map((i) => <div key={i} className="card"><Skeleton lines={2} /></div>)}</div>
          ) : (Array.isArray(dealers) && dealers.length > 0) ? (
            <div className="space-y-3">
              {dealers.map((d, i) => (
                <div key={d.id || i} className="card hover:shadow-elevated transition-shadow">
                  <h4 className="font-semibold text-text-primary">{d.name}</h4>
                  <p className="text-sm text-text-secondary">📞 {d.phone_number}</p>
                  {d.regions_served?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {d.regions_served.map((r) => <span key={r} className="badge-success">{r}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon="🏪" title={t('nav.marketplace')} message="No dealers found nearby" />
          )}
        </>
      )}
    </div>
  );
}
