import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postHarvestBatch, getBatchIntegrity, verifyBatch } from '../services/api';
import { Spinner } from '../components/shared/LoadingStates';

/* ─── Helpers ──────────────────────────────────────────────────── */

// A QR value can be (a) a generated image path/URL, or (b) a verifiable
// trace URL string when image generation is unavailable.
function isQrImage(url) {
  return (
    typeof url === 'string' &&
    (/^\/?static\//.test(url) || /\.(png|jpe?g|gif|svg|webp)$/i.test(url))
  );
}

function copyText(text) {
  if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
}

/* ─── Page ─────────────────────────────────────────────────────── */

export default function TraceabilityPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState('register');

  // --- Register form state ---
  const [crop, setCrop] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('kg');
  const [inputText, setInputText] = useState('');
  const [inputs, setInputs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [registerError, setRegisterError] = useState(null);
  const [batch, setBatch] = useState(null);

  // --- Integrity verification (farmer side) ---
  const [verifying, setVerifying] = useState(false);
  const [integrity, setIntegrity] = useState(null);

  // --- Public scan verify (consumer side) ---
  const [scan, setScan] = useState({ batch: '', h: '', t: '' });
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState(null);

  const addInput = () => {
    const v = inputText.trim();
    if (!v) return;
    setInputs((prev) => (prev.includes(v) ? prev : [...prev, v]));
    setInputText('');
  };
  const removeInput = (v) => setInputs((prev) => prev.filter((x) => x !== v));

  const handleRegister = async () => {
    if (!crop || !quantity) return;
    setSubmitting(true);
    setRegisterError(null);
    setIntegrity(null);
    try {
      const res = await postHarvestBatch({
        crop,
        quantity: parseFloat(quantity),
        inputs,
        unit,
      });
      setBatch(res);
      // Pre-fill the consumer scan box for convenience.
      setScan({
        batch: res.batch_id,
        h: res.current_hash,
        t: res.trace_token,
      });
    } catch (e) {
      setRegisterError(e.message || 'Failed to register batch.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyIntegrity = async () => {
    if (!batch?.batch_id) return;
    setVerifying(true);
    setIntegrity(null);
    try {
      setIntegrity(await getBatchIntegrity(batch.batch_id));
    } catch (e) {
      setIntegrity({ verified: false, error: e.message || 'Verification failed.' });
    } finally {
      setVerifying(false);
    }
  };

  const handleScanVerify = async () => {
    const { batch: b, h, t } = scan;
    if (!b.trim() || !h.trim() || !t.trim()) return;
    setScanning(true);
    setScanError(null);
    setScanResult(null);
    try {
      setScanResult(await verifyBatch(b.trim(), h.trim(), t.trim()));
    } catch (e) {
      setScanError(e.message || 'Verification failed.');
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-text-primary text-lg">🔗 {t('nav.traceability')}</h3>

      {/* Tab selector */}
      <div className="flex gap-2">
        {[['register', '📝 Register Batch'], ['verify', '🔍 Public Verify']].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`flex-1 py-2 rounded-btn text-sm font-medium transition-all
              ${tab === k ? 'bg-primary text-white' : 'bg-surface border border-border text-text-secondary'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* ════════ FARMER: REGISTER ════════ */}
      {tab === 'register' ? (
        <div className="card-elevated space-y-3">
          <input value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="Crop name (e.g. Rice)" className="input-field" />
          <div className="flex gap-2">
            <input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="Quantity" type="number" className="input-field flex-1" />
            <select value={unit} onChange={(e) => setUnit(e.target.value)} className="input-field w-24">
              <option value="kg">kg</option>
              <option value="mon">মণ</option>
              <option value="ton">ton</option>
            </select>
          </div>

          {/* Inputs list */}
          <div>
            <div className="flex gap-2">
              <input value={inputText} onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addInput())}
                placeholder="Add an input used (e.g. urea, compost)" className="input-field flex-1" />
              <button onClick={addInput} type="button" className="btn-outline !px-4 !py-2">+ Add</button>
            </div>
            {inputs.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {inputs.map((v) => (
                  <span key={v} className="badge-success cursor-pointer" onClick={() => removeInput(v)}>
                    {v} ✕
                  </span>
                ))}
              </div>
            )}
          </div>

          <button onClick={handleRegister} disabled={submitting || !crop || !quantity}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {submitting && <Spinner size="sm" />} Register Harvest Batch
          </button>

          {registerError && (
            <p className="text-xs text-danger">{registerError}</p>
          )}

          {/* Success result */}
          {batch && (
            <div className="bg-bg rounded-btn p-4 space-y-3 text-center">
              <p className="text-sm font-medium text-primary">✅ Batch Registered</p>

              {/* QR */}
              <div className="inline-block bg-white p-3 rounded-btn shadow-card">
                {batch.qr_url && isQrImage(batch.qr_url) ? (
                  <img src={batch.qr_url} alt="Batch QR code"
                    className="w-40 h-40 object-contain" />
                ) : batch.qr_url ? (
                  <a href={batch.qr_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-primary underline break-all block max-w-[200px]">
                    {batch.qr_url}
                  </a>
                ) : (
                  <p className="text-xs text-text-secondary">QR not available</p>
                )}
                <p className="text-[10px] text-text-secondary mt-1">Scan to verify</p>
              </div>

              {/* Verify URL */}
              {batch.verify_url && (
                <div className="text-left">
                  <p className="text-[11px] text-text-secondary mb-1">Public verify link:</p>
                  <a href={batch.verify_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-primary underline break-all block">
                    {batch.verify_url}
                  </a>
                </div>
              )}

              {/* Hash */}
              <div className="text-left">
                <p className="text-[11px] text-text-secondary mb-1">Current hash (tamper-evidence):</p>
                <p className="text-xs font-mono text-text-primary break-all bg-surface rounded-btn p-2">
                  {batch.current_hash}
                </p>
                {batch.prev_hash && (
                  <p className="text-[10px] text-text-secondary mt-1 break-all">
                    Previous: {batch.prev_hash}
                  </p>
                )}
              </div>

              {/* Integrity verify */}
              <button onClick={handleVerifyIntegrity} disabled={verifying}
                className="btn-outline w-full flex items-center justify-center gap-2 !py-2">
                {verifying && <Spinner size="sm" />} Verify Integrity
              </button>
              {integrity && (
                integrity.verified ? (
                  <div className="bg-primary/10 text-primary rounded-btn p-3">
                    <p className="text-sm font-semibold">🛡️ Verified — chain intact</p>
                    <p className="text-[11px] mt-1">Hash matches stored record. No tampering detected.</p>
                  </div>
                ) : (
                  <div className="bg-danger-light/40 text-danger rounded-btn p-3">
                    <p className="text-sm font-semibold">⚠️ Tampered</p>
                    <p className="text-[11px] mt-1">{integrity.error || 'Hash mismatch — data may have been altered.'}</p>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      ) : (
        /* ════════ CONSUMER: PUBLIC VERIFY ════════ */
        <div className="card-elevated space-y-3">
          <p className="text-xs text-text-secondary">
            Paste the <strong>batch</strong>, <strong>hash (h)</strong>, and <strong>token (t)</strong>{' '}
            from a scanned QR to confirm it is genuine. This check is public and needs no login.
          </p>

          <input value={scan.batch} onChange={(e) => setScan((s) => ({ ...s, batch: e.target.value }))}
            placeholder="Batch ID" className="input-field font-mono text-xs" />
          <input value={scan.h} onChange={(e) => setScan((s) => ({ ...s, h: e.target.value }))}
            placeholder="Hash (h)" className="input-field font-mono text-xs" />
          <input value={scan.t} onChange={(e) => setScan((s) => ({ ...s, t: e.target.value }))}
            placeholder="Token (t)" className="input-field font-mono text-xs" />

          <button onClick={handleScanVerify}
            disabled={scanning || !scan.batch.trim() || !scan.h.trim() || !scan.t.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {scanning && <Spinner size="sm" />} Verify Scan
          </button>

          {scanError && <p className="text-xs text-danger">{scanError}</p>}

          {scanResult && (
            scanResult.valid ? (
              <div className="bg-primary/10 text-primary rounded-btn p-4 text-center">
                <p className="text-lg font-semibold">✅ Genuine</p>
                <p className="text-[11px] mt-1">This batch's token matches the recorded hash. Trusted source.</p>
                <button onClick={() => copyText(window.location.origin + '/trace?batch=' + encodeURIComponent(scan.batch) + '&h=' + encodeURIComponent(scan.h) + '&t=' + encodeURIComponent(scan.t))}
                  className="text-[11px] underline mt-2">Copy verify link</button>
              </div>
            ) : (
              <div className="bg-danger-light/40 text-danger rounded-btn p-4 text-center">
                <p className="text-lg font-semibold">❌ Invalid</p>
                <p className="text-[11px] mt-1">Token does not match. This QR may be forged or altered.</p>
              </div>
            )
          )}

          <p className="text-[11px] text-text-secondary leading-relaxed border-t border-border pt-3">
            🔒 Verification recomputes an HMAC token from the batch hash. A match proves the QR
            was issued by the platform and the record is unaltered — it does not certify crop
            quality or organic status.
          </p>
        </div>
      )}
    </div>
  );
}
