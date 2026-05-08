/**
 * Central API Service — All backend API calls in one place.
 * Injects auth headers, handles errors uniformly.
 */

import { API_BASE } from '../api';

// ---------------------------------------------------------------------------
// Core request helpers
// ---------------------------------------------------------------------------

const getAuthHeaders = () => {
  const token = localStorage.getItem('krishi_auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const parseResponse = async (response) => {
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { message: text };
  }
  if (!response.ok) {
    const error = data.error || data.detail || data.message || response.statusText || 'API request failed';
    throw new Error(error);
  }
  return data;
};

export const get = async (endpoint) => {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { ...getAuthHeaders() },
  });
  return parseResponse(response);
};

export const post = async (endpoint, data) => {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  return parseResponse(response);
};

export const postForm = async (endpoint, formData) => {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
    body: formData,
  });
  return parseResponse(response);
};

export const del = async (endpoint) => {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() },
  });
  return parseResponse(response);
};

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------
export const getConversations = () => get('/conversations');
export const deleteConversation = (id) => del(`/conversations/${id}`);

// ---------------------------------------------------------------------------
// Chat / Voice / Image
// ---------------------------------------------------------------------------
export const postChat = (formData) => postForm('/chat', formData);
export const postUploadAudio = (formData) => postForm('/upload_audio', formData);
export const postUploadImage = (formData) => postForm('/upload_image', formData);

// ---------------------------------------------------------------------------
// Market Intelligence
// ---------------------------------------------------------------------------
export const getMarketPrices = (crop) => get(`/market/prices?crop=${encodeURIComponent(crop)}`);
export const getMarketTrend = (crop) => get(`/market/trend?crop=${encodeURIComponent(crop)}`);
export const getMarketHistory = (crop, days = 7) => get(`/market/history?crop=${encodeURIComponent(crop)}&days=${days}`);

// ---------------------------------------------------------------------------
// Farm Diary
// ---------------------------------------------------------------------------
export const getDiaryEntries = (userId) => get(`/diary/entries?user_id=${encodeURIComponent(userId)}`);
export const postDiaryEntry = (data) => post('/diary/entries', data);
export const getDiaryReport = (userId, period) => get(`/diary/report?user_id=${encodeURIComponent(userId)}&period=${period}`);
export const getDiaryPdf = (userId) => `${API_BASE}/diary/pdf?user_id=${encodeURIComponent(userId)}`;

// ---------------------------------------------------------------------------
// Alerts & Tips
// ---------------------------------------------------------------------------
export const getAlerts = (crop, lat, lon) => get(`/alerts/tips?crop=${encodeURIComponent(crop)}&lat=${lat}&lon=${lon}`);

// ---------------------------------------------------------------------------
// Soil Health
// ---------------------------------------------------------------------------
export const postSoilAnalyze = (data) => post('/soil/analyze', data);
export const postSoilDiy = (data) => post('/soil/diy-test', data);

// ---------------------------------------------------------------------------
// Water & Irrigation
// ---------------------------------------------------------------------------
export const postWaterAdvice = (data) => post('/water/advice', data);
export const getWaterAdvice = (crop, lat, lon) => get(`/water/balance?crop=${encodeURIComponent(crop)}&lat=${lat}&lon=${lon}`);

// ---------------------------------------------------------------------------
// Finance
// ---------------------------------------------------------------------------
export const postFinanceSchemes = (data) => post('/finance/schemes', data);
export const getFinanceCreditReport = (userId) => get(`/finance/credit-report?user_id=${encodeURIComponent(userId)}`);
export const postInsuranceQuote = (data) => post('/finance/insurance-quote', data);

// ---------------------------------------------------------------------------
// Community Q&A
// ---------------------------------------------------------------------------
export const getCommunityQuestions = (page = 1) => get(`/community/questions?page=${page}`);
export const postCommunityQuestion = (data) => post('/community/questions', data);
export const postCommunityAnswer = (questionId, data) => post(`/community/questions/${questionId}/answers`, data);

// ---------------------------------------------------------------------------
// Marketplace
// ---------------------------------------------------------------------------
export const getDealers = (lat, lon) => get(`/marketplace/dealers?lat=${lat}&lon=${lon}`);
export const postScanProduct = (formData) => postForm('/marketplace/scan', formData);
export const getVerifiedProducts = () => get('/marketplace/verified-products');

// ---------------------------------------------------------------------------
// Emergency
// ---------------------------------------------------------------------------
export const getEmergencyProviders = () => get('/emergency/providers');
export const postEmergencyReport = (data) => post('/emergency/reports', data);
export const postHelplineCall = (data) => post('/emergency/helpline', data);

// ---------------------------------------------------------------------------
// Yield & Planning
// ---------------------------------------------------------------------------
export const getYieldPrediction = (userId, crop, lat, lon) =>
  get(`/planner/predict?user_id=${encodeURIComponent(userId)}&crop=${encodeURIComponent(crop)}&lat=${lat}&lon=${lon}`);
export const getSeasonPlan = (userId, crop, lat, lon) =>
  get(`/planner/season-plan?user_id=${encodeURIComponent(userId)}&crop=${encodeURIComponent(crop)}&lat=${lat}&lon=${lon}`);

// ---------------------------------------------------------------------------
// Traceability
// ---------------------------------------------------------------------------
export const getTraceabilityBatches = (userId) => get(`/traceability/batches?user_id=${encodeURIComponent(userId)}`);
export const postTraceabilityEntry = (data) => post('/traceability/entries', data);
export const getTraceabilityVerify = (batchId) => get(`/traceability/verify/${batchId}`);

// ---------------------------------------------------------------------------
// Sustainability
// ---------------------------------------------------------------------------
export const getSustainabilityScore = (userId) => get(`/sustainability/score?user_id=${encodeURIComponent(userId)}`);
export const getSustainabilityReport = (userId) => get(`/sustainability/report?user_id=${encodeURIComponent(userId)}`);
