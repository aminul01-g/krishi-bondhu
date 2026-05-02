import React, { useState } from 'react';
import { postFinanceSchemes, getFinanceCreditReport } from '../services/api';

const FinanceHub = ({ userId }) => {
    const [subsidies, setSubsidies] = useState('');
    const [report, setReport] = useState('');

    const fetchSubsidies = async () => {
        const res = await postFinanceSchemes({ user_id: userId, crop: "Rice", land_size: 1.0 });
        setSubsidies(res.advice);
    };

    const fetchReport = async () => {
        const res = await getFinanceCreditReport(userId);
        setReport(res.report);
    };

    return (
        <div className="card glassmorphism fade-in">
            <div className="feature-header">
                <h2>💰 Finance & Subsidies (অর্থ ও ভর্তুকি)</h2>
                <p className="section-description">Manage credit readiness and discover government support.</p>
            </div>

            <div className="feature-form flex-row gap-2">
                <button className="vibrant-btn glow-effect flex-1" onClick={fetchSubsidies}>View Subsidies</button>
                <button className="vibrant-btn glow-effect flex-1" onClick={fetchReport}>Credit Score</button>
            </div>

            {subsidies && (
                <div className="result-card fade-in mt-4 p-4 border border-yellow-200">
                    <h3 className="font-semibold text-yellow-800 mb-2">Available Subsidies:</h3>
                    <div className="whitespace-pre-wrap text-sm text-gray-700">{subsidies}</div>
                </div>
            )}
            
            {report && (
                <div className="report-card fade-in mt-4 bg-yellow-50 p-4 border border-yellow-100 rounded-lg">
                    <div className="whitespace-pre-wrap font-medium text-yellow-900">{report}</div>
                </div>
            )}
        </div>
    );
};

export default FinanceHub;
