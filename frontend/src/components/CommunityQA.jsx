import React, { useState } from 'react';

export default function CommunityQA() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  
  const handleSearch = (e) => {
    e.preventDefault();
    // In a real implementation, this would call /api/community/search
    setResults([
      { id: 1, text: "How do I treat leaf curl virus in tomatoes?", answer: "Use neem oil spray and remove infected leaves." },
      { id: 2, text: "Best fertilizer for Aman rice?", answer: "Apply Urea in three split doses." }
    ]);
  };

  return (
    <div className="community-container">
      <form onSubmit={handleSearch} className="search-form" style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input 
          type="text" 
          value={query} 
          onChange={(e) => setQuery(e.target.value)} 
          placeholder="Ask the community..."
          style={{ flex: 1, padding: '10px', borderRadius: '5px', border: '1px solid #ccc' }}
        />
        <button type="submit" style={{ padding: '10px 20px', borderRadius: '5px', background: '#2e7d32', color: 'white', border: 'none' }}>Search</button>
      </form>
      
      <div className="results-list" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {results.map(r => (
          <div key={r.id} className="result-card" style={{ padding: '15px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', borderLeft: '4px solid #4caf50' }}>
            <h4 style={{ margin: '0 0 10px 0' }}>Q: {r.text}</h4>
            <p style={{ margin: 0, color: '#aaa' }}>A: {r.answer}</p>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <button style={{ background: 'transparent', color: '#4caf50', border: '1px solid #4caf50', padding: '8px 16px', borderRadius: '5px' }}>Escalate to Expert</button>
      </div>
    </div>
  );
}
