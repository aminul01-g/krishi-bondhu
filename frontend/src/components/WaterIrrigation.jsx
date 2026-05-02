import React, { useState } from 'react';
import { postWaterAdvice } from '../services/api';

const WaterIrrigation = ({ userId }) => {
    const [advice, setAdvice] = useState('');

    const handleGetAdvice = async () => {
        const res = await postWaterAdvice({ user_id: userId, lat: 23.81, lon: 90.41, crop: "Rice" });
        setAdvice(res.advice);
    };

    return (
        <div className="card glassmorphism fade-in">
            <div className="feature-header">
                <h2>💧 Water & Irrigation (সেচ ও পানি ব্যবস্থাপনা)</h2>
                <p className="section-description">Precision irrigation based on real-time satellite moisture data.</p>
            </div>

            <div className="feature-form">
                <button className="vibrant-btn glow-effect" onClick={handleGetAdvice}>Get Daily Advice</button>
            </div>

            {advice && (
                <div className="result-card fade-in mt-4 bg-blue-50 rounded-lg p-4 border border-blue-100">
                    <div className="whitespace-pre-wrap text-gray-800 font-medium">{advice}</div>
                </div>
            )}
        </div>
    );
};

export default WaterIrrigation;
