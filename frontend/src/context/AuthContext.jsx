import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../api/axios.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [hr, setHr] = useState(null);
  const [loading, setLoading] = useState(!!token);

  useEffect(() => {
    if (!token) return;
    async function fetchMe() {
      try {
        const res = await api.get("/api/auth/me");
        setHr(res.data);
      } catch {
        setToken(null);
        localStorage.removeItem("token");
      } finally {
        setLoading(false);
      }
    }
    fetchMe();
  }, [token]);

  const login = (newToken, hrData) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
    setHr(hrData);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setHr(null);
  };

  return (
    <AuthContext.Provider value={{ token, hr, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

