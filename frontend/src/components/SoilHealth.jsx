import React, { useState } from 'react';
import { postSoilAnalyze } from '../services/api';

const SoilHealth = ({ userId }) => {
    const [advice, setAdvice] = useState('');
    const [crop, setCrop] = useState('');

    const handleAnalyze = async () => {
        const res = await postSoilAnalyze({ user_id: userId, crop });
        setAdvice(res.advice);
    };

    return (
        <div className="card glassmorphism fade-in">
            <div className="feature-header">
                <h2>🌱 Soil Health Advisor (মাটির স্বাস্থ্য)</h2>
                <p className="section-description">Analyze soil for optimal crop nutrition.</p>
            </div>
            
            <div className="feature-form">
                <input 
                    className="vibrant-input" 
                    placeholder="Enter crop name (e.g., Rice)" 
                    value={crop} 
                    onChange={(e) => setCrop(e.target.value)} 
                />
                <button className="vibrant-btn glow-effect" onClick={handleAnalyze}>Analyze Soil</button>
            </div>
            
            {advice && (
                <div className="result-card fade-in mt-4 bg-white rounded-lg shadow-sm p-4">
                    <h3 className="text-lg font-semibold mb-2">Analysis Results:</h3>
                    <div className="whitespace-pre-wrap text-gray-700">{advice}</div>
                </div>
            )}
        </div>
    );
};

export default SoilHealth;
