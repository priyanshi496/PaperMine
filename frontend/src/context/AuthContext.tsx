"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";

interface AuthState {
  token: string | null;
  user: {
    id: number;
    email: string;
    role: "admin" | "vendor";
    vendor_id: number | null;
  } | null;
}

interface AuthContextType {
  authState: AuthState;
  login: (token: string, user: any) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({ token: null, user: null });
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const savedToken = localStorage.getItem("papermine_token");
    const savedUser = localStorage.getItem("papermine_user");
    
    if (savedToken && savedUser) {
      try {
        setAuthState({ token: savedToken, user: JSON.parse(savedUser) });
      } catch (e) {}
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const interceptor = axios.interceptors.request.use((config) => {
      if (authState.token) {
        config.headers.Authorization = `Bearer ${authState.token}`;
      }
      return config;
    });

    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          logout();
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(interceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [authState]);

  const login = (token: string, user: any) => {
    localStorage.setItem("papermine_token", token);
    localStorage.setItem("papermine_user", JSON.stringify(user));
    setAuthState({ token, user });
  };

  const logout = () => {
    localStorage.removeItem("papermine_token");
    localStorage.removeItem("papermine_user");
    setAuthState({ token: null, user: null });
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ authState, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
