import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getFarmerProfile, upsertFarmerProfile } from '../services/api';
import { Spinner, LoadingScreen } from '../components/shared/LoadingStates';
import {
  DISTRICTS, COMMON_CROPS, EXPERIENCE_OPTIONS,
  LAND_MIN, LAND_MAX, LAND_STEP, toBengaliNumerals,
} from '../utils/farmOptions';

/**
 * ProfileEditPage
 * Same two sections as onboarding steps 2 + 3, pre-filled from the existing
 * farmer profile. Saves via upsert (POST /api/profile) and returns to the
 * profile hub.
 */
export default function ProfileEditPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // ── Location ──
  const [district, setDistrict] = useState('');
  const [upazila, setUpazila] = useState('');
  const [phone, setPhone] = useState('');

  // ── Farm details ──
  const [crops, setCrops] = useState([]);
  const [landArea, setLandArea] = useState(5);
  const [experience, setExperience] = useState('');

  const [loadingProfile, setLoadingProfile] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        const data = await getFarmerProfile(ctrl.signal);
        if (data && Object.keys(data).length > 0) {
          setDistrict(data.district || '');
          setUpazila(data.upazila || '');
          setPhone(data.phone_number || '');
          setCrops(Array.isArray(data.crops) ? data.crops : []);
          if (typeof data.land_area_bigha === 'number') setLandArea(data.land_area_bigha);
          if (data.farming_experience_years != null) setExperience(String(data.farming_experience_years));
        }
      } catch (err) {
        if (err.name !== 'AbortError') setError(err.message || 'Failed to load profile');
      } finally {
        setLoadingProfile(false);
      }
    })();
    return () => ctrl.abort();
  }, []);

  const toggleCrop = (crop) => {
    setSuccess(false);
    setError('');
    setCrops((prev) =>
      prev.includes(crop) ? prev.filter((c) => c !== crop) : [...prev, crop]
    );
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    if (crops.length === 0) { setError(t('onboarding.crops_required')); return; }
    setSaving(true);
    try {
      await upsertFarmerProfile({
        district: district || null,
        upazila: upazila.trim() || null,
        crops,
        land_area_bigha: Number(landArea),
        farming_experience_years: experience ? Number(experience) : null,
        phone_number: phone.trim() || null,
      });
      setSuccess(true);
      setTimeout(() => navigate('/app/profile', { replace: true }), 600);
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setSaving(false);
    }
  };

  if (loadingProfile) return <LoadingScreen message={t('common.loading')} />;

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/app/profile')}
          className="w-9 h-9 rounded-full bg-surface border border-border flex items-center justify-center text-text-primary hover:bg-primary/5"
          aria-label={t('common.back')}
        >
          ←
        </button>
        <h1 className="text-lg font-bold text-text-primary">প্রোফাইল সম্পাদনা</h1>
      </div>

      <form onSubmit={handleSave} className="flex flex-col gap-4">
        {/* ── Section: Location ── */}
        <section className="bg-surface rounded-card shadow-card border border-border p-4 space-y-4">
          <h2 className="text-sm font-bold text-primary-dark">{t('onboarding.step_location_title')}</h2>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              {t('onboarding.district_label')}
            </label>
            <select
              value={district}
              onChange={(e) => { setDistrict(e.target.value); setSuccess(false); }}
              className="input-field"
            >
              <option value="">{t('onboarding.district_placeholder')}</option>
              {DISTRICTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              {t('onboarding.upazila_label')}
            </label>
            <input
              type="text"
              value={upazila}
              onChange={(e) => { setUpazila(e.target.value); setSuccess(false); }}
              placeholder="আপনার উপজেলার নাম লিখুন"
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              {t('onboarding.phone_label')}
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => { setPhone(e.target.value); setSuccess(false); }}
              placeholder="আপনার ফোন নম্বর"
              className="input-field"
              autoComplete="tel"
            />
          </div>
        </section>

        {/* ── Section: Farm details ── */}
        <section className="bg-surface rounded-card shadow-card border border-border p-4 space-y-5">
          <h2 className="text-sm font-bold text-primary-dark">{t('onboarding.step_farm_title')}</h2>

          {/* Crop chips (multi-select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              {t('onboarding.crops_label')}
            </label>
            <p className="text-xs text-text-secondary mb-2">{t('onboarding.crops_hint')}</p>
            <div className="flex flex-wrap gap-2">
              {COMMON_CROPS.map((crop) => {
                const selected = crops.includes(crop);
                return (
                  <button
                    key={crop}
                    type="button"
                    onClick={() => toggleCrop(crop)}
                    className={`px-3.5 py-1.5 rounded-pill text-sm font-medium border transition-all
                      ${selected
                        ? 'bg-primary text-white border-primary shadow-card'
                        : 'bg-surface text-text-primary border-border hover:border-primary'}`}
                  >
                    {crop}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Land area slider */}
          <div>
            <div className="flex items-baseline justify-between mb-1">
              <label className="block text-sm font-medium text-text-primary">
                {t('onboarding.land_label')}
              </label>
              <span className="text-sm font-semibold text-primary">
                {toBengaliNumerals(landArea)} {t('onboarding.land_unit')}
              </span>
            </div>
            <input
              type="range"
              min={LAND_MIN}
              max={LAND_MAX}
              step={LAND_STEP}
              value={landArea}
              onChange={(e) => { setLandArea(Number(e.target.value)); setSuccess(false); }}
              className="w-full accent-primary"
            />
          </div>

          {/* Farming experience */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              {t('onboarding.experience_label')}
            </label>
            <select
              value={experience}
              onChange={(e) => { setExperience(e.target.value); setSuccess(false); }}
              className="input-field"
            >
              <option value="">{t('onboarding.experience_placeholder')}</option>
              {EXPERIENCE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </section>

        {error && (
          <div className="bg-danger-light text-danger text-sm p-3 rounded-btn text-center">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-primary/10 text-primary text-sm p-3 rounded-btn text-center">
            ✓ সংরক্ষিত হয়েছে
          </div>
        )}

        {/* Sticky save bar */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => navigate('/app/profile')}
            className="btn-outline flex-1"
          >
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            disabled={saving}
            className="btn-primary flex-[2] flex items-center justify-center gap-2"
          >
            {saving && <Spinner size="sm" />}
            {t('common.save')}
          </button>
        </div>
      </form>
    </div>
  );
}
