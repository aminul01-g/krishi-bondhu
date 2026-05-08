import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postDiaryEntry, getDiaryReport, exportDiaryPdf } from '../services/api';
import { useApi } from '../hooks/useApi';
import { Spinner, EmptyState, Skeleton } from '../components/shared/LoadingStates';

export default function DiaryPage() {
  const { t } = useTranslation();
  const { data: report, loading: reportLoading, refetch } = useApi(
    (signal) => getDiaryReport(signal), []
  );
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');

  const handleAddEntry = async () => {
    if (!input.trim()) return;
    setSubmitting(true);
    setSuccess('');
    try {
      const res = await postDiaryEntry(input.trim());
      setSuccess(res.message);
      setInput('');
      refetch();
    } catch { /* handled by UI */ }
    finally { setSubmitting(false); }
  };

  const handlePdfDownload = async () => {
    try {
      const blob = await exportDiaryPdf();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'KrishiBondhu_Report.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* silent */ }
  };

  return (
    <div className="space-y-4">
      {/* P&L summary */}
      {reportLoading ? (
        <div className="card"><Skeleton lines={3} /></div>
      ) : report ? (
        <div className="card-elevated">
          <h3 className="font-semibold text-text-primary mb-3">📊 {t('diary.title')}</h3>
          <div className="grid grid-cols-3 gap-3 text-center mb-3">
            <div className="bg-green-50 rounded-btn p-3">
              <p className="text-xs text-text-secondary">{t('diary.income')}</p>
              <p className="text-lg font-bold text-primary">৳{report.totals?.income?.toLocaleString() || 0}</p>
            </div>
            <div className="bg-red-50 rounded-btn p-3">
              <p className="text-xs text-text-secondary">{t('diary.expense')}</p>
              <p className="text-lg font-bold text-danger">৳{report.totals?.expense?.toLocaleString() || 0}</p>
            </div>
            <div className={`rounded-btn p-3 ${report.net_profit >= 0 ? 'bg-accent-light/20' : 'bg-danger-light'}`}>
              <p className="text-xs text-text-secondary">{report.net_profit >= 0 ? t('diary.profit') : t('diary.loss')}</p>
              <p className={`text-lg font-bold ${report.net_profit >= 0 ? 'text-accent' : 'text-danger'}`}>
                ৳{Math.abs(report.net_profit || 0).toLocaleString()}
              </p>
            </div>
          </div>
          <button onClick={handlePdfDownload} className="btn-outline w-full text-sm py-2">
            📄 {t('diary.download_pdf')}
          </button>
        </div>
      ) : null}

      {/* Add entry */}
      <div className="card">
        <label className="block text-sm font-medium text-text-primary mb-2">
          ✏️ {t('diary.add_entry')}
        </label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('diary.entry_placeholder')}
          className="input-field min-h-[80px] resize-none"
          rows={3}
        />
        {success && <p className="text-sm text-primary mt-2">✅ {success}</p>}
        <button
          onClick={handleAddEntry}
          disabled={submitting || !input.trim()}
          className="btn-primary w-full mt-3 flex items-center justify-center gap-2"
        >
          {submitting && <Spinner size="sm" />}
          {t('common.save')}
        </button>
      </div>
    </div>
  );
}
