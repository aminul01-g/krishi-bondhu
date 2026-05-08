import { createContext, useContext, useState, useEffect } from 'react';
import { getMe } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('kb_auth_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    const ctrl = new AbortController();
    getMe(ctrl.signal)
      .then(setUser)
      .catch(() => { localStorage.removeItem('kb_auth_token'); setToken(null); })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [token]);

  const loginUser = (accessToken) => {
    localStorage.setItem('kb_auth_token', accessToken);
    setToken(accessToken);
  };

  const logout = () => {
    localStorage.removeItem('kb_auth_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, loginUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
