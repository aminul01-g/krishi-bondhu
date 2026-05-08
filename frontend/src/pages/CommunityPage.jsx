import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getCommunityQuestions, postCommunityQuestion } from '../services/api';
import { useApi } from '../hooks/useApi';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';

export default function CommunityPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [search, setSearch] = useState('');
  const { data: questions, loading, refetch } = useApi(
    (s) => getCommunityQuestions(search || null, 20, s), [search]
  );
  const [showForm, setShowForm] = useState(false);
  const [qText, setQText] = useState('');
  const [qCrop, setQCrop] = useState('Rice');
  const [submitting, setSubmitting] = useState(false);

  const handleAsk = async () => {
    if (!qText.trim()) return;
    setSubmitting(true);
    try {
      await postCommunityQuestion({
        question_text: qText, crop_type: qCrop,
        growth_stage: null, lat: lat || 23.81, lon: lon || 90.41,
      });
      setQText(''); setShowForm(false); refetch();
    } catch { /* handled */ }
    finally { setSubmitting(false); }
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="flex gap-2">
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder={`🔍 ${t('common.search')}...`} className="input-field flex-1 !py-2" />
        <button onClick={() => setShowForm(!showForm)}
          className="btn-primary !py-2 !px-4 text-xl">+</button>
      </div>

      {/* Ask form */}
      {showForm && (
        <div className="card-elevated space-y-3">
          <textarea value={qText} onChange={(e) => setQText(e.target.value)}
            placeholder="Ask your question..." className="input-field min-h-[60px]" rows={2} />
          <div className="flex gap-2">
            <select value={qCrop} onChange={(e) => setQCrop(e.target.value)} className="input-field flex-1 !py-2">
              {['Rice', 'Wheat', 'Potato', 'Maize', 'Jute', 'Onion'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <button onClick={handleAsk} disabled={submitting || !qText.trim()}
              className="btn-primary !py-2 flex items-center gap-1">
              {submitting ? <Spinner size="sm" /> : '➤'} {t('common.submit')}
            </button>
          </div>
        </div>
      )}

      {/* Questions list */}
      {loading ? (
        <div className="space-y-3">{[1,2,3].map((i) => <div key={i} className="card"><Skeleton lines={2} /></div>)}</div>
      ) : questions?.length > 0 ? (
        <div className="space-y-3">
          {(Array.isArray(questions) ? questions : []).map((q, i) => (
            <div key={q.id || i} className="card hover:shadow-elevated transition-shadow">
              <div className="flex items-start gap-2 mb-2">
                <span className="badge-success text-xs">{q.crop_type || 'General'}</span>
                <span className="badge-warning text-xs">{q.status || 'open'}</span>
              </div>
              <p className="text-sm text-text-primary font-medium">{q.question_text}</p>
              {q.answers_count > 0 && (
                <p className="text-xs text-text-secondary mt-2">💬 {q.answers_count} answers</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon="🤝" title={t('nav.community')} message="No questions yet. Be the first to ask!" />
      )}
    </div>
  );
}
