'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authService from '../services/authService';
import { getAccessToken, clearAccessToken } from '../lib/apiClient';

const AuthContext = createContext(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Helper to notify other contexts (e.g. CartContext) of auth transitions
  const notifyAuthChanged = () => {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('bharat:auth-changed'));
    }
  };

  // Initialize authentication state from backend
  const initAuth = useCallback(async () => {
    try {
      const token = getAccessToken();
      if (!token) {
        setUser(null);
        setIsLoading(false);
        return;
      }
      const currentUser = await authService.getMe();
      if (currentUser) {
        setUser(currentUser);
      }
    } catch {
      // Unauthenticated visitor is expected for guest browsing
      setUser(null);
      clearAccessToken();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initAuth();

    const handleAuthExpired = () => {
      setUser(null);
      notifyAuthChanged();
    };

    window.addEventListener('bharat:auth-expired', handleAuthExpired);
    return () => {
      window.removeEventListener('bharat:auth-expired', handleAuthExpired);
    };
  }, [initAuth]);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const data = await authService.login(email, password);
      if (data?.user) {
        setUser(data.user);
        notifyAuthChanged();
      }
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload) => {
    setIsLoading(true);
    try {
      const data = await authService.register(payload);
      if (data?.user) {
        setUser(data.user);
        notifyAuthChanged();
      }
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const registerWholesale = async (payload) => {
    setIsLoading(true);
    try {
      const data = await authService.registerWholesale(payload);
      if (data?.user) {
        setUser(data.user);
        notifyAuthChanged();
      }
      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authService.logout();
      setUser(null);
      notifyAuthChanged();
    } finally {
      setIsLoading(false);
    }
  };

  const refreshProfile = async () => {
    try {
      const updated = await authService.getMe();
      if (updated) {
        setUser(updated);
      }
      return updated;
    } catch {
      return null;
    }
  };

  const isWholesale =
    user?.role === 'WHOLESALE' ||
    user?.is_wholesale_buyer === true ||
    user?.wholesale_profile?.verification_status === 'VERIFIED';

  const isStaff =
    user?.is_staff === true ||
    user?.is_superuser === true ||
    user?.role === 'STAFF' ||
    user?.role === 'MANAGER' ||
    user?.role === 'ADMIN';

  const value = {
    user,
    isAuthenticated: !!user,
    isWholesale,
    isStaff,
    isLoading,
    login,
    register,
    registerWholesale,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;
