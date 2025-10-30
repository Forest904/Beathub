import React, { useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import DownloadProgress from './DownloadProgress';
import { useDownloadPanel } from '../context/DownloadPanelContext.jsx';
import { API_BASE_URL } from '../../../api/client';

const GlobalDownloadProgress = () => {
  const {
    visible,
    isPeeking,
    hide,
    setActiveDownload,
    handlers,
    primaryHost,
    overlayHost,
    jobToken,
    collectionTitle,
    setCollectionTitle,
  } = useDownloadPanel();

  const fallbackHostRef = useRef(null);

  const handleActiveChange = useCallback((active) => {
    setActiveDownload(Boolean(active));
    if (handlers?.onActiveChange) {
      handlers.onActiveChange(Boolean(active));
    }
  }, [handlers, setActiveDownload]);

  const host = overlayHost || primaryHost || fallbackHostRef.current;
  const shouldRender = Boolean(host);

  return (
    <>
      <div ref={fallbackHostRef} className="hidden" aria-hidden="true" />
      {shouldRender
        ? createPortal(
            <DownloadProgress
              visible={visible || isPeeking}
              onClose={hide}
              baseUrl={API_BASE_URL}
              onActiveChange={handleActiveChange}
              onComplete={handlers?.onComplete}
              jobToken={jobToken}
              collectionTitle={collectionTitle}
              onCollectionTitleChange={setCollectionTitle}
            />,
            host,
          )
        : null}
    </>
  );
};

export default GlobalDownloadProgress;