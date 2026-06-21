import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  postDiaryEntry,
  getDiaryReport,
  exportDiaryPdf,
  getDiaryEntries,
  deleteDiaryEntry,
} from '../services/api';
import { useApi } from '../hooks/useApi';
import { Spinner, Skeleton } from '../components/shared/LoadingStates';

// ─── Category config ────────────────────────────────────────────────────────
const CATEGORIES = [
  { key: 'seed',       emoji: '🌱', label: 'বীজ',      template: 'বীজ কিনলাম ৳XXX' },
  { key: 'fertilizer', emoji: '🌿', label: 'সার',      template: 'সার কিনলাম ৳XXX' },
  { key: 'pesticide',  emoji: '💊', label: 'কীটনাশক', template: 'কীটনাশক কিনলাম ৳XXX' },
  { key: 'labor',      emoji: '👷', label: 'মজুর',     template: 'মজুরি দিলাম ৳XXX' },
  { key: 'irrigation', emoji: '💧', label: 'সেচ',      template: 'সেচ দিলাম ৳XXX' },
  { key: 'harvest',    emoji: '🌾', label: 'ফলন',      template: 'ফসল বিক্রি করলাম ৳XXX' },
];

const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map(c => [c.key, c]));

// Bengalised date formatting
function formatBengaliDate(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (isNaN(d)) return '';
  const bengaliMonths = [
    'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
    'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর',
  ];
  const day = d.getDate().toString().replace(/\d/g, c => '০১২৩৪৫৬৭৮৯'[c]);
  return `${day} ${bengaliMonths[d.getMonth()]}`;
}

function toBengaliNum(n) {
  return n.toString().replace(/\d/g, c => '০১২৩৪৫৬৭৮৯'[c]);
}

// ─── Category Quick-Entry Chips ──────────────────────────────────────────────
function CategoryChips({ onSelect }) {
  return (
    <div className="diary-chips-grid">
      {CATEGORIES.map(cat => (
        <button
          key={cat.key}
          className="diary-chip"
          onClick={() => onSelect(cat.template)}
          title={`${cat.label} এন্ট্রি যোগ করুন`}
        >
          <span className="diary-chip-emoji">{cat.emoji}</span>
          <span className="diary-chip-label">{cat.label}</span>
        </button>
      ))}
    </div>
  );
}

// ─── Expense Breakdown Chart ─────────────────────────────────────────────────
function ExpenseBreakdown({ breakdown }) {
  if (!breakdown || breakdown.length === 0) return null;
  const top3 = breakdown.slice(0, 3);
  const maxAmt = Math.max(...top3.map(c => c.amount), 1);

  return (
    <div className="expense-breakdown">
      <h4 className="breakdown-title">📊 ব্যয়ের বিভাগ</h4>
      <div className="breakdown-bars">
        {top3.map((cat, i) => {
          const catInfo = CATEGORY_MAP[cat.category];
          const pct = Math.round((cat.amount / maxAmt) * 100);
          return (
            <div key={cat.category} className="breakdown-row">
              <div className="breakdown-label">
                <span>{catInfo?.emoji || '📦'}</span>
                <span>{cat.label}</span>
              </div>
              <div className="breakdown-bar-track">
                <div
                  className="breakdown-bar-fill"
                  style={{
                    width: `${pct}%`,
                    '--bar-color': ['#22c55e', '#f59e0b', '#6366f1'][i],
                    animationDelay: `${i * 0.12}s`,
                  }}
                />
              </div>
              <span className="breakdown-amount">৳{toBengaliNum(cat.amount.toLocaleString())}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Entry History Row ───────────────────────────────────────────────────────
function EntryRow({ entry, onDelete }) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const catInfo = CATEGORY_MAP[entry.category] || { emoji: '📦', label: entry.category_label || 'অন্যান্য' };
  const isIncome = entry.entry_type === 'income' || entry.entry_type === 'yield';

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(entry.id);
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  };

  return (
    <div className="entry-row">
      {/* Left: category + date */}
      <div className="entry-left">
        <span className="entry-emoji">{catInfo.emoji}</span>
        <div>
          <p className="entry-cat-label">{catInfo.label}</p>
          <p className="entry-date">{formatBengaliDate(entry.date)}</p>
        </div>
      </div>

      {/* Center: notes */}
      <p className="entry-text">{entry.text || '—'}</p>

      {/* Right: amount + actions */}
      <div className="entry-right">
        <span className={`entry-amount ${isIncome ? 'entry-income' : 'entry-expense'}`}>
          {isIncome ? '+' : '-'}৳{toBengaliNum(Math.round(entry.amount).toLocaleString())}
        </span>

        {confirming ? (
          <div className="entry-confirm">
            <span className="confirm-text">নিশ্চিত করুন?</span>
            <button
              className="confirm-yes"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? '…' : 'হ্যাঁ'}
            </button>
            <button className="confirm-no" onClick={() => setConfirming(false)}>না</button>
          </div>
        ) : (
          <button
            className="delete-btn"
            onClick={() => setConfirming(true)}
            title="মুছুন"
            aria-label="এন্ট্রি মুছুন"
          >
            🗑️
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Main DiaryPage ──────────────────────────────────────────────────────────
export default function DiaryPage() {
  const { t } = useTranslation();
  const { data: report, loading: reportLoading, refetch: refetchReport } = useApi(
    (signal) => getDiaryReport(signal), []
  );

  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Entries list state
  const [entries, setEntries] = useState([]);
  const [entriesLoading, setEntriesLoading] = useState(true);
  const [entriesError, setEntriesError] = useState('');

  const fetchEntries = useCallback(async () => {
    setEntriesLoading(true);
    setEntriesError('');
    try {
      const data = await getDiaryEntries(1);
      setEntries(data.items || []);
    } catch (e) {
      setEntriesError('এন্ট্রি লোড করতে সমস্যা হয়েছে।');
    } finally {
      setEntriesLoading(false);
    }
  }, []);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const handleChipSelect = (template) => {
    setInput(template);
  };

  const handleAddEntry = async () => {
    if (!input.trim()) return;
    setSubmitting(true);
    setSuccess('');
    setError('');
    try {
      const res = await postDiaryEntry(input.trim());
      setSuccess(res.message);
      setInput('');
      refetchReport();
      fetchEntries();
    } catch (err) {
      setError('এন্ট্রি সেভ করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    await deleteDiaryEntry(id);
    setEntries(prev => prev.filter(e => e.id !== id));
    refetchReport();
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
    } catch (err) {
      setError('PDF তৈরিতে সমস্যা হয়েছে।');
    }
  };

  return (
    <div className="diary-page space-y-4">
      {/* ── Error alert ── */}
      {error && (
        <div className="bg-danger-light text-danger p-4 rounded-card text-sm text-center font-semibold">
          ⚠️ {error}
        </div>
      )}

      {/* ── P&L Summary Card ── */}
      {reportLoading ? (
        <div className="card"><Skeleton lines={3} /></div>
      ) : report ? (
        <div className="card-elevated pnl-card">
          <h3 className="font-semibold text-text-primary mb-3">📊 {t('diary.title')}</h3>

          {/* Income / Expense / Profit grid */}
          <div className="grid grid-cols-3 gap-3 text-center mb-4">
            <div className="pnl-cell pnl-income">
              <p className="pnl-cell-label">{t('diary.income')}</p>
              <p className="pnl-cell-value text-primary">
                ৳{report.totals?.income?.toLocaleString() || 0}
              </p>
            </div>
            <div className="pnl-cell pnl-expense">
              <p className="pnl-cell-label">{t('diary.expense')}</p>
              <p className="pnl-cell-value text-danger">
                ৳{report.totals?.expense?.toLocaleString() || 0}
              </p>
            </div>
            <div className={`pnl-cell ${report.net_profit >= 0 ? 'pnl-profit' : 'pnl-loss'}`}>
              <p className="pnl-cell-label">
                {report.net_profit >= 0 ? t('diary.profit') : t('diary.loss')}
              </p>
              <p className={`pnl-cell-value ${report.net_profit >= 0 ? 'text-accent' : 'text-danger'}`}>
                ৳{Math.abs(report.net_profit || 0).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Expense Breakdown Chart */}
          <ExpenseBreakdown breakdown={report.category_breakdown} />

          <button onClick={handlePdfDownload} className="btn-outline w-full text-sm py-2 mt-3">
            📄 {t('diary.download_pdf')}
          </button>
        </div>
      ) : null}

      {/* ── Add Entry Card ── */}
      <div className="card">
        <label className="block text-sm font-semibold text-text-primary mb-3">
          ✏️ {t('diary.add_entry')}
        </label>

        {/* Category Quick-Entry Chips */}
        <CategoryChips onSelect={handleChipSelect} />

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('diary.entry_placeholder')}
          className="input-field min-h-[80px] resize-none mt-3"
          rows={3}
        />

        {success && (
          <p className="text-sm text-primary mt-2 flex items-center gap-1">
            ✅ {success}
          </p>
        )}

        <button
          onClick={handleAddEntry}
          disabled={submitting || !input.trim()}
          className="btn-primary w-full mt-3 flex items-center justify-center gap-2"
        >
          {submitting && <Spinner size="sm" />}
          {t('common.save')}
        </button>
      </div>

      {/* ── Entry History List ── */}
      <div className="card">
        <h3 className="font-semibold text-text-primary mb-3">📋 সাম্প্রতিক এন্ট্রি</h3>

        {entriesError && (
          <p className="text-sm text-danger text-center py-2">{entriesError}</p>
        )}

        {entriesLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => <Skeleton key={i} lines={2} />)}
          </div>
        ) : entries.length === 0 ? (
          <div className="empty-entries">
            <p className="text-4xl mb-2">📓</p>
            <p className="text-text-secondary text-sm">এখনো কোনো এন্ট্রি নেই।</p>
            <p className="text-text-secondary text-xs">উপরের চিপ বা টেক্সটবক্স ব্যবহার করে প্রথম এন্ট্রি যোগ করুন।</p>
          </div>
        ) : (
          <div className="entries-list">
            {entries.map(entry => (
              <EntryRow key={entry.id} entry={entry} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
