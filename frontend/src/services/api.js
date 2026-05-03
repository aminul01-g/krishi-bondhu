import { API_BASE } from '../api';

const parseResponse = async (response) => {
  const text = await response.text();
  let data = null;

  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { message: text }
  }

  if (!response.ok) {
    const error = data.error || data.detail || data.message || response.statusText || 'API request failed'
    throw new Error(error)
  }

  return data
}

const post = async (endpoint, data) => {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return parseResponse(response)
}

const get = async (endpoint) => {
  const response = await fetch(`${API_BASE}${endpoint}`)
  return parseResponse(response)
}

export const postSoilAnalyze = (data) => post('/soil/analyze', data)
export const postWaterAdvice = (data) => post('/water/advice', data)
export const postFinanceSchemes = (data) => post('/finance/schemes', data)
export const getFinanceCreditReport = (userId) => get(`/finance/credit-report?user_id=${userId}`)

export const postInsuranceQuote = (data) => post('/finance/insurance-quote', data)
export const getEmergencyProviders = () => get('/emergency/providers')
export const postEmergencyReport = (data) => post('/emergency/reports', data)
export const postHelplineCall = (data) => post('/emergency/helpline', data)
