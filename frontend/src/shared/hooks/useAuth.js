import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { get, post } from '../../api/http';
import { endpoints } from '../../api/client';

const AuthContext = createContext(undefined);

const parseError = (error) => {
  if (error?.response?.data?.errors) {
    return error.response.data.errors;
  }
  return { form: 'Something went wrong. Please try again.' };
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState(null);

  const loadSession = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await get(endpoints.auth.session());
      setUser(resp?.user || null);
      setErrors(null);
    } catch (error) {
      setErrors(parseError(error));
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const register = useCallback(async ({ email, password }) => {
    try {
      const resp = await post(endpoints.auth.register(), { email, password });
      setUser(resp.user);
      setErrors(null);
      return { ok: true };
    } catch (error) {
      const parsed = parseError(error);
      setErrors(parsed);
      return { ok: false, errors: parsed };
    }
  }, []);

  const login = useCallback(async ({ email, password }) => {
    try {
      const resp = await post(endpoints.auth.login(), { email, password });
      setUser(resp.user);
      setErrors(null);
      return { ok: true };
    } catch (error) {
      const parsed = parseError(error);
      setErrors(parsed);
      return { ok: false, errors: parsed };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await post(endpoints.auth.logout());
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      errors,
      register,
      login,
      logout,
      refresh: loadSession,
      clearErrors: () => setErrors(null),
    }),
    [user, loading, errors, register, login, logout, loadSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
