import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import PropTypes from "prop-types";

import { fetchSettingsStatus } from "../../api";
import { useAuth } from "../hooks/useAuth";

const SettingsStatusContext = createContext({
  loading: false,
  spotdlReady: false,
  spotifyReady: false,
  geniusReady: false,
  credentialsReady: false,
  apiKeys: null,
  refresh: () => {},
});

export const SettingsStatusProvider = ({ children }) => {
  const { user } = useAuth();
  const [state, setState] = useState({
    loading: Boolean(user),
    spotdlReady: false,
    spotifyReady: false,
    geniusReady: false,
    credentialsReady: false,
    apiKeys: null,
  });

  const refresh = useCallback(async () => {
    if (!user) {
      setState({
        loading: false,
        spotdlReady: false,
        spotifyReady: false,
        geniusReady: false,
        credentialsReady: false,
        apiKeys: null,
      });
      return;
    }

    setState((prev) => ({ ...prev, loading: true }));
    try {
      const status = await fetchSettingsStatus();
      setState({
        loading: false,
        spotdlReady: Boolean(status?.spotdl_ready),
        spotifyReady: Boolean(status?.spotify_ready),
        geniusReady: Boolean(status?.genius_ready),
        credentialsReady: Boolean(status?.credentials_ready ?? status?.spotify_ready),
        apiKeys: status?.api_keys || null,
      });
    } catch (error) {
      setState({
        loading: false,
        spotdlReady: false,
        spotifyReady: false,
        geniusReady: false,
        credentialsReady: false,
        apiKeys: null,
      });
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <SettingsStatusContext.Provider value={{ ...state, refresh }}>
      {children}
    </SettingsStatusContext.Provider>
  );
};

SettingsStatusProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export const useSettingsStatus = () => useContext(SettingsStatusContext);

export default SettingsStatusContext;
