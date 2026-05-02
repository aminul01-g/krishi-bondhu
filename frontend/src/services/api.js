import { API_BASE } from '../api';

const post = (endpoint, data) => fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json' }
}).then(r => r.json());

const get = (endpoint) => fetch(`${API_BASE}${endpoint}`).then(r => r.json());

export const postSoilAnalyze = (data) => post('/soil/analyze', data);
export const postWaterAdvice = (data) => post('/water/advice', data);
export const postFinanceSchemes = (data) => post('/finance/schemes', data);
export const getFinanceCreditReport = (userId) => get(`/finance/credit-report?user_id=${userId}`);
export const postInsuranceQuote = (data) => post('/finance/insurance-quote', data);
