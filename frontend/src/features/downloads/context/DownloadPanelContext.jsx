import React, { createContext, useContext, useMemo, useState, useCallback } from 'react';

const DownloadPanelContext = createContext(null);

export const DownloadPanelProvider = ({ children }) => {
  const [visible, setVisible] = useState(false);
  const [hasActiveDownload, setHasActiveDownload] = useState(false);
  const [handlers, setHandlers] = useState({});
  const [hostElement, setHostElement] = useState(null);

  const show = useCallback(() => setVisible(true), []);
  const hide = useCallback(() => setVisible(false), []);
  const registerHandlers = useCallback((nextHandlers) => {
    setHandlers(nextHandlers || {});
  }, []);

  const registerHost = useCallback((node) => {
    setHostElement(node || null);
  }, []);

  const value = useMemo(() => ({
    visible,
    show,
    hide,
    hasActiveDownload,
    setHasActiveDownload,
    handlers,
    registerHandlers,
    hostElement,
    registerHost,
  }), [visible, show, hide, hasActiveDownload, setHasActiveDownload, handlers, registerHandlers, hostElement, registerHost]);

  return (
    <DownloadPanelContext.Provider value={value}>
      {children}
    </DownloadPanelContext.Provider>
  );
};

export const useDownloadPanel = () => {
  const ctx = useContext(DownloadPanelContext);
  if (!ctx) throw new Error('useDownloadPanel must be used within DownloadPanelProvider');
  return ctx;
};
