import React, { createContext, useContext, useMemo, useReducer, useState, useCallback } from 'react';

const DownloadPanelContext = createContext(null);

const initialPanelState = {
  visible: false,
  hasActiveDownload: false,
  manualHide: false,
  isPeeking: false,
};

function panelReducer(state, action) {
  switch (action.type) {
    case 'SHOW':
      return { ...state, visible: true, manualHide: false };
    case 'HIDE':
      return { ...state, visible: false, manualHide: true, isPeeking: false };
    case 'SET_ACTIVE':
      if (action.active) {
        const shouldShow = state.manualHide ? state.visible : true;
        return {
          ...state,
          hasActiveDownload: true,
          visible: shouldShow,
        };
      }
      return {
        ...state,
        hasActiveDownload: false,
        manualHide: false,
        isPeeking: false,
        visible: false,
      };
    case 'BEGIN_PEEK':
      return { ...state, isPeeking: true };
    case 'END_PEEK':
      return { ...state, isPeeking: false };
    case 'NEW_JOB':
      return { ...state, manualHide: false, isPeeking: false };
    default:
      return state;
  }
}

export const DownloadPanelProvider = ({ children }) => {
  const [panelState, dispatch] = useReducer(panelReducer, initialPanelState);
  const [handlers, setHandlers] = useState({});
  const [primaryHost, setPrimaryHost] = useState(null);
  const [overlayHost, setOverlayHost] = useState(null);
  const [jobToken, setJobToken] = useState(0);
  const [collectionTitle, setCollectionTitle] = useState('');

  const show = useCallback(() => {
    dispatch({ type: 'SHOW' });
  }, []);

  const hide = useCallback(() => {
    dispatch({ type: 'HIDE' });
  }, []);

  const setActiveDownload = useCallback((active) => {
    dispatch({ type: 'SET_ACTIVE', active });
  }, []);

  const beginPeek = useCallback(() => {
    dispatch({ type: 'BEGIN_PEEK' });
  }, []);

  const endPeek = useCallback(() => {
    dispatch({ type: 'END_PEEK' });
  }, []);

  const registerHandlers = useCallback((nextHandlers) => {
    setHandlers(nextHandlers || {});
  }, []);

  const registerHost = useCallback((node) => {
    setPrimaryHost(node || null);
  }, []);

  const registerOverlayHost = useCallback((node) => {
    setOverlayHost(node || null);
  }, []);

  const notifyJobStart = useCallback(() => {
    setJobToken((token) => token + 1);
    setCollectionTitle('');
    dispatch({ type: 'NEW_JOB' });
  }, []);

  const value = useMemo(() => ({
    visible: panelState.visible,
    hasActiveDownload: panelState.hasActiveDownload,
    isPeeking: panelState.isPeeking,
    jobToken,
    collectionTitle,
    setCollectionTitle,
    show,
    hide,
    setActiveDownload,
    beginPeek,
    endPeek,
    notifyJobStart,
    handlers,
    registerHandlers,
    registerHost,
    registerOverlayHost,
    primaryHost,
    overlayHost,
  }), [panelState.visible, panelState.hasActiveDownload, panelState.isPeeking, jobToken, collectionTitle, show, hide, setActiveDownload, beginPeek, endPeek, notifyJobStart, handlers, registerHandlers, registerHost, registerOverlayHost, primaryHost, overlayHost]);

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
