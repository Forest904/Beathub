import React, { useCallback } from 'react';
import { createPortal } from 'react-dom';
import DownloadProgress from './DownloadProgress';
import { useDownloadPanel } from '../context/DownloadPanelContext.jsx';
import { API_BASE_URL } from '../../../api/client';

const GlobalDownloadProgress = () => {
  const { visible, setHasActiveDownload, hide, handlers, hostElement } = useDownloadPanel();

  const handleActiveChange = useCallback((active) => {
    const isActive = Boolean(active);
    setHasActiveDownload(isActive);
    if (handlers?.onActiveChange) {
      handlers.onActiveChange(isActive);
    }
  }, [handlers, setHasActiveDownload]);

  const panel = (
    <DownloadProgress
      visible={visible}
      onClose={hide}
      baseUrl={API_BASE_URL}
      onActiveChange={handleActiveChange}
      onComplete={handlers?.onComplete}
    />
  );

  if (hostElement) {
    return createPortal(panel, hostElement);
  }

  return (
    <div className="px-4 pb-4">
      {panel}
    </div>
  );
};

export default GlobalDownloadProgress;
