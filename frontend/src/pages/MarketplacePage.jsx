import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  getListings,
  postListing,
  postListingContact,
  getMyListings,
  deleteListing,
  getFarmerProfile,
} from '../services/api';
import { useApi } from '../hooks/useApi';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';
import {
  COMMON_CROPS,
  DISTRICTS,
  getCropEmoji,
  toBengaliNumerals,
  formatRelativeTimeBn,
} from '../utils/farmOptions';

const MK = 'marketplace';

// Quantity slider bounds (kg)
const QTY_MIN = 1;
const QTY_MAX = 5000;
const QTY_STEP = 1;

export default function MarketplacePage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState('browse'); // 'browse' | 'post' | 'mine'

  return (
    <div className="space-y-4">
      {/* Tab switcher */}
      <div className="flex gap-2">
        {[
          ['browse', `🛒 ${t(`${MK}.tab_browse`)}`],
          ['post', `📢 ${t(`${MK}.tab_post`)}`],
          ['mine', `📋 ${t(`${MK}.tab_mine`)}`],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 py-2.5 rounded-btn text-xs sm:text-sm font-medium transition-all whitespace-nowrap
              ${tab === key
                ? 'bg-primary text-white shadow-card'
                : 'bg-surface border border-border text-text-secondary hover:border-primary'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'browse' && <BrowseTab onGoPost={() => setTab('post')} />}
      {tab === 'post' && <PostTab onDone={() => setTab('mine')} />}
      {tab === 'mine' && <MineTab onGoPost={() => setTab('post')} />}
    </div>
  );
}

/* ───────────────────────── Tab 1: Browse listings ───────────────────────── */

function BrowseTab({ onGoPost }) {
  const { t } = useTranslation();
  const [crop, setCrop] = useState('');
  const [district, setDistrict] = useState('');
  const [contacting, setContacting] = useState(null); // listing id being contacted
  const [expanded, setExpanded] = useState(null);     // listing id whose details are open

  const { data: listings, loading, error } = useApi(
    (signal) => getListings({ crop: crop || undefined, district: district || undefined, type: 'sell' }, signal),
    [crop, district],
  );

  const handleCall = async (listing) => {
    setContacting(listing.id);
    try {
      const { phone } = await postListingContact(listing.id);
      if (phone) {
        window.location.href = `tel:${phone}`;
      } else {
        alert(t(`${MK}.call_failed`));
      }
    } catch (err) {
      alert(err.message || t(`${MK}.call_failed`));
    } finally {
      setContacting(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filter row: crop chips + district dropdown */}
      <div className="card-elevated space-y-3">
        <div className="flex flex-wrap gap-1.5">
          <FilterChip active={!crop} onClick={() => setCrop('')}>
            {t(`${MK}.filter_all_crops`)}
          </FilterChip>
          {COMMON_CROPS.map((c) => (
            <FilterChip key={c} active={crop === c} onClick={() => setCrop(c)}>
              {getCropEmoji(c)} {c}
            </FilterChip>
          ))}
        </div>
        <select
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className="input-field !py-2"
        >
          <option value="">{t(`${MK}.filter_all_districts`)}</option>
          {DISTRICTS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-danger-light text-danger p-3 rounded-btn text-sm text-center">
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card"><Skeleton lines={3} /></div>
          ))}
        </div>
      ) : (Array.isArray(listings) && listings.length > 0) ? (
        <div className="space-y-3">
          {listings.map((l, i) => (
            <ListingCard
              key={l.id || i}
              listing={l}
              onCall={handleCall}
              contacting={contacting === l.id}
              expanded={expanded === l.id}
              onToggleDetails={() => setExpanded(expanded === l.id ? null : l.id)}
            />
          ))}
        </div>
      ) : (
        <>
          <EmptyState
            icon="🛒"
            title={t(`${MK}.no_listings`)}
            message={t(`${MK}.no_listings_msg`)}
          />
          <button onClick={onGoPost} className="btn-primary w-full">
            {t(`${MK}.tab_post`)}
          </button>
        </>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-pill text-sm font-medium border transition-all
        ${active
          ? 'bg-primary text-white border-primary shadow-card'
          : 'bg-surface text-text-primary border-border hover:border-primary'}`}
    >
      {children}
    </button>
  );
}

function ListingCard({ listing, onCall, contacting, expanded, onToggleDetails }) {
  const { t } = useTranslation();
  const location = [listing.district, listing.upazila].filter(Boolean).join(', ');

  return (
    <div className="card space-y-3 hover:shadow-elevated transition-shadow">
      {/* Header: crop + quantity badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-3xl">{getCropEmoji(listing.crop)}</span>
          <div>
            <h4 className="text-lg font-bold text-text-primary leading-tight">{listing.crop}</h4>
            <p className="text-xs text-text-secondary">{listing.seller_name}</p>
          </div>
        </div>
        <span className="badge-success text-xs whitespace-nowrap shrink-0">
          {toBengaliNumerals(listing.quantity_kg)} কেজি
        </span>
      </div>

      {/* Price */}
      <p className="text-2xl font-bold text-primary">
        ৳{toBengaliNumerals(listing.price_per_kg)}
        <span className="text-sm font-medium text-text-secondary">{t(`${MK}.per_kg`)}</span>
      </p>

      {/* Location + posted */}
      <div className="flex flex-col gap-1 text-sm text-text-secondary">
        <p>📍 {location || '—'}</p>
        {listing.posted_date && <p>🕒 {formatRelativeTimeBn(listing.posted_date)}</p>}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="bg-bg rounded-btn p-3 space-y-2 text-sm">
          {listing.description ? (
            <p className="text-text-primary whitespace-pre-wrap">{listing.description}</p>
          ) : (
            <p className="text-text-secondary italic">{listing.title}</p>
          )}
          <p className="text-text-secondary">
            📞 <span dir="ltr">{listing.phone_number || '—'}</span>
          </p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => onCall(listing)}
          disabled={contacting}
          className="btn-primary flex-1 flex items-center justify-center gap-1.5 !py-2.5"
        >
          {contacting ? <Spinner size="sm" /> : '📞'}
          {t(`${MK}.call`)}
        </button>
        <button onClick={onToggleDetails} className="btn-outline !py-2.5 px-4">
          {expanded ? t(`${MK}.hide`) : t(`${MK}.details`)}
        </button>
      </div>
    </div>
  );
}

/* ───────────────────────── Tab 2: Post an ad ───────────────────────── */

function PostTab({ onDone }) {
  const { t } = useTranslation();
  const [crop, setCrop] = useState('');
  const [quantity, setQuantity] = useState(100);
  const [price, setPrice] = useState('');
  const [description, setDescription] = useState('');
  const [district, setDistrict] = useState('');
  const [upazila, setUpazila] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Pre-fill district + upazila from the farmer's profile when available.
  useEffect(() => {
    const ctrl = new AbortController();
    getFarmerProfile(ctrl.signal)
      .then((p) => {
        if (p && Object.keys(p).length > 0) {
          if (p.district) setDistrict(p.district);
          if (p.upazila) setUpazila(p.upazila);
        }
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!crop) { setError(t('onboarding.crops_required')); return; }
    if (!price || Number(price) <= 0) { setError(t(`${MK}.field_price`)); return; }
    setSubmitting(true);
    try {
      await postListing({
        crop,
        quantity_kg: Number(quantity),
        price_per_kg: Number(price),
        description: description.trim() || null,
        district: district || null,
        upazila: upazila.trim() || null,
        type: 'sell',
      });
      setSuccess(true);
    } catch (err) {
      setError(err.message || t('common.error'));
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="card-elevated flex flex-col items-center text-center py-10 space-y-4">
        <div className="text-5xl">✅</div>
        <h3 className="text-lg font-bold text-text-primary">{t(`${MK}.success`)}</h3>
        <p className="text-sm text-text-secondary">{t(`${MK}.no_mine_msg`)}</p>
        <div className="grid grid-cols-1 gap-2 w-full max-w-xs">
          <button onClick={onDone} className="btn-primary !py-2.5">
            {t(`${MK}.view_mine`)}
          </button>
          <button
            onClick={() => {
              setSuccess(false);
              setCrop('');
              setPrice('');
              setDescription('');
            }}
            className="btn-outline !py-2.5"
          >
            {t(`${MK}.post_another`)}
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card-elevated space-y-5">
      {/* Crop selector (chips) */}
      <div>
        <label className="block text-sm font-medium text-text-primary mb-2">
          {t(`${MK}.field_crop`)} *
        </label>
        <div className="flex flex-wrap gap-2">
          {COMMON_CROPS.map((c) => {
            const selected = crop === c;
            return (
              <button
                key={c}
                type="button"
                onClick={() => setCrop(selected ? '' : c)}
                className={`px-3.5 py-1.5 rounded-pill text-sm font-medium border transition-all
                  ${selected
                    ? 'bg-primary text-white border-primary shadow-card'
                    : 'bg-surface text-text-primary border-border hover:border-primary'}`}
              >
                {getCropEmoji(c)} {c}
              </button>
            );
          })}
        </div>
      </div>

      {/* Quantity slider */}
      <div>
        <div className="flex items-baseline justify-between mb-1">
          <label className="block text-sm font-medium text-text-primary">{t(`${MK}.field_quantity`)}</label>
          <span className="text-sm font-semibold text-primary">
            {toBengaliNumerals(quantity)} কেজি
          </span>
        </div>
        <input
          type="range"
          min={QTY_MIN}
          max={QTY_MAX}
          step={QTY_STEP}
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          className="w-full accent-primary"
        />
        <div className="flex justify-between text-xs text-text-secondary mt-1">
          <span>{toBengaliNumerals(QTY_MIN)}</span>
          <span>{toBengaliNumerals(QTY_MAX)}</span>
        </div>
      </div>

      {/* Price per kg */}
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t(`${MK}.field_price`)} *</label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary font-medium">৳</span>
          <input
            type="number"
            inputMode="decimal"
            min="0"
            step="any"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="৪৫"
            className="input-field !pl-7"
            required
          />
        </div>
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t(`${MK}.field_description`)}</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t(`${MK}.field_description_placeholder`)}
          className="input-field min-h-[80px] resize-none"
          rows={3}
        />
      </div>

      {/* District + Upazila */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-text-primary mb-1">{t(`${MK}.field_district`)}</label>
          <select
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            className="input-field"
          >
            <option value="">{t('onboarding.district_placeholder')}</option>
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-text-primary mb-1">{t(`${MK}.field_upazila`)}</label>
          <input
            type="text"
            value={upazila}
            onChange={(e) => setUpazila(e.target.value)}
            placeholder={t(`${MK}.field_upazila_placeholder`)}
            className="input-field"
          />
        </div>
      </div>

      {error && (
        <div className="bg-danger-light text-danger text-sm p-3 rounded-btn text-center">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {submitting && <Spinner size="sm" />}
        {submitting ? t(`${MK}.posting`) : t(`${MK}.submit`)}
      </button>
    </form>
  );
}

/* ───────────────────────── Tab 3: My listings ───────────────────────── */

function MineTab({ onGoPost }) {
  const { t } = useTranslation();
  const { data: listings, loading, error, refetch } = useApi(
    (signal) => getMyListings(signal), [],
  );
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (id) => {
    if (!window.confirm(t(`${MK}.delete`) + '?')) return;
    setDeleting(id);
    try {
      await deleteListing(id);
      await refetch();
    } catch (err) {
      alert(err.message || t('common.error'));
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="card"><Skeleton lines={2} /></div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-danger-light text-danger p-3 rounded-btn text-sm text-center">
        ⚠️ {error}
      </div>
    );
  }

  const list = Array.isArray(listings) ? listings : [];

  if (list.length === 0) {
    return (
      <>
        <EmptyState icon="📋" title={t(`${MK}.no_mine`)} message={t(`${MK}.no_mine_msg`)} />
        <button onClick={onGoPost} className="btn-primary w-full">
          {t(`${MK}.tab_post`)}
        </button>
      </>
    );
  }

  return (
    <div className="space-y-3">
      {list.map((l, i) => (
        <div key={l.id || i} className="card space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{getCropEmoji(l.crop)}</span>
              <div>
                <h4 className="text-base font-bold text-text-primary leading-tight">{l.crop}</h4>
                <p className="text-xs text-text-secondary">{formatRelativeTimeBn(l.posted_date)}</p>
              </div>
            </div>
            {!l.is_active && <span className="badge-warning text-xs whitespace-nowrap">{t(`${MK}.inactive_badge`)}</span>}
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <span className="text-primary font-bold">
              ৳{toBengaliNumerals(l.price_per_kg)}
              <span className="text-text-secondary font-normal">{t(`${MK}.per_kg`)}</span>
            </span>
            <span className="text-text-secondary">{toBengaliNumerals(l.quantity_kg)} কেজি</span>
            <span className="text-text-secondary">
              📍 {[l.district, l.upazila].filter(Boolean).join(', ') || '—'}
            </span>
          </div>

          <div className="text-sm text-text-secondary">
            📞 <span className="font-medium text-text-primary" dir="ltr">{l.phone_number || '—'}</span>
          </div>

          <button
            onClick={() => handleDelete(l.id)}
            disabled={deleting === l.id}
            className="btn-outline w-full !py-2 text-danger border-danger/40 hover:bg-danger-light flex items-center justify-center gap-1.5"
          >
            {deleting === l.id ? <Spinner size="sm" /> : '🗑️'}
            {t(`${MK}.delete`)}
          </button>
        </div>
      ))}
    </div>
  );
}
