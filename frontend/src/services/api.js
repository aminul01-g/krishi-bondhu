/**
 * Central API service for KrishiBondhu.
 * All backend communication goes through this layer.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '';

function getAuthHeaders() {
  const token = localStorage.getItem('kb_auth_token');
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

async function request(method, path, { body, isForm = false, signal } = {}) {
  const url = `${API_BASE}${path}`;
  const headers = { ...getAuthHeaders() };
  if (!isForm && body) headers['Content-Type'] = 'application/json';

  const config = { method, headers, signal };
  if (body) config.body = isForm ? body : JSON.stringify(body);

  const res = await fetch(url, config);
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('kb_auth_token');
      window.dispatchEvent(new Event('kb_auth_unauthorized'));
    }

    const err = await res.json().catch(() => ({ detail: res.statusText }));
    let errorMsg = err.error || `API Error ${res.status}`;
    if (Array.isArray(err.detail)) {
      // Handle FastAPI validation errors (array of dicts)
      errorMsg = err.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
    } else if (typeof err.detail === 'string') {
      errorMsg = err.detail;
    }
    throw new Error(errorMsg);
  }

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return res.json();
  if (contentType.includes('application/pdf')) return res.blob();
  return res.text();
}

// --- Auth ---
export const register = (username, password) =>
  request('POST', `/api/auth/register`, { body: { username, password } });

export const login = (username, password) => {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);
  return request('POST', '/api/auth/token', { body: form, isForm: true });
};

export const getMe = (signal) => request('GET', '/api/auth/me', { signal });

// --- Chat ---
export const postChat = (message, lat, lon, image, signal) => {
  const form = new FormData();
  form.append('message', message);
  if (lat != null) form.append('lat', lat);
  if (lon != null) form.append('lon', lon);
  if (image) form.append('image', image);
  return request('POST', '/api/chat', { body: form, isForm: true, signal });
};

export const postUploadAudio = (file, lat, lon, image) => {
  const form = new FormData();
  form.append('file', file);
  if (lat != null) form.append('lat', lat);
  if (lon != null) form.append('lon', lon);
  if (image) form.append('image', image);
  return request('POST', '/api/upload_audio', { body: form, isForm: true });
};

export const postUploadImage = (image, lat, lon, question = '') => {
  const form = new FormData();
  form.append('image', image);
  if (lat != null) form.append('lat', lat);
  if (lon != null) form.append('lon', lon);
  form.append('question', question);
  return request('POST', '/api/upload_image', { body: form, isForm: true });
};

// --- Market ---
export const getMarketAdvice = (crop, lat, lon, signal) =>
  request('GET', `/api/market/advice?crop=${encodeURIComponent(crop)}${lat ? `&lat=${lat}&lon=${lon}` : ''}`, { signal });

export const getMarketHistory = (crop, days = 7, signal) =>
  request('GET', `/api/market/history?crop=${encodeURIComponent(crop)}&days=${days}`, { signal });

// --- Diary ---
export const postDiaryEntry = (transcript) =>
  request('POST', '/api/diary/add', { body: { transcript } });

export const getDiaryReport = (signal) =>
  request('GET', '/api/diary/report', { signal });

export const exportDiaryPdf = () =>
  request('GET', '/api/diary/export/pdf');

// --- Alerts ---
export const getDailyAlert = (crop, lat, lon, signal) =>
  request('GET', `/api/alerts/daily?crop=${encodeURIComponent(crop)}${lat ? `&lat=${lat}&lon=${lon}` : ''}`, { signal });

// --- Emergency ---
export const postDamageReport = (data) =>
  request('POST', '/api/emergency/reports', { body: data });

export const getDamageReport = (id, signal) =>
  request('GET', `/api/emergency/reports/${id}`, { signal });

export const postHelplineCall = (data) =>
  request('POST', '/api/emergency/helpline', { body: data });

// --- Soil ---
export const postSoilImage = (image, lat, lon) => {
  const form = new FormData();
  form.append('image', image);
  if (lat != null) form.append('lat', lat);
  if (lon != null) form.append('lon', lon);
  return request('POST', '/api/soil/analyze-image', { body: form, isForm: true });
};

// --- Water ---
export const postWaterAdvice = (lat, lon, crop) =>
  request('POST', '/api/water/advice', { body: { lat, lon, crop } });

// --- Finance ---
export const postSubsidySchemes = (crop, landSize) =>
  request('POST', '/api/finance/schemes', { body: { crop, land_size: landSize } });

export const getCreditReport = (signal) =>
  request('GET', '/api/finance/credit-report', { signal });

export const postInsuranceQuote = (crop, landSize) =>
  request('POST', '/api/finance/insurance-quote', { body: { crop, land_size: landSize } });

// --- Community ---
export const postCommunityQuestion = (data) =>
  request('POST', '/api/community/questions', { body: data });

export const getCommunityQuestions = (query, limit = 20, signal) =>
  request('GET', `/api/community/questions?${query ? `query=${encodeURIComponent(query)}&` : ''}limit=${limit}`, { signal });

export const postCommunityAnswer = (questionId, data) =>
  request('POST', `/api/community/questions/${questionId}/answers`, { body: data });

// --- Marketplace ---
export const getDealers = (lat, lon, signal) =>
  request('GET', `/api/marketplace/dealers?${lat ? `lat=${lat}&lon=${lon}&` : ''}limit=20`, { signal });

export const postScanProduct = (data) =>
  request('POST', '/api/marketplace/scan', { body: data });

// --- Planner ---
export const postGeneratePlan = (crop, lat, lon) =>
  request('POST', '/api/planner/generate', { body: { crop, lat, lon } });

export const getMyPlans = (signal) =>
  request('GET', '/api/planner/my-plans', { signal });

export const getYieldForecast = (crop, lat, lon, signal) =>
  request('GET', `/api/planner/forecast?crop=${encodeURIComponent(crop)}&lat=${lat}&lon=${lon}`, { signal });

// --- Traceability ---
export const postHarvestBatch = (data) =>
  request('POST', '/api/traceability/batches', { body: data });

export const getHarvestBatch = (id, signal) =>
  request('GET', `/api/traceability/batches/${id}`, { signal });

// --- Sustainability ---
export const getSustainabilityScore = (signal) =>
  request('GET', '/api/sustainability/scorecard', { signal });

export const getSustainabilityOpportunities = (signal) =>
  request('GET', '/api/sustainability/opportunities', { signal });
