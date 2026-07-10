import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEmergencyQueue } from '../hooks/useEmergencyQueue';
import { useGeolocation } from '../hooks/useGeolocation';
import { getDealers, getListings } from '../services/api';
import { Spinner, EmptyState } from '../components/shared/LoadingStates';
import {
  getCropEmoji,
  toBengaliNumerals,
  formatRelativeTimeBn,
} from '../utils/farmOptions';

/* ───────────────────────── Inline geo helpers ───────────────────────── */

// Great-circle distance between two coordinates, in kilometres.
function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius (km)
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Initial compass bearing from point 1 → point 2 (degrees, 0 = north).
function bearing(lat1, lon1, lat2, lon2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const φ1 = toRad(lat1);
  const φ2 = toRad(lat2);
  const Δλ = toRad(lon2 - lon1);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return (Math.atan2(y, x) * 180) / Math.PI;
}

function formatDistance(km) {
  if (km == null || !Number.isFinite(km)) return '—';
  if (km < 1) return `${toBengaliNumerals(Math.round(km * 1000))} মি`;
  return `${toBengaliNumerals(km.toFixed(1))} কিমি`;
}

function formatCoord(v) {
  if (v == null) return '—';
  return toBengaliNumerals(v.toFixed(4));
}

/* ───────────────────────── Quick farm tools ───────────────────────── */

const FIELD_CARDS = [
  { emoji: '💧', labelBn: 'সেচ', path: '/app/water' },
  { emoji: '🌱', labelBn: 'মাটি', path: '/app/soil' },
  { emoji: '🚨', labelBn: 'জরুরি', path: '/app/emergency', badgeKey: 'emergency' },
  { emoji: '📒', labelBn: 'ডায়েরি', path: '/app/diary' },
  { emoji: '📅', labelBn: 'পরিকল্পনা', path: '/app/planner' },
  { emoji: '♻️', labelBn: 'টেকসই', path: '/app/sustainability' },
];

/* ───────────────────────── Radial coordinate plot ─────────────────────────
 * Places the farmer at center and nearby dealers as dots by bearing/distance.
 * Pure SVG, no map library. Only used when we have items with coordinates. */

function RadialPlot({ origin, items }) {
  const size = 240;
  const c = size / 2;
  const maxR = 96;
  const maxDist = items.reduce((m, it) => Math.max(m, it.distance || 0), 0);
  const scale = maxDist > 0 ? maxR / maxDist : 0;

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[260px] mx-auto" role="img"
      aria-label="আপনার অবস্থানের চারপাশে নিকটবর্তী ডিলারদের বিন্যাস">
      <circle cx={c} cy={c} r={maxR} className="fill-none stroke-border" />
      <circle cx={c} cy={c} r={maxR / 2} className="fill-none stroke-border" strokeDasharray="3 4" />
      <line x1={c} y1={c - maxR} x2={c} y2={c + maxR} className="stroke-border" strokeDasharray="2 4" />
      <line x1={c - maxR} y1={c} x2={c + maxR} y2={c} className="stroke-border" strokeDasharray="2 4" />
      <text x={c} y={c - maxR + 12} textAnchor="middle" className="fill-text-secondary" style={{ fontSize: 9 }}>
        উত্তর
      </text>
      <circle cx={c} cy={c} r={6} className="fill-primary" />
      <text x={c} y={c + 20} textAnchor="middle" className="fill-text-secondary" style={{ fontSize: 9 }}>
        আপনি
      </text>
      {items.map((it) => {
        const br = (bearing(origin.lat, origin.lon, it.location_lat, it.location_lon) + 360) % 360;
        const r = Math.max(8, (it.distance || 0) * scale);
        const rad = ((br - 90) * Math.PI) / 180; // 0° = up
        const x = c + r * Math.cos(rad);
        const y = c + r * Math.sin(rad);
        return (
          <circle key={it.id} cx={x} cy={y} r={4} className="fill-accent">
            <title>{`${it.name} — ${formatDistance(it.distance)}`}</title>
          </circle>
        );
      })}
    </svg>
  );
}

/* ───────────────────────── Real map view ─────────────────────────
 * A REAL Leaflet map loaded from CDN via the global `window.L` (see
 * index.html). We do NOT `import 'leaflet'` because that would be an
 * unresolved bare import under the offline sandbox. If the CDN failed to
 * load (`window.L` is undefined), we render a small fallback notice instead
 * of crashing. Only dealers (which carry GPS) are plotted; listings have no
 * coordinates so they remain a side list. */

function DealerMap({ origin, dealers }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [mapFailed, setMapFailed] = useState(false);

  // Initialise the map ONCE. The Leaflet global is loaded by a <script> tag in
  // index.html (render-blocking, in <head>), so it is available by the time
  // this component mounts. We guard anyway in case the CDN was unreachable.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const L = typeof window !== 'undefined' ? window.L : undefined;
    if (!containerRef.current) return;
    if (!L) {
      setMapFailed(true);
      return;
    }
    if (mapRef.current) return; // already created

    const map = L.map(containerRef.current, {
      center: [origin.lat, origin.lon],
      zoom: 12,
      scrollWheelZoom: false,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);
    mapRef.current = map;

    // The container may have had zero size at mount; let the browser lay it out.
    const t = setTimeout(() => map.invalidateSize(), 0);

    return () => {
      clearTimeout(t);
      map.remove();
      mapRef.current = null;
    };
  }, [origin.lat, origin.lon]);

  // (Re)draw markers whenever the origin or dealer list changes.
  useEffect(() => {
    const L = typeof window !== 'undefined' ? window.L : undefined;
    const map = mapRef.current;
    if (!map || !L) return;

    // Recenter on the farmer when the origin changes (e.g. manual re-entry).
    map.setView([origin.lat, origin.lon], 12);

    if (map._kbMarkerLayer) map.removeLayer(map._kbMarkerLayer);
    const layer = L.layerGroup().addTo(map);
    map._kbMarkerLayer = layer;

    // Farmer marker.
    L.marker([origin.lat, origin.lon], { title: 'আপনার অবস্থান' })
      .addTo(layer)
      .bindPopup('আপনার অবস্থান');

    // One marker per dealer that actually has valid numeric coordinates.
    dealers.forEach((d) => {
      const la = Number(d.location_lat);
      const lo = Number(d.location_lon);
      if (!Number.isFinite(la) || !Number.isFinite(lo)) return;
      const name = (d.name || 'ডিলার').replace(/</g, '&lt;');
      L.marker([la, lo])
        .addTo(layer)
        .bindPopup(`<strong>${name}</strong><br/>দূরত্ব: ${formatDistance(d.distance)}`);
    });
  }, [origin.lat, origin.lon, dealers]);

  if (mapFailed) {
    return (
      <div className="bg-surface rounded-card border border-border p-4 shadow-card">
        <p className="text-sm text-text-secondary">
          মানচিত্র লোড করা যায়নি (ইন্টারনেট সংযোগ নেই)। নিকটবর্তী ডিলারদের তালিকা নিচে দেখুন।
        </p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-[320px] rounded-card border border-border shadow-card z-0"
      role="img"
      aria-label="নিকটবর্তী ডিলারদের মানচিত্র"
    />
  );
}

/* ───────────────────────── Row components ───────────────────────── */

function DealerRow({ dealer }) {
  return (
    <li className="flex items-center gap-3 bg-surface rounded-card border border-border px-4 py-3 shadow-card">
      <div className="flex flex-col items-center justify-center min-w-[66px]">
        <span className="text-sm font-bold text-primary">{formatDistance(dealer.distance)}</span>
        <span className="text-[10px] text-text-secondary">দূরত্ব</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold text-text-primary truncate">{dealer.name}</h4>
          {dealer.is_verified && (
            <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-pill whitespace-nowrap">
              যাচাইকৃত
            </span>
          )}
        </div>
        <p className="text-xs text-text-secondary truncate">📞 {dealer.phone_number || '—'}</p>
      </div>
    </li>
  );
}

function ListingRow({ listing, distance }) {
  return (
    <li className="flex items-center gap-3 bg-surface rounded-card border border-border px-4 py-3 shadow-card">
      <span className="text-2xl" aria-hidden="true">{getCropEmoji(listing.crop)}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold text-text-primary truncate">{listing.crop}</h4>
          {distance != null && (
            <span className="text-[10px] bg-accent/10 text-soil px-1.5 py-0.5 rounded-pill whitespace-nowrap">
              {formatDistance(distance)}
            </span>
          )}
        </div>
        <p className="text-xs text-text-secondary truncate">
          {toBengaliNumerals(listing.quantity_kg)} কেজি · ৳{toBengaliNumerals(listing.price_per_kg)}
          {listing.district ? ` · ${listing.district}` : ''}
        </p>
        <p className="text-[11px] text-text-secondary truncate">
          {listing.seller_name}
          {listing.posted_date ? ` · ${formatRelativeTimeBn(listing.posted_date)}` : ''}
        </p>
      </div>
    </li>
  );
}

/* ───────────────────────── Manual coordinate entry ───────────────────────── */

function ManualCoordForm({ lat, lon, setLat, setLon, onSubmit, onRetryGps, retryLabel }) {
  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card">
      <p className="text-sm text-text-secondary mb-3">
        আপনার অবস্থানের অক্ষাংশ (latitude) ও দ্রাঘিমাংশ (longitude) লিখুন।
        উদাহরণ: ২৩.৭৫, ৯০.৩৮
      </p>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs text-text-secondary">অক্ষাংশ (Lat)</span>
          <input
            type="number" step="any" inputMode="decimal" value={lat}
            onChange={(e) => setLat(e.target.value)}
            placeholder="23.7500"
            className="mt-1 w-full rounded-btn border border-border bg-bg px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </label>
        <label className="block">
          <span className="text-xs text-text-secondary">দ্রাঘিমাংশ (Lon)</span>
          <input
            type="number" step="any" inputMode="decimal" value={lon}
            onChange={(e) => setLon(e.target.value)}
            placeholder="90.3800"
            className="mt-1 w-full rounded-btn border border-border bg-bg px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </label>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button" onClick={onSubmit}
          className="rounded-btn bg-primary px-4 py-2 text-sm font-semibold text-white shadow-card hover:bg-primary-light active:scale-95 transition"
        >
          অবস্থান সেট করুন
        </button>
        {onRetryGps && (
          <button
            type="button" onClick={onRetryGps}
            className="text-sm text-primary font-medium underline-offset-2 hover:underline"
          >
            {retryLabel || 'GPS আবার চেষ্টা করুন'}
          </button>
        )}
      </div>
    </div>
  );
}

/* ───────────────────────── Page ───────────────────────── */

/**
 * FieldHubPage — a spatial "command center" for the farmer's location.
 *
 * Shows nearby agro-input dealers (which carry GPS coordinates in the API) and
 * marketplace listings, sorted by straight-line distance via the haversine
 * formula. Dealers are plotted on a REAL Leaflet map (loaded from CDN as the
 * global `window.L`; see index.html) as the primary spatial view, with the
 * haversine dealer list and SVG radial plot kept as complementary UI.
 * Listings currently returned by the API are NOT geo-tagged, so they are shown
 * as a recency-sorted "recent" list with an honest note; if the backend later
 * attaches coordinates they will automatically join the spatial view.
 */
export default function FieldHubPage() {
  const navigate = useNavigate();
  const { pendingCount } = useEmergencyQueue();

  // Auto GPS via the existing hook (requests permission on mount).
  const { lat: geoLat, lon: geoLon, error: geoError, requestLocation } = useGeolocation();

  const [manualLat, setManualLat] = useState('');
  const [manualLon, setManualLon] = useState('');
  const [manualActive, setManualActive] = useState(false);
  const [origin, setOrigin] = useState(null); // { lat, lon }

  const [dealers, setDealers] = useState(null);
  const [listings, setListings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Keep GPS as the origin until the farmer opts into manual entry.
  useEffect(() => {
    if (!manualActive && geoLat != null && geoLon != null) {
      setOrigin({ lat: geoLat, lon: geoLon });
    }
  }, [geoLat, geoLon, manualActive]);

  // Fetch nearby dealers + listings whenever the origin changes.
  useEffect(() => {
    if (!origin) return;
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      getDealers(origin.lat, origin.lon, ctrl.signal),
      getListings({}, ctrl.signal),
    ])
      .then(([d, l]) => {
        setDealers(Array.isArray(d) ? d : []);
        setListings(Array.isArray(l) ? l : []);
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message || 'তথ্য লোড করা যায়নি');
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [origin]);

  const applyManual = useCallback(() => {
    const la = parseFloat(manualLat);
    const lo = parseFloat(manualLon);
    if (Number.isFinite(la) && Number.isFinite(lo)) {
      setManualActive(true);
      setOrigin({ lat: la, lon: lo });
    }
  }, [manualLat, manualLon]);

  const retryGps = useCallback(() => {
    setManualActive(false);
    setManualLat('');
    setManualLon('');
    setOrigin(null);
    requestLocation();
  }, [requestLocation]);

  // Dealers always carry coordinates → distance-sorted spatial list.
  const dealersWithDist = useMemo(() => {
    if (!dealers || !origin) return [];
    return dealers
      .map((d) => ({
        ...d,
        distance: haversine(origin.lat, origin.lon, d.location_lat, d.location_lon),
      }))
      .sort((a, b) => a.distance - b.distance);
  }, [dealers, origin]);

  // Listings: geo-tagged ones get distance-sorted; the rest fall back to recency.
  const { geoListings, plainListings } = useMemo(() => {
    if (!listings) return { geoListings: [], plainListings: [] };
    const geo = [];
    const plain = [];
    for (const l of listings) {
      if (origin && l.location_lat != null && l.location_lon != null) {
        geo.push({
          ...l,
          distance: haversine(origin.lat, origin.lon, l.location_lat, l.location_lon),
        });
      } else {
        plain.push(l);
      }
    }
    geo.sort((a, b) => a.distance - b.distance);
    plain.sort(
      (a, b) => new Date(b.posted_date || 0).getTime() - new Date(a.posted_date || 0).getTime()
    );
    return { geoListings: geo, plainListings: plain };
  }, [listings, origin]);

  const hasData = dealersWithDist.length > 0 || geoListings.length > 0 || plainListings.length > 0;

  /* ---------- Location gate (no coordinates yet) ---------- */
  if (!origin) {
    const denied = Boolean(geoError);
    return (
      <div className="min-h-[calc(100vh-8rem)] flex flex-col gap-4">
        <div className="mb-1">
          <h1 className="text-xl font-bold text-text-primary">ফিল্ড হাব</h1>
          <p className="text-sm text-text-secondary">
            আপনার অবস্থান জানতে পারলে নিকটবর্তী ডিলার ও বিজ্ঞপ্তি দেখাবে
          </p>
        </div>

        {denied ? (
          <div className="bg-danger/5 border border-danger/30 rounded-card p-4">
            <p className="text-sm font-medium text-danger mb-1">অবস্থানের অনুমতি মেলেনি</p>
            <p className="text-xs text-text-secondary">{geoError}</p>
          </div>
        ) : (
          <div className="flex items-center gap-3 bg-surface rounded-card border border-border p-4 shadow-card">
            <Spinner size="sm" className="text-primary" />
            <p className="text-sm text-text-secondary">আপনার অবস্থান খোঁজা হচ্ছে…</p>
          </div>
        )}

        <ManualCoordForm
          lat={manualLat}
          lon={manualLon}
          setLat={setManualLat}
          setLon={setManualLon}
          onSubmit={applyManual}
          onRetryGps={denied ? retryGps : undefined}
        />
      </div>
    );
  }

  /* ---------- Command center (origin known) ---------- */
  return (
    <div className="min-h-[calc(100vh-8rem)] flex flex-col gap-6">
      {/* Summary header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary">ফিল্ড হাব</h1>
          <p className="text-sm text-text-secondary">
            আপনার অবস্থান: {formatCoord(origin.lat)}, {formatCoord(origin.lon)}
            {manualActive && <span className="ml-1 text-[11px]">(ম্যানুয়াল)</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <div className="flex-1 sm:flex-none bg-surface border border-border rounded-card px-4 py-2 text-center shadow-card">
            <div className="text-lg font-bold text-primary">
              {toBengaliNumerals(dealersWithDist.length)}
            </div>
            <div className="text-[11px] text-text-secondary">নিকটবর্তী ডিলার</div>
          </div>
          <div className="flex-1 sm:flex-none bg-surface border border-border rounded-card px-4 py-2 text-center shadow-card">
            <div className="text-lg font-bold text-accent">
              {toBengaliNumerals(geoListings.length + plainListings.length)}
            </div>
            <div className="text-[11px] text-text-secondary">বিজ্ঞপ্তি</div>
          </div>
        </div>
      </div>

      {/* Permission / location controls */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button" onClick={retryGps}
          className="text-sm text-primary font-medium underline-offset-2 hover:underline"
        >
          অবস্থান পুনরায় চেষ্টা
        </button>
        <button
          type="button"
          onClick={() => setManualActive(true)}
          className="text-sm text-text-secondary font-medium underline-offset-2 hover:underline"
        >
          অবস্থান হাতে লিখুন
        </button>
        {manualActive && (
          <ManualCoordForm
            lat={manualLat}
            lon={manualLon}
            setLat={setManualLat}
            setLon={setManualLon}
            onSubmit={applyManual}
          />
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-danger/5 border border-danger/30 rounded-card p-4">
          <p className="text-sm font-medium text-danger mb-1">তথ্য লোড করা যায়নি</p>
          <p className="text-xs text-text-secondary">{error}</p>
          <button
            type="button"
            onClick={() => setOrigin({ ...origin })}
            className="mt-2 text-sm text-primary font-medium underline-offset-2 hover:underline"
          >
            আবার চেষ্টা করুন
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center gap-3 bg-surface rounded-card border border-border p-4 shadow-card">
          <Spinner size="sm" className="text-primary" />
          <p className="text-sm text-text-secondary">নিকটবর্তী ডিলার ও বিজ্ঞপ্তি লোড হচ্ছে…</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !hasData && (
        <EmptyState
          icon="🗺️"
          title="কাছে কিছু পাওয়া যায়নি"
          message="এই অবস্থানের আশেপাশে কোনো ডিলার বা বিজ্ঞপ্তি নেই। অন্য অবস্থান চেষ্টা করুন।"
        />
      )}

      {/* Spatial view */}
      {!loading && !error && hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Primary spatial view: real Leaflet map */}
          {dealersWithDist.length > 0 && (
            <section className="lg:col-span-3 flex flex-col gap-2">
              <h2 className="text-base font-semibold text-text-primary">মানচিত্র</h2>
              <DealerMap origin={origin} dealers={dealersWithDist} />
            </section>
          )}

          {/* Dealer spatial list + radial plot */}
          <section className="lg:col-span-2 flex flex-col gap-3">
            <h2 className="text-base font-semibold text-text-primary">
              নিকটবর্তী ডিলার ({toBengaliNumerals(dealersWithDist.length)})
            </h2>
            {dealersWithDist.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {dealersWithDist.map((d) => (
                  <DealerRow key={d.id} dealer={d} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-secondary">এই অবস্থানের কাছে কোনো ডিলার নেই।</p>
            )}
          </section>

          {/* Radial plot sidebar */}
          <aside className="flex flex-col gap-2">
            <h2 className="text-base font-semibold text-text-primary">স্থানিক দৃশ্য</h2>
            {dealersWithDist.length > 0 ? (
              <div className="bg-surface rounded-card border border-border p-3 shadow-card">
                <RadialPlot origin={origin} items={dealersWithDist} />
                <p className="mt-2 text-[11px] text-text-secondary text-center">
                  কেন্দ্রে আপনি, বিন্দুগুলো নিকটবর্তী ডিলার (দূরত্ব ও দিক অনুযায়ী)।
                </p>
              </div>
            ) : (
              <div className="bg-surface rounded-card border border-border p-4 shadow-card text-center">
                <p className="text-sm text-text-secondary">দৃশ্যের জন্য ডিলারের প্রয়োজন।</p>
              </div>
            )}
          </aside>

          {/* Listings */}
          <section className="lg:col-span-3 flex flex-col gap-3">
            {geoListings.length > 0 && (
              <>
                <h2 className="text-base font-semibold text-text-primary">
                  নিকটবর্তী বিজ্ঞপ্তি ({toBengaliNumerals(geoListings.length)})
                </h2>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {geoListings.map((l) => (
                    <ListingRow key={l.id} listing={l} distance={l.distance} />
                  ))}
                </ul>
              </>
            )}

            {plainListings.length > 0 && (
              <>
                <h2 className="text-base font-semibold text-text-primary">
                  সাম্প্রতিক বিজ্ঞপ্তি ({toBengaliNumerals(plainListings.length)})
                </h2>
                <p className="text-[11px] text-text-secondary">
                  এই বিজ্ঞপ্তিগুলোতে GPS অবস্থান নেই, তাই দূরত্ব অনুযায়ী সাজানো যায়নি।
                </p>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {plainListings.map((l) => (
                    <ListingRow key={l.id} listing={l} distance={null} />
                  ))}
                </ul>
              </>
            )}
          </section>
        </div>
      )}

      {/* Quick farm tools (preserves FieldHub navigation) */}
      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-text-primary">দ্রুত টুল</h2>
        <div className="grid grid-cols-3 gap-3">
          {FIELD_CARDS.map((card) => {
            const badge =
              card.badgeKey === 'emergency' && pendingCount > 0 ? pendingCount : null;
            return (
              <button
                key={card.path}
                onClick={() => navigate(card.path)}
                className="relative flex flex-col items-center justify-center gap-2
                           bg-surface rounded-card px-3 py-5 shadow-card
                           hover:bg-primary/5 active:scale-95
                           transition-all duration-150 border border-border
                           focus:outline-none focus:ring-2 focus:ring-primary/40"
                aria-label={card.labelBn}
              >
                {badge != null && (
                  <span
                    className="absolute top-1.5 right-1.5 min-w-[20px] h-[20px] px-1
                               bg-danger text-white text-[11px] font-bold rounded-full
                               flex items-center justify-center shadow-card"
                    aria-label={`${badge} টি স্থগিত রিপোর্ট`}
                  >
                    {badge}
                  </span>
                )}
                <span style={{ fontSize: '2rem', lineHeight: 1 }} aria-hidden="true">
                  {card.emoji}
                </span>
                <span className="text-sm font-semibold text-text-primary text-center leading-snug">
                  {card.labelBn}
                </span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
