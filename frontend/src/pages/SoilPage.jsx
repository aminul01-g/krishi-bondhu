import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { postSoilImage } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

export default function SoilPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const handleCapture = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setLoading(true);
    setError('');
    try {
      const data = await postSoilImage(file, lat, lon);
      setResult(data);
    } catch (err) {
      setError('Failed to analyze soil image. Please try again.');
    }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      {/* Error alert */}
      {error && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center font-semibold">
          ⚠️ {error}
        </div>
      )}

      <div className="card-elevated text-center">
        <h3 className="font-semibold text-primary mb-3">🔬 {t('nav.soil')}</h3>
        <button onClick={() => fileRef.current?.click()}
          className="btn-primary w-full flex items-center justify-center gap-2">
          📷 Capture Soil Photo
        </button>
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleCapture} />
      </div>

      {preview && (
        <div className="card"><img src={preview} alt="Soil" className="w-full rounded-btn max-h-48 object-cover" /></div>
      )}

      {loading && <div className="flex justify-center py-8"><Spinner size="lg" className="text-primary" /></div>}

      {result && !loading && (
        <div className="card-elevated border-l-4 border-soil">
          <h3 className="font-semibold text-soil mb-2">📋 Analysis Result</h3>
          <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">{result.analysis}</p>
          {result.recommendations && (
            <div className="mt-3 pt-3 border-t border-border">
              <h4 className="text-sm font-semibold text-primary mb-1">💊 Recommendations</h4>
              <p className="text-sm text-text-primary whitespace-pre-wrap">{result.recommendations}</p>
            </div>
          )}
        </div>
      )}

      {!result && !loading && !preview && <EmptyState icon="🌱" title={t('nav.soil')} message="Take a photo of your soil to get analysis" />}
    </div>
  );
}
