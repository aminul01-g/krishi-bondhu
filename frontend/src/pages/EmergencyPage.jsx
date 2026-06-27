import { useState, useRef, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { postDamageReport, postHelplineCall, isNetworkError } from '../services/api';
import { getFarmerProfile } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { useEmergencyQueue } from '../hooks/useEmergencyQueue';
import { useToast } from '../contexts/ToastContext';
import { queueReport } from '../utils/emergencyDb';
import { getOfficePhone } from '../data/agriOffices';
import { Spinner } from '../components/shared/LoadingStates';

// Fallback to Dhaka if GPS fails.
const DEFAULT_LAT = 23.81;
const DEFAULT_LON = 90.41;

const OFFLINE_QUEUED_MSG =
  'সংযোগ নেই। রিপোর্ট সংরক্ষিত হয়েছে। সংযোগ ফিরলে স্বয়ংক্রিয়ভাবে পাঠানো হবে।';

export default function EmergencyPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const toast = useToast();
  const { pendingCount, refreshCount } = useEmergencyQueue();

  const [step, setStep] = useState('idle');
  const [cropType, setCropType] = useState('');
  const [damageCause, setDamageCause] = useState('');
  const [damagePercent, setDamagePercent] = useState(50);
  const [voiceText, setVoiceText] = useState('');
  const [photos, setPhotos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [reference, setReference] = useState(null);
  const [submittedPayload, setSubmittedPayload] = useState(null);
  const [error, setError] = useState('');
  const [district, setDistrict] = useState('');
  const fileRef = useRef(null);

  // Try to learn the farmer's district for the "forward to agriculture office"
  // action. Non-critical: falls back to national helpline if unknown.
  useEffect(() => {
    getFarmerProfile()
      .then((p) => { if (p && p.district) setDistrict(p.district); })
      .catch(() => {});
  }, []);

  const handlePhotoCapture = (e) => {
    const files = Array.from(e.target.files || []);
    setPhotos((prev) => [...prev, ...files].slice(0, 5));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const imageData = await photosToBase64(photos);
      const latVal = lat ?? DEFAULT_LAT;
      const lonVal = lon ?? DEFAULT_LON;

      const res = await postDamageReport({
        crop_type: cropType,
        damage_cause: damageCause,
        damage_estimate_percent: damagePercent,
        yield_loss_estimate_percent: damagePercent,
        lat: latVal,
        lon: lonVal,
        voice_statement_transcribed: voiceText,
        image_data: imageData,
      });

      setResult(res);
      setReference(res?.id || makeReference());
      setSubmittedPayload({
        cropType, damageCause, damagePercent, voiceText, lat: latVal, lon: lonVal,
      });
      setStep('done');
      // Drop the locally held photos now that they reached the server.
      setPhotos([]);
    } catch (err) {
      if (isNetworkError(err)) {
        // Offline — persist report (+ raw photo Blobs) for automatic retry.
        try {
          await queueReport(
            {
              cropType, damageCause, damagePercent, voiceText,
              lat: lat ?? DEFAULT_LAT, lon: lon ?? DEFAULT_LON,
            },
            photos
          );
          setError(OFFLINE_QUEUED_MSG);
          refreshCount();
          // Reset the form so the farmer can file another report if needed.
          setCropType(''); setDamageCause(''); setDamagePercent(50); setVoiceText(''); setPhotos([]);
        } catch {
          setError('রিপোর্ট সংরক্ষণ করা যায়নি। আবার চেষ্টা করুন বা 16123 নম্বরে কল করুন।');
        }
      } else {
        setError(err.message || 'Report submission failed. Please try again or call 16123.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const callHelpline = () => {
    postHelplineCall({ crop_type: cropType, damage_estimate: damagePercent, lat, lon, status: 'initiated' }).catch(() => {});
    window.location.href = 'tel:16123';
  };

  const resetToIdle = () => {
    setStep('idle');
    setResult(null);
    setReference(null);
    setSubmittedPayload(null);
  };

  return (
    <div className="space-y-4">
      {/* Error / info alert */}
      {error && (
        <div className="bg-danger text-white p-4 rounded-card text-sm text-center font-semibold">
          🚨 {error}
        </div>
      )}

      {/* Pending reports hint */}
      {pendingCount > 0 && step !== 'done' && (
        <div className="bg-accent/15 text-soil border border-accent/40 p-3 rounded-card text-xs text-center font-medium">
          ⏳ {pendingCount} টি রিপোর্ট স্থগিত আছে — সংযোগ ফিরলে স্বয়ংক্রিয়ভাবে পাঠানো হবে।
        </div>
      )}

      {/* Helpline button */}
      <button onClick={callHelpline}
        className="w-full bg-danger text-white font-bold py-4 rounded-card shadow-elevated
                   flex items-center justify-center gap-3 text-lg active:scale-[0.97] transition-all">
        📞 {t('emergency.call_helpline')}
      </button>

      {step === 'idle' && (
        <button onClick={() => setStep('form')}
          className="w-full btn-danger py-4 text-lg shadow-elevated flex items-center justify-center gap-2">
          🚨 {t('emergency.report_damage')}
        </button>
      )}

      {step === 'form' && (
        <div className="card-elevated space-y-4">
          <h3 className="font-semibold text-danger flex items-center gap-2">🚨 {t('emergency.report_damage')}</h3>
          <input value={cropType} onChange={(e) => setCropType(e.target.value)}
            placeholder="ফসলের নাম (যেমন: ধান, গম)" className="input-field" />
          <input value={damageCause} onChange={(e) => setDamageCause(e.target.value)}
            placeholder="ক্ষতির কারণ (যেমন: বন্যা, পোকা)" className="input-field" />
          <div>
            <label className="text-sm text-text-secondary">ক্ষতির পরিমাণ: {damagePercent}%</label>
            <input type="range" min={0} max={100} value={damagePercent}
              onChange={(e) => setDamagePercent(Number(e.target.value))}
              className="w-full accent-danger" />
          </div>

          <div>
            <button onClick={() => fileRef.current?.click()}
              className="btn-outline w-full !py-2 text-sm flex items-center justify-center gap-2">
              📷 {t('emergency.take_photos')} ({photos.length}/5)
            </button>
            <input ref={fileRef} type="file" accept="image/*" capture="environment"
              multiple className="hidden" onChange={handlePhotoCapture} />
            {photos.length > 0 && (
              <div className="flex gap-2 mt-2 overflow-x-auto">
                {photos.map((p, i) => (
                  <img key={i} src={URL.createObjectURL(p)} className="w-16 h-16 rounded-btn object-cover" alt="" />
                ))}
              </div>
            )}
          </div>

          <textarea value={voiceText} onChange={(e) => setVoiceText(e.target.value)}
            placeholder="ক্ষতির বিবরণ লিখুন..." className="input-field min-h-[60px]" rows={2} />

          <button onClick={handleSubmit} disabled={submitting || !cropType}
            className="btn-danger w-full flex items-center justify-center gap-2">
            {submitting && <Spinner size="sm" />} {t('emergency.submit_report')}
          </button>
        </div>
      )}

      {step === 'done' && submittedPayload && (
        <SuccessScreen
          reference={reference}
          payload={submittedPayload}
          result={result}
          district={district}
          onReset={resetToIdle}
        />
      )}
    </div>
  );
}

/* ───────────────────────── Success / Share screen ───────────────────────── */

function SuccessScreen({ reference, payload, result, district, onReset }) {
  const { t } = useTranslation();
  const { cropType, damageCause, damagePercent, voiceText, lat, lon } = payload;

  const shareText = useMemo(() => {
    // WhatsApp pre-filled message (matches the required template).
    const detail = voiceText?.trim() || `${cropType} ফসলের ${damagePercent}% ক্ষতি (${damageCause || 'অজানা কারণ'})।`;
    return `আমার ফসলের ক্ষতির রিপোর্ট (রেফ: ${reference}): ${damagePercent}% ক্ষতি হয়েছে। বিস্তারিত: ${detail}`;
  }, [reference, cropType, damageCause, damagePercent, voiceText]);

  const shareWhatsApp = () => {
    window.open('https://wa.me/?text=' + encodeURIComponent(shareText), '_blank');
  };

  const forwardToOffice = () => {
    const phone = getOfficePhone(district);
    // wa.me expects the number in international form, digits only.
    const digits = phone.replace(/[^0-9]/g, '');
    // Bangladesh numbers need a 88 prefix when dialled internationally.
    const intl = digits.startsWith('880') ? digits : `880${digits.replace(/^0/, '')}`;
    const officeText =
      `${shareText}\n\nঅনুগ্রহ করে আমার এলাকার কৃষি অফিসে সহায়তা প্রয়োজন। জেলা: ${district || 'অজানা'}।`;
    window.open(`https://wa.me/${intl}?text=${encodeURIComponent(officeText)}`, '_blank');
  };

  const downloadPdf = () => {
    const html = buildReceiptHtml({ reference, payload, result, district });
    const win = window.open('', '_blank');
    if (!win) return; // pop-up blocked
    win.document.open();
    win.document.write(html);
    win.document.close();
    // Give the new document a tick to lay out before printing.
    setTimeout(() => { win.focus(); win.print(); }, 300);
  };

  return (
    <div className="card-elevated space-y-4 border-l-4 border-primary">
      <div>
        <h3 className="font-semibold text-primary text-lg">রিপোর্ট জমা হয়েছে ✅</h3>
        <p className="text-sm text-text-secondary mt-1">রেফারেন্স: <span className="font-mono font-semibold text-text-primary">{reference}</span></p>
      </div>

      {/* Damage summary card */}
      <div className="bg-bg rounded-card p-4 space-y-2 text-sm">
        <SummaryRow label="ফসল" value={cropType || '—'} />
        <SummaryRow label="কারণ" value={damageCause || '—'} />
        <SummaryRow label="ক্ষতি" value={`${damagePercent}%`} />
        <SummaryRow label="অবস্থান" value={(lat != null && lon != null) ? `${lat}, ${lon}` : '—'} />
      </div>

      {/* Action buttons */}
      <div className="space-y-2">
        <button onClick={shareWhatsApp}
          className="w-full bg-[#25D366] text-white font-semibold py-3 rounded-btn
                     flex items-center justify-center gap-2 active:scale-[0.97] transition-all">
          <WhatsAppIcon /> WhatsApp-এ শেয়ার করুন
        </button>
        <button onClick={forwardToOffice}
          className="w-full btn-primary flex items-center justify-center gap-2">
          🏛️ কৃষি অফিসে ফরোয়ার্ড করুন
        </button>
        <button onClick={downloadPdf}
          className="w-full btn-outline flex items-center justify-center gap-2">
          📄 PDF ডাউনলোড করুন
        </button>
      </div>

      <button onClick={onReset} className="btn-outline w-full !py-2 text-sm">
        {t('common.back')}
      </button>
    </div>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-text-secondary">{label}</span>
      <span className="font-medium text-text-primary text-right break-words">{value}</span>
    </div>
  );
}

/** Inline WhatsApp glyph (avoids adding an icon dependency). */
function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M.057 24l1.687-6.163a11.867 11.867 0 01-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.82 11.82 0 018.413 3.488 11.82 11.82 0 013.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 01-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 001.51 5.26l-.999 3.648 3.978-1.607zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.078 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z" />
    </svg>
  );
}

/* ───────────────────────── Helpers ───────────────────────── */

/** Convert an array of File objects to base64 data URLs (for online submit). */
function photosToBase64(photos) {
  return Promise.all(
    photos.map(
      (photo) =>
        new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.onerror = () => resolve(null);
          reader.readAsDataURL(photo);
        })
    )
  ).then((arr) => arr.filter(Boolean));
}

/** Build a "KB-YYYY-XXXXX" reference number. */
function makeReference() {
  const year = new Date().getFullYear();
  const rand = Math.floor(10000 + Math.random() * 90000); // 5 digits
  return `KB-${year}-${rand}`;
}

/** Build a printable HTML receipt document string for the PDF action. */
function buildReceiptHtml({ reference, payload, result, district }) {
  const { cropType, damageCause, damagePercent, voiceText, lat, lon } = payload;
  const date = new Date().toLocaleString('en-GB');
  const aiReport = result?.ai_report ? `<p class="ai">${escapeHtml(result.ai_report)}</p>` : '';
  const office = getOfficePhone(district);

  return `<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8" />
<title>KrishiBondhu — ক্ষতির রিপোর্ট (${reference})</title>
<style>
  body { font-family: 'Noto Sans Bengali', Arial, sans-serif; color: #1A1A2E; margin: 40px; }
  .head { display: flex; justify-content: space-between; border-bottom: 3px solid #2D6A4F; padding-bottom: 12px; }
  .brand { font-size: 22px; font-weight: 700; color: #2D6A4F; }
  .ref { font-size: 13px; color: #6B7280; text-align: right; }
  h1 { font-size: 18px; margin: 24px 0 12px; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 8px 0; border-bottom: 1px solid #E5E2DB; font-size: 14px; }
  td.label { color: #6B7280; width: 35%; }
  td.value { font-weight: 600; }
  .ai { background: #F7F5F0; padding: 12px; border-radius: 8px; white-space: pre-wrap; font-size: 13px; }
  .foot { margin-top: 28px; font-size: 12px; color: #6B7280; }
  @media print { body { margin: 16px; } }
</style>
</head>
<body>
  <div class="head">
    <div class="brand">🌾 কৃষি বন্ধু</div>
    <div class="ref">
      রেফারেন্স: ${reference}<br/>
      ${escapeHtml(date)}
    </div>
  </div>
  <h1>ফসলের ক্ষতির রিপোর্ট</h1>
  <table>
    <tr><td class="label">ফসল</td><td class="value">${escapeHtml(cropType || '—')}</td></tr>
    <tr><td class="label">ক্ষতির কারণ</td><td class="value">${escapeHtml(damageCause || '—')}</td></tr>
    <tr><td class="label">ক্ষতির পরিমাণ</td><td class="value">${damagePercent}%</td></tr>
    <tr><td class="label">অবস্থান</td><td class="value">${lat != null && lon != null ? `${lat}, ${lon}` : '—'}</td></tr>
    <tr><td class="label">বিবরণ</td><td class="value">${escapeHtml(voiceText || '—')}</td></tr>
    <tr><td class="label">নিকটস্থ কৃষি অফিস</td><td class="value">${escapeHtml(office)}</td></tr>
  </table>
  ${aiReport}
  <div class="foot">
    এই রসিদটি কৃষি বন্ধু অ্যাপ থেকে তৈরি। জরুরি সহায়তার জন্য হেল্পলাইন: 16123।
  </div>
</body>
</html>`;
}

/** Minimal HTML-escaper for user-supplied strings in the receipt. */
function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
