import React, { createContext, useContext, useEffect, useState } from 'react';
import { getToken, removeToken, saveToken } from './api';
import api from './api';

interface User {
  id: number;
  username: string;
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getToken().then(async (t) => {
      if (t) {
        setToken(t);
        try {
          const res = await api.get('/users/me');
          setUser(res.data);
        } catch {
          await removeToken();
        }
      }
      setLoading(false);
    });
  }, []);

  const login = async (username: string, password: string) => {
    const res = await api.post('/auth/login', { username, password });
    const { access_token, user: u } = res.data;
    await saveToken(access_token);
    setToken(access_token);
    setUser(u);
  };

  const logout = async () => {
    await removeToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
