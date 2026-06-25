import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postSoilAnalysis } from '../services/api';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

// Same crop list as WaterPage to keep selection consistent across the app.
const CROPS = ['ধান', 'গম', 'আলু', 'ভুট্টা', 'পাট', 'সরিষা', 'মরিচ', 'টমেটো'];

const BN_NUMS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];
const toBnDigits = (s) => String(s).replace(/[0-9]/g, (d) => BN_NUMS[d]);
const BN_MONTHS = [
  'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
  'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর',
];

// Per-nutrient status → icon, colour, and direction symbol for the badges.
const STATUS_META = {
  পর্যাপ্ত: { icon: '✓', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  কম: { icon: '↓', cls: 'bg-red-50 text-red-600 border-red-200' },
  বেশি: { icon: '↑', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
};

// Map recommendation nutrient → display icon + accent colour.
const REC_ICON = {
  নাইট্রোজেন: { emoji: '🌿', bar: 'bg-emerald-500' },
  ফসফরাস: { emoji: '🔴', bar: 'bg-red-500' },
  পটাসিয়াম: { emoji: '🟡', bar: 'bg-amber-500' },
  'পিএইচ (অম্লীয়)': { emoji: '🧪', bar: 'bg-rose-500' },
  'পিএইচ (ক্ষারীয়)': { emoji: '🧪', bar: 'bg-sky-500' },
  'জৈব পদার্থ': { emoji: '🟤', bar: 'bg-amber-700' },
};

// Health-score ring colour band, matching WaterPage's gauge idiom.
function healthColor(score) {
  if (score >= 70) return { ring: 'text-emerald-500', text: 'text-emerald-600', label: '🟢 ভালো' };
  if (score >= 40) return { ring: 'text-amber-500', text: 'text-amber-600', label: '🟡 মাঝারি' };
  return { ring: 'text-red-500', text: 'text-red-600', label: '🔴 খারাপ' };
}

export default function SoilPage() {
  const { t } = useTranslation();
  const [crop, setCrop] = useState('ধান');
  const [nitrogen, setNitrogen] = useState(180);
  const [phosphorus, setPhosphorus] = useState(25);
  const [potassium, setPotassium] = useState(160);
  const [ph, setPh] = useState(6.5);
  const [organicMatter, setOrganicMatter] = useState(1.8);
  const [district, setDistrict] = useState('');

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reminderSaved, setReminderSaved] = useState(false);

  const analyze = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const payload = {
        nitrogen,
        phosphorus,
        potassium,
        ph,
        organic_matter: organicMatter,
        crop,
        ...(district ? { district } : {}),
      };
      const data = await postSoilAnalysis(payload);
      setResult(data);
      setReminderSaved(false);
    } catch (err) {
      setError(err.message || 'মাটি বিশ্লেষণ ব্যর্থ হয়েছে। আবার চেষ্টা করুন।');
    } finally {
      setLoading(false);
    }
  };

  // ---- pH helpers (real-time label before submit) ----
  const livePhStatus = ph < 6.5 ? 'অম্লীয়' : ph > 7.5 ? 'ক্ষারীয়' : 'নিরপেক্ষ';
  // Map current pH (4–9) to a 0–100% position on the gradient bar.
  const phPercent = ((ph - 4) / 5) * 100;

  // ---- Next-test reminder ----
  const nextTestDate = result
    ? new Date(Date.now() + result.next_test_recommended_days * 86400000)
    : null;
  const nextTestLabel = nextTestDate
    ? `${toBnDigits(nextTestDate.getDate())} ${BN_MONTHS[nextTestDate.getMonth()]} ${toBnDigits(nextTestDate.getFullYear())}`
    : '';

  const saveReminder = () => {
    if (!result || !nextTestDate) return;
    const payload = {
      date: nextTestDate.toISOString(),
      health_score: result.health_score,
      crop,
      createdAt: new Date().toISOString(),
    };
    localStorage.setItem('kb_soil_reminder', JSON.stringify(payload));
    setReminderSaved(true);
  };

  return (
    <div className="space-y-4 pb-6">
      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl text-sm text-center font-semibold border border-red-100">
          ⚠️ {error}
        </div>
      )}

      {/* ================= SECTION 1 — INPUT FORM ================= */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 space-y-4">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          🧪 মাটি পরীক্ষা
        </h3>

        {/* Crop + district */}
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-xs font-medium text-slate-500">ফসল</span>
            <select
              value={crop}
              onChange={(e) => setCrop(e.target.value)}
              className="mt-1 w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-lg focus:ring-primary focus:border-primary p-2.5 outline-none transition-colors"
            >
              {CROPS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">জেলা (ঐচ্ছিক)</span>
            <input
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              placeholder="যেমন: টাঙ্গাইল"
              className="mt-1 w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-lg focus:ring-primary focus:border-primary p-2.5 outline-none transition-colors"
            />
          </label>
        </div>

        {/* NPK sliders */}
        <Slider
          label="নাইট্রোজেন (N)"
          icon="🌿"
          value={nitrogen}
          min={0} max={400} step={5}
          unit="কেজি/হেক্টর"
          onChange={setNitrogen}
        />
        <Slider
          label="ফসফরাস (P)"
          icon="🔴"
          value={phosphorus}
          min={0} max={100} step={1}
          unit="কেজি/হেক্টর"
          onChange={setPhosphorus}
        />
        <Slider
          label="পটাসিয়াম (K)"
          icon="🟡"
          value={potassium}
          min={0} max={400} step={5}
          unit="কেজি/হেক্টর"
          onChange={setPotassium}
        />
        <Slider
          label="জৈব পদার্থ"
          icon="🟤"
          value={organicMatter}
          min={0} max={8} step={0.1}
          unit="%"
          onChange={setOrganicMatter}
        />

        {/* pH slider with gradient + status */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-slate-700">🧪 পিএইচ (pH)</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{toBnDigits(ph.toFixed(1))}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                livePhStatus === 'নিরপেক্ষ'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : livePhStatus === 'অম্লীয়'
                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                    : 'bg-sky-50 text-sky-700 border-sky-200'
              }`}>{livePhStatus}</span>
            </div>
          </div>
          <input
            type="range"
            min={4} max={9} step={0.1}
            value={ph}
            onChange={(e) => setPh(parseFloat(e.target.value))}
            className="w-full h-2 accent-primary cursor-pointer"
          />
          {/* pH gradient scale: red(4) → yellow(6) → green(6.5-7) → yellow(7.5) → blue(9) */}
          <div className="relative mt-2">
            <div
              className="h-2 rounded-full"
              style={{
                background:
                  'linear-gradient(to right, #ef4444 0%, #f59e0b 40%, #22c55e 50%, #22c55e 60%, #f59e0b 70%, #3b82f6 100%)',
              }}
            />
            <div
              className="absolute -top-1 w-1 h-4 bg-slate-800 rounded-full"
              style={{ left: `calc(${phPercent}% - 2px)` }}
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>৪ অম্লীয়</span>
              <span>৬.৫</span>
              <span>৭.৫</span>
              <span>৯ ক্ষারীয়</span>
            </div>
          </div>
        </div>

        <button
          onClick={analyze}
          disabled={loading}
          className="w-full bg-primary hover:bg-primary-dark text-white font-semibold rounded-lg text-sm px-4 py-3 inline-flex items-center justify-center gap-2 transition-colors disabled:opacity-70"
        >
          {loading ? <Spinner size="sm" className="text-white" /> : <span>🔬</span>}
          {loading ? 'বিশ্লেষণ হচ্ছে...' : 'বিশ্লেষণ করুন'}
        </button>
      </div>

      {/* ================= RESULTS ================= */}
      {result && !loading && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          {/* SECTION 2 — Overall health score ring */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col items-center">
            <h4 className="text-sm font-semibold text-slate-700 mb-2">মাটির স্বাস্থ্য স্কোর</h4>
            <HealthRing score={result.health_score} />
            <p className="mt-3 text-sm text-slate-600">
              সামগ্রিক অবস্থা:{' '}
              <span className={`font-bold ${healthColor(result.health_score).text}`}>
                {result.overall_health}
              </span>
            </p>
          </div>

          {/* SECTION 2 — NPK status badges */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">এনপিকে অবস্থা</h4>
            <div className="grid grid-cols-3 gap-2">
              <StatusBadge label="N" labelFull="নাইট্রোজেন" status={result.n_status} />
              <StatusBadge label="P" labelFull="ফসফরাস" status={result.p_status} />
              <StatusBadge label="K" labelFull="পটাসিয়াম" status={result.k_status} />
            </div>
          </div>

          {/* SECTION 2 — pH bar */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">পিএইচ স্কেল</h4>
            <PhScale ph={ph} status={result.ph_status} />
          </div>

          {/* SECTION 3 — Action cards */}
          {result.recommendations.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
              <h4 className="text-sm font-semibold text-slate-700 mb-3">💊 সার পরামর্শ</h4>
              <div className="space-y-3">
                {result.recommendations.map((rec, idx) => (
                  <ActionCard key={idx} rec={rec} />
                ))}
              </div>
            </div>
          )}

          {/* SECTION 4 — Next test reminder */}
          <div className="bg-gradient-to-br from-primary/5 to-accent/5 rounded-xl border border-primary/20 p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-1">📅 পরবর্তী পরীক্ষা</h4>
            <p className="text-sm text-slate-600">
              পরবর্তী মাটি পরীক্ষা:{' '}
              <span className="font-bold text-primary">
                {toBnDigits(result.next_test_recommended_days)} দিনের মধ্যে
              </span>{' '}
              (তারিখ: {nextTestLabel})
            </p>
            <button
              onClick={saveReminder}
              disabled={reminderSaved}
              className="mt-3 w-full bg-primary hover:bg-primary-dark text-white font-medium rounded-lg text-sm px-4 py-2.5 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {reminderSaved ? '✓ ক্যালেন্ডারে সংরক্ষিত হয়েছে' : '📅 ক্যালেন্ডারে যোগ করুন'}
            </button>
          </div>
        </div>
      )}

      {!result && !loading && (
        <EmptyState
          icon="🌱"
          title={t('nav.soil')}
          message="মাটির এনপিকে ও পিএইচ মান দিন, সঠিক সারের পরামর্শ পান"
        />
      )}
    </div>
  );
}

/* ---------- Sub-components ---------- */

function Slider({ label, icon, value, min, max, step, unit, onChange }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-slate-700">
          {icon} {label}
        </span>
        <span className="text-sm font-bold text-primary">
          {toBnDigits(value % 1 === 0 ? value : value.toFixed(1))}{' '}
          <span className="text-[10px] font-normal text-slate-400">{unit}</span>
        </span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 accent-primary cursor-pointer"
      />
    </div>
  );
}

function HealthRing({ score }) {
  const meta = healthColor(score);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg className="transform -rotate-90 w-36 h-36">
        <circle cx="72" cy="72" r={radius} stroke="currentColor" strokeWidth="10" fill="transparent" className="text-slate-100" />
        <circle
          cx="72" cy="72" r={radius} stroke="currentColor" strokeWidth="10" fill="transparent"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={`${meta.ring} transition-all duration-1000 ease-in-out`}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className={`text-3xl font-bold ${meta.text}`}>{toBnDigits(score)}</span>
        <span className="text-[10px] text-slate-400">/ ১০০</span>
        <span className="text-[11px] mt-1 font-medium text-slate-500">{meta.label}</span>
      </div>
    </div>
  );
}

function StatusBadge({ label, labelFull, status }) {
  const meta = STATUS_META[status] || STATUS_META.পর্যাপ্ত;
  return (
    <div className={`rounded-lg border p-2.5 text-center ${meta.cls}`}>
      <div className="text-xs font-bold uppercase tracking-wide opacity-70">{label}</div>
      <div className="text-base font-bold mt-0.5">
        {meta.icon} {status}
      </div>
      <div className="text-[10px] opacity-70 mt-0.5">{labelFull}</div>
    </div>
  );
}

function PhScale({ ph, status }) {
  const percent = ((ph - 4) / 5) * 100;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs text-slate-500">আপনার পিএইচ</span>
        <span className="text-lg font-bold text-slate-900">{toBnDigits(ph.toFixed(1))}</span>
      </div>
      <div className="relative">
        <div
          className="h-3 rounded-full"
          style={{
            background:
              'linear-gradient(to right, #ef4444 0%, #f59e0b 40%, #22c55e 50%, #22c55e 60%, #f59e0b 70%, #3b82f6 100%)',
          }}
        />
        {/* Arrow marker pointing down at current pH */}
        <div className="absolute -top-3.5" style={{ left: `calc(${percent}% - 8px)` }}>
          <div className="w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-slate-800" />
        </div>
        <div className="absolute -bottom-5" style={{ left: `calc(${percent}% - 14px)` }}>
          <span className="text-[10px] font-semibold text-slate-700 whitespace-nowrap">{status}</span>
        </div>
      </div>
      <div className="flex justify-between text-[10px] text-slate-400 mt-7">
        <span>৪</span>
        <span>৬.৫</span>
        <span>৭.৫</span>
        <span>৯</span>
      </div>
    </div>
  );
}

function ActionCard({ rec }) {
  const icon = REC_ICON[rec.nutrient] || { emoji: '💊', bar: 'bg-slate-400' };
  return (
    <div className="flex gap-3 rounded-lg border border-slate-200 p-3 bg-slate-50/50">
      {/* Left: coloured icon with accent bar */}
      <div className="flex flex-col items-center gap-1">
        <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-xl shrink-0">
          {icon.emoji}
        </div>
        <div className={`w-1 flex-1 rounded-full ${icon.bar}`} />
      </div>
      {/* Right: content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-xs font-semibold text-slate-500">{rec.nutrient}</span>
        </div>
        <p className="text-sm font-bold text-slate-900 leading-snug">{rec.action}</p>
        <p className="text-xs text-slate-600 mt-1">
          📦 {rec.amount} · ⏰ {rec.timing}
        </p>
        {rec.brand_suggestion && rec.brand_suggestion !== '—' && (
          <p className="text-[11px] text-slate-400 mt-1">প্রস্তাবিত ব্র্যান্ড: {rec.brand_suggestion}</p>
        )}
      </div>
    </div>
  );
}
