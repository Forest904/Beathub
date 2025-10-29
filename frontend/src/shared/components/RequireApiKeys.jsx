import React from "react";
import PropTypes from "prop-types";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { useSettingsStatus } from "../context/SettingsStatusContext";

const RequireApiKeys = ({ children, requireCredentials }) => {
  const location = useLocation();
  const { user, loading: authLoading } = useAuth();
  const { loading, credentialsReady } = useSettingsStatus();

  const loadingView = (
    <section className="mx-auto flex max-w-3xl flex-1 items-center justify-center px-4 py-24 text-center">
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-10 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <p className="text-sm text-slate-500 dark:text-slate-400">Checking API credentials...</p>
      </div>
    </section>
  );

  if (authLoading) {
    return loadingView;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (requireCredentials) {
    if (loading) {
      return loadingView;
    }

    if (!credentialsReady) {
      return (
        <Navigate
          to="/settings"
          replace
          state={{ from: location.pathname + location.search, focus: "apiKeys" }}
        />
      );
    }
  }

  return children;
};

RequireApiKeys.propTypes = {
  children: PropTypes.node.isRequired,
  requireCredentials: PropTypes.bool,
};

RequireApiKeys.defaultProps = {
  requireCredentials: false,
};

export default RequireApiKeys;

