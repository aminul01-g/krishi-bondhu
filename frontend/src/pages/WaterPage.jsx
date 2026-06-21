import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { postWaterAdvice } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';

const CROPS = ['ধান', 'গম', 'আলু', 'ভুট্টা', 'পাট', 'সরিষা', 'মরিচ', 'টমেটো'];

export default function WaterPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [crop, setCrop] = useState('ধান');
  const [adviceData, setAdviceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);

  const fetchAdvice = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await postWaterAdvice(lat || 23.81, lon || 90.41, crop);
      setAdviceData(data);
    } catch (err) {
      setError('Unable to get irrigation advice. Check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const renderGauge = () => {
    if (!adviceData || adviceData.moisture_index == null) return null;
    const index = adviceData.moisture_index;
    const percentage = Math.round(index * 100);
    
    let colorClass = 'text-green-500';
    let statusText = '🟢 ভালো';
    
    if (percentage < 40) {
      colorClass = 'text-red-500';
      statusText = '🔴 সেচ দিন';
    } else if (percentage <= 70) {
      colorClass = 'text-amber-500';
      statusText = '🟡 সতর্ক থাকুন';
    }

    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className="flex flex-col items-center justify-center my-6">
        <div className="relative flex items-center justify-center">
          <svg className="transform -rotate-90 w-32 h-32">
            <circle cx="64" cy="64" r={radius} stroke="currentColor" strokeWidth="8" fill="transparent" className="text-slate-100" />
            <circle 
              cx="64" cy="64" r={radius} stroke="currentColor" strokeWidth="8" fill="transparent" 
              strokeDasharray={circumference} 
              strokeDashoffset={strokeDashoffset} 
              className={`${colorClass} transition-all duration-1000 ease-in-out`} 
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center">
            <span className={`text-2xl font-bold ${colorClass}`}>{percentage}%</span>
            <span className="text-[10px] text-slate-500 mt-1">{statusText}</span>
          </div>
        </div>
        <div className="mt-4 text-center">
          <p className="text-sm font-medium text-slate-700">দৈনিক পানির চাহিদা: <span className="font-bold text-sky-600">{adviceData.et0_mm_per_day} মিমি</span></p>
          <p className="text-xs text-slate-500 mt-1">বর্তমান বৃষ্টিপাত: {adviceData.current_rainfall_mm} মিমি</p>
        </div>
      </div>
    );
  };

  const renderCalendar = () => {
    if (!adviceData || !adviceData.irrigation_schedule) return null;
    return (
      <div className="mb-6">
        <h4 className="font-semibold text-slate-800 mb-3 text-sm">৭ দিনের সেচ ক্যালেন্ডার</h4>
        <div className="flex overflow-x-auto gap-3 pb-2 snap-x scrollbar-hide">
          {adviceData.irrigation_schedule.map((day, idx) => {
            const isRain = day.reason.includes('বৃষ্টি');
            const bgClass = day.irrigate ? 'bg-sky-50 border-sky-200' : 'bg-slate-50 border-slate-200';
            const icon = day.irrigate ? '💧' : (isRain ? '🌧️' : '☀️');
            const amountText = day.irrigate ? `${day.amount_mm} মিমি` : (isRain ? 'বৃষ্টি' : '—');
            
            return (
              <div key={idx} className={`snap-center flex-shrink-0 w-[72px] rounded-xl border ${bgClass} p-2 flex flex-col items-center justify-center relative group transition-colors hover:border-sky-300 cursor-help`}>
                <span className="text-[11px] font-medium text-slate-600 truncate w-full text-center">{day.day}</span>
                <span className="text-2xl my-1.5">{icon}</span>
                <span className="text-[10px] font-bold text-slate-700">{amountText}</span>
                
                {/* Tooltip */}
                <div className="absolute bottom-full mb-2 hidden group-hover:block w-max max-w-[120px] bg-slate-800 text-white text-[10px] rounded px-2 py-1.5 z-10 text-center shadow-lg">
                  {day.reason}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800"></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4 pb-6">
      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl text-sm text-center font-semibold border border-red-100">
          ⚠️ {error}
        </div>
      )}

      {/* Section 1: Crop Selector */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-3 flex items-center gap-2">
        <select 
          value={crop} 
          onChange={(e) => setCrop(e.target.value)} 
          className="flex-1 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-lg focus:ring-sky-500 focus:border-sky-500 block w-full p-2.5 outline-none transition-colors"
        >
          {CROPS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button 
          onClick={fetchAdvice} 
          disabled={loading} 
          className="bg-sky-600 hover:bg-sky-700 text-white font-medium rounded-lg text-sm px-4 py-2.5 text-center inline-flex items-center transition-colors disabled:opacity-70"
        >
          {loading ? (
            <div className="mr-2"><Spinner size="sm" /></div>
          ) : (
            <span className="mr-2">💧</span>
          )}
          {t('common.search')}
        </button>
      </div>

      {adviceData && !loading && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <h3 className="font-semibold text-slate-800 mb-2 flex items-center gap-2">
            💧 {t('nav.water')} ড্যাশবোর্ড
          </h3>
          
          {/* Section 2: Soil Moisture Gauge */}
          {renderGauge()}

          {/* Section 3: 7-Day Calendar */}
          {renderCalendar()}

          {/* Section 4: Text Advice */}
          <div className="mt-4 pt-4 border-t border-slate-100">
            <div className={`text-sm text-slate-600 leading-relaxed transition-all duration-300 ${expanded ? '' : 'line-clamp-2'}`}>
              {adviceData.advice}
            </div>
            <button 
              onClick={() => setExpanded(!expanded)}
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 mt-2 inline-flex items-center transition-colors"
            >
              {expanded ? 'সংক্ষিপ্ত করুন' : 'বিস্তারিত পড়ুন'} 
              <span className={`ml-1 transition-transform ${expanded ? 'rotate-180' : ''}`}>▼</span>
            </button>
          </div>
        </div>
      )}

      {!adviceData && !loading && (
        <EmptyState 
          icon="💧" 
          title={t('nav.water')} 
          message="আপনার ফসলের জন্য সঠিক সেচ পরামর্শ এবং ৭ দিনের ক্যালেন্ডার পান" 
        />
      )}
    </div>
  );
}
