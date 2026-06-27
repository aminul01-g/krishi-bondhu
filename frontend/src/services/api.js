/**
 * Central API service for KrishiBondhu.
 * All backend communication goes through this layer.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '';

function getAuthHeaders() {
  const token = localStorage.getItem('kb_auth_token');
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  // Propagate selected UI language to backend so LLMs can respect it
  const lang = localStorage.getItem('kb_lang') || 'bn';
  headers['X-KB-Lang'] = lang;
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

// --- Farmer Profile (create or update by user_id) ---
export const getFarmerProfile = (signal) =>
  request('GET', '/api/profile', { signal });

export const upsertFarmerProfile = (data) =>
  request('POST', '/api/profile', { body: data });

// --- Chat ---
export const postChat = (message, lat, lon, image, signal) => {
  const form = new FormData();
  form.append('message', message);
  if (lat != null) form.append('lat', lat);
  if (lon != null) form.append('lon', lon);
  if (image) form.append('image', image);
  return request('POST', '/api/chat', { body: form, isForm: true, signal });
};

/**
 * SSE streaming chat — calls /api/chat/stream and fires callbacks as events arrive.
 * @param {string}   message  - The user message text
 * @param {number|null} lat   - Optional latitude
 * @param {number|null} lon   - Optional longitude
 * @param {function} onChunk  - Called with each text chunk string
 * @param {function} onDone   - Called with the full reply text when stream ends
 * @param {function} onError  - Called with an error message string on failure
 * @returns {Promise<void>}
 */
export async function streamChat(message, lat, lon, onChunk, onDone, onError) {
  const formData = new FormData();
  formData.append('message', message);
  if (lat != null) formData.append('lat', lat);
  if (lon != null) formData.append('lon', lon);

  const token = localStorage.getItem('kb_auth_token');
  const lang = localStorage.getItem('kb_lang') || 'bn';
  const headers = { 'X-KB-Lang': lang };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: formData,
    });
  } catch (networkErr) {
    onError(networkErr.message);
    return;
  }

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('kb_auth_token');
      window.dispatchEvent(new Event('kb_auth_unauthorized'));
    }
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    onError(err.error || err.detail || `HTTP ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop(); // keep any incomplete event in the buffer
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'chunk') onChunk(data.text);
            else if (data.type === 'done') onDone(data.full_text);
            else if (data.type === 'error') onError(data.message);
            // 'thinking' events are intentionally ignored here (UI handles loading state)
          } catch (_) {
            // Malformed JSON in a single event — skip gracefully
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

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

// --- Dashboard ---
export const getDashboardSummary = (lat, lon, crops, signal) => {
  let query = '';
  if (lat != null && lon != null) query += `lat=${lat}&lon=${lon}&`;
  if (crops) query += `crops=${encodeURIComponent(crops)}`;
  return request('GET', `/api/dashboard/summary?${query}`, { signal });
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

export const getDiaryEntries = (page = 1, signal) =>
  request('GET', `/api/diary/entries?page=${page}&per_page=20`, { signal });

export const deleteDiaryEntry = (id) =>
  request('DELETE', `/api/diary/entries/${id}`);

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

export const postSoilAnalysis = (data) =>
  request('POST', '/api/soil/analyze', { body: data });

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

export const getListings = ({ crop, district, type } = {}, signal) => {
  const params = new URLSearchParams();
  if (crop) params.set('crop', crop);
  if (district) params.set('district', district);
  if (type) params.set('type', type);
  const qs = params.toString();
  return request('GET', `/api/marketplace/listings${qs ? `?${qs}` : ''}`, { signal });
};

export const postListing = (data) =>
  request('POST', '/api/marketplace/listings', { body: data });

export const postListingContact = (id) =>
  request('POST', `/api/marketplace/listings/${id}/contact`);

export const getMyListings = (signal) =>
  request('GET', '/api/marketplace/listings/mine', { signal });

export const deleteListing = (id) =>
  request('DELETE', `/api/marketplace/listings/${id}`);

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
