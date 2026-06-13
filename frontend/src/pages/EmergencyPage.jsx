import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { postDamageReport, postHelplineCall } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner } from '../components/shared/LoadingStates';

export default function EmergencyPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [step, setStep] = useState('idle');
  const [cropType, setCropType] = useState('');
  const [damageCause, setDamageCause] = useState('');
  const [damagePercent, setDamagePercent] = useState(50);
  const [voiceText, setVoiceText] = useState('');
  const [photos, setPhotos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const handlePhotoCapture = (e) => {
    const files = Array.from(e.target.files || []);
    setPhotos((prev) => [...prev, ...files].slice(0, 5));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const imageData = [];
      for (const photo of photos) {
        const reader = new FileReader();
        const base64 = await new Promise((resolve) => {
          reader.onload = () => resolve(reader.result);
          reader.readAsDataURL(photo);
        });
        imageData.push(base64);
      }
      const res = await postDamageReport({
        crop_type: cropType, damage_cause: damageCause,
        damage_estimate_percent: damagePercent, yield_loss_estimate_percent: damagePercent,
        lat: lat || 23.81, lon: lon || 90.41,
        voice_statement_transcribed: voiceText, image_data: imageData,
      });
      setResult(res);
      setStep('done');
    } catch (err) {
      const pendingReport = {
        crop_type: cropType,
        damage_cause: damageCause,
        damage_estimate_percent: damagePercent,
        yield_loss_estimate_percent: damagePercent,
        lat: lat || 23.81,
        lon: lon || 90.41,
        voice_statement_transcribed: voiceText,
        image_data: photos.map(p => URL.createObjectURL(p))
      };
      localStorage.setItem('kb_pending_emergency', JSON.stringify(pendingReport));
      setError('Report submission failed. Please try again or call 16123.');
    }
    finally { setSubmitting(false); }
  };

  const callHelpline = () => {
    postHelplineCall({ crop_type: cropType, damage_estimate: damagePercent, lat, lon, status: 'initiated' }).catch(() => {});
    window.location.href = 'tel:16123';
  };

  return (
    <div className="space-y-4">
      {/* Error alert */}
      {error && (
        <div className="bg-danger text-white p-4 rounded-card text-sm text-center font-semibold">
          🚨 {error}
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
            placeholder="Crop type (e.g. Rice)" className="input-field" />
          <input value={damageCause} onChange={(e) => setDamageCause(e.target.value)}
            placeholder="Cause (e.g. Flood, Pest)" className="input-field" />
          <div>
            <label className="text-sm text-text-secondary">Damage: {damagePercent}%</label>
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
            placeholder="Describe the damage..." className="input-field min-h-[60px]" rows={2} />

          <button onClick={handleSubmit} disabled={submitting || !cropType}
            className="btn-danger w-full flex items-center justify-center gap-2">
            {submitting && <Spinner size="sm" />} {t('emergency.submit_report')}
          </button>
        </div>
      )}

      {step === 'done' && result && (
        <div className="card-elevated border-l-4 border-primary">
          <h3 className="font-semibold text-primary mb-2">✅ Report Submitted</h3>
          <p className="text-sm text-text-secondary mb-2">ID: {result.id}</p>
          <p className="text-sm text-text-primary whitespace-pre-wrap">{result.ai_report}</p>
          <button onClick={() => { setStep('idle'); setResult(null); }}
            className="btn-outline w-full mt-3 !py-2 text-sm">{t('common.back')}</button>
        </div>
      )}
    </div>
  );
}
