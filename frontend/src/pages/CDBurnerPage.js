import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
/* eslint-disable unicode-bom */
import axios from 'axios';
import AlbumGallery from '../components/AlbumGallery';
import { AlbumCardVariant } from '../components/AlbumCard';
import DeviceCard from '../components/DeviceCard';
import BurnProgress from '../components/BurnProgress';
import BurnPreview from '../components/BurnPreview';
import Message from '../components/Message';

const CDBurnerPage = () => {
  const [downloadedItems, setDownloadedItems] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [burnerStatus, setBurnerStatus] = useState({
    is_burning: false,
    current_status: 'Initializing...'
  });
  const [message, setMessage] = useState(null);
  const [isLoadingItems, setIsLoadingItems] = useState(true);
  const [isBurningInitiating, setIsBurningInitiating] = useState(false);
  const [devices, setDevices] = useState([]);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [showBurnProgress, setShowBurnProgress] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState(null);

  // Burn preview state
  const [previewPlan, setPreviewPlan] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const lastPreviewItemIdRef = useRef(null);

  const messageTextRef = useRef(null);

  const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

  const pushMessage = useCallback((next) => {
    if (!next) {
      messageTextRef.current = null;
      setMessage(null);
      return;
    }
    if (messageTextRef.current === next.text) {
      return;
    }
    messageTextRef.current = next.text;
    setMessage(next);
  }, []);

  useEffect(() => {
    if (!message) {
      return undefined;
    }
    const timer = setTimeout(() => pushMessage(null), 3500);
    return () => clearTimeout(timer);
  }, [message, pushMessage]);

  const fetchDownloadedItems = useCallback(async () => {
    setIsLoadingItems(true);
    try {
      const response = await axios.get(`${apiBaseUrl}/api/albums`);
      setDownloadedItems(response.data);
    } catch (error) {
      console.error('Error fetching downloaded items', error);
      pushMessage({ type: 'error', text: 'Failed to load downloaded items. Please try again.' });
    } finally {
      setIsLoadingItems(false);
    }
  }, [apiBaseUrl, pushMessage]);

  const pollBurnerStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${apiBaseUrl}/api/cd-burner/status`);
      setBurnerStatus(response.data);
      if (response.data?.session_id) {
        setActiveSessionId(response.data.session_id);
      }
      // Subtle UX: avoid periodic popups. Only show errors while an operation is active.
      if (response.data?.last_error && (burnerStatus.is_burning || isBurningInitiating)) {
        pushMessage({ type: 'error', text: `Burner error: ${response.data.last_error}` });
      }
    } catch (error) {
      console.error('Error polling burner status', error);
    }
  }, [apiBaseUrl, pushMessage, burnerStatus.is_burning, isBurningInitiating]);

  const fetchDevices = useCallback(
    async (options = { showSpinner: false }) => {
      const { showSpinner } = options || {};
      if (showSpinner) setLoadingDevices(true);
      try {
        const response = await axios.get(`${apiBaseUrl}/api/cd-burner/devices`);
        setDevices(response.data.devices || []);
        if (response.data?.error) {
          pushMessage({ type: 'error', text: response.data.error });
        }
      } catch (error) {
        console.error('Error fetching devices', error);
        const errorMessage =
          error.response?.data?.error ||
          'Unable to enumerate CD burners. Ensure Windows IMAPI2 and comtypes are installed.';
        pushMessage({ type: 'error', text: errorMessage });
        // Keep showing previous devices on error to avoid UI flicker
      } finally {
        if (showSpinner) setLoadingDevices(false);
      }
    },
    [apiBaseUrl, pushMessage],
  );

  useEffect(() => {
    fetchDownloadedItems();
    pollBurnerStatus();
    fetchDevices({ showSpinner: true });

    const statusInterval = setInterval(pollBurnerStatus, 4000);
    const deviceInterval = setInterval(() => fetchDevices(), 8000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(deviceInterval);
    };
  }, [fetchDownloadedItems, pollBurnerStatus, fetchDevices]);

  // Prevent accidental navigation/refresh while burning or initiating
  useEffect(() => {
    const shouldBlock = burnerStatus.is_burning || isBurningInitiating;
    const beforeUnload = (e) => {
      if (!shouldBlock) return;
      e.preventDefault();
      e.returnValue = '';
    };
    if (shouldBlock) {
      window.addEventListener('beforeunload', beforeUnload);
    }
    return () => {
      window.removeEventListener('beforeunload', beforeUnload);
    };
  }, [burnerStatus.is_burning, isBurningInitiating]);

  const selectedItem = useMemo(
    () => downloadedItems.find((item) => item.id === selectedItemId) || null,
    [downloadedItems, selectedItemId],
  );

  const handleSelectItem = useCallback((item) => {
    if (burnerStatus.is_burning || isBurningInitiating) return;
    setSelectedItemId((current) => (current === item.id ? null : item.id));
  }, [burnerStatus.is_burning, isBurningInitiating]);

  const handleBurnCD = useCallback(async () => {
    if (!selectedItem) {
      pushMessage({ type: 'warning', text: 'Select a downloaded item to burn first.' });
      return;
    }

    const selectedDevice = devices.find((device) => device.selected);
    if (!selectedDevice) {
      pushMessage({ type: 'warning', text: 'Select a burner device before starting.' });
      return;
    }
    if (!selectedDevice.present) {
      pushMessage({ type: 'warning', text: 'Insert a disc in the selected device.' });
      return;
    }
    if (!selectedDevice.writable) {
      pushMessage({ type: 'warning', text: 'Insert a blank or writable disc.' });
      return;
    }
    if (burnerStatus.is_burning) {
      pushMessage({ type: 'info', text: 'A burn is already in progress.' });
      return;
    }

    setIsBurningInitiating(true);
    setShowBurnProgress(true);
    try {
      await axios.post(`${apiBaseUrl}/api/cd-burner/burn`, { download_item_id: selectedItem.id });
      // Subtle UX: no popup success; progress panel and banner will indicate activity
      pollBurnerStatus();
    } catch (error) {
      console.error('Failed to start burn', error);
      pushMessage({ type: 'error', text: 'Could not start the burn. Please check the burner status.' });
    } finally {
      setIsBurningInitiating(false);
    }
  }, [apiBaseUrl, burnerStatus.is_burning, devices, pollBurnerStatus, pushMessage, selectedItem]);

  const handleCancelBurn = useCallback(async () => {
    if (!activeSessionId) {
      return;
    }
    try {
      await axios.post(`${apiBaseUrl}/api/cd-burner/cancel`, { session_id: activeSessionId });
      pollBurnerStatus();
    } catch (error) {
      console.error('Failed to cancel burn', error);
      pushMessage({ type: 'error', text: 'Failed to cancel the burn.' });
    }
  }, [activeSessionId, apiBaseUrl, pollBurnerStatus, pushMessage]);

  const handleSelectDevice = useCallback(
    async (device) => {
      try {
        if (!device) {
          await axios.post(`${apiBaseUrl}/api/cd-burner/select-device`, { device_id: null });
        } else {
          await axios.post(`${apiBaseUrl}/api/cd-burner/select-device`, { device_id: device.id });
        }
        fetchDevices();
        pollBurnerStatus();
      } catch (error) {
        console.error('Failed to select device', error);
        const errorMessage = error.response?.data?.error || 'Failed to select device.';
        pushMessage({ type: 'error', text: errorMessage });
      }
    },
    [apiBaseUrl, fetchDevices, pollBurnerStatus, pushMessage],
  );
  // Removed status summary display; keep burnerStatus for internal logic only.
  const selectedDevice = useMemo(() => devices.find((device) => device.selected) || null, [devices]);

  const disableReason = useMemo(() => {
    if (!selectedItem) {
      return 'Select a downloaded album below.';
    }
    if (!selectedDevice) {
      return 'Select a burner device above.';
    }
    if (!selectedDevice.present) {
      return 'Insert a disc in the selected device.';
    }
    if (!selectedDevice.writable) {
      return 'Insert a blank or writable disc.';
    }
    if (burnerStatus.is_burning) {
      return 'A burn is already in progress.';
    }
    if (isBurningInitiating) {
      return 'Starting burn...';
    }
    return null;
  }, [burnerStatus.is_burning, isBurningInitiating, selectedDevice, selectedItem]);
  
  const canStartByDevice = Boolean(selectedDevice && selectedDevice.present && selectedDevice.writable && !burnerStatus.is_burning);

  const fetchPreview = useCallback(async () => {
    if (!selectedItem) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const res = await axios.post(`${apiBaseUrl}/api/cd-burner/preview`, {
        download_item_id: selectedItem.id,
      });
      setPreviewPlan(res.data);
    } catch (error) {
      console.error('Preview fetch failed', error);
      const msg = error.response?.data?.error || 'Failed to generate burn preview.';
      setPreviewError(msg);
      pushMessage({ type: 'error', text: msg });
      setPreviewPlan(null);
    } finally {
      setPreviewLoading(false);
    }
  }, [apiBaseUrl, pushMessage, selectedItem]);

  // Auto-fetch preview only when both device and album are selected
  useEffect(() => {
    if (selectedItem && selectedDevice) {
      const key = `${selectedItem.id}|${selectedDevice.id}`;
      if (lastPreviewItemIdRef.current !== key || !previewPlan) {
        lastPreviewItemIdRef.current = key;
        fetchPreview();
      }
    } else {
      lastPreviewItemIdRef.current = null;
      setPreviewPlan(null);
      setPreviewError(null);
      setPreviewLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedItem?.id, selectedDevice?.id]);

  return (
    <div className="min-h-screen">
      <main className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6 text-center">CD Burner</h1>
        {(burnerStatus.is_burning || isBurningInitiating) && (
          <div className="sticky top-0 z-40">
            <div
              role="status"
              aria-live="polite"
              aria-atomic="true"
              className="mx-auto my-4 w-full rounded-md bg-brandWarning-400 text-black ring-1 ring-brandWarning-500/70 px-4 py-3 shadow-lg flex items-center justify-center gap-3"
            >
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-black/10 text-black text-sm font-extrabold">!</span>
              <span className="text-sm font-semibold">CD burn in progress — do not navigate away.</span>
            </div>
          </div>
        )}

        {message && (
          <div className="mb-4">
            <Message type={message.type} text={message.text} />
          </div>
        )}

        <section className="bg-brand-50 dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 ring-1 ring-brand-100 dark:ring-0">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-xl font-semibold">Devices</h2>
          </div>
          {loadingDevices ? (
            <p className="text-slate-600 dark:text-gray-400">Scanning devices...</p>
          ) : (
            <>
              {devices.length === 0 ? (
                <p className="text-slate-600 dark:text-gray-400">No connected burner detected.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                  {devices.map((device) => (
                    <DeviceCard
                      key={device.id}
                      device={device}
                      onSelect={handleSelectDevice}
                      disabled={burnerStatus.is_burning || isBurningInitiating}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </section>

        {/* Checklist panel removed; guidance will appear inline with the preview/start area */}

        <div className="bg-brand-50 dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8 ring-1 ring-brand-100 dark:ring-0">
          <h2 className="text-xl font-semibold mb-4">Music</h2>
          {isLoadingItems ? (
            <p className="text-slate-600 dark:text-gray-400">Loading downloaded items...</p>
          ) : downloadedItems.length === 0 ? (
            <p className="text-slate-600 dark:text-gray-400">Download some music first.</p>
          ) : (
            <>
              <p className="text-slate-600 dark:text-gray-300 mb-4">Click an album, playlist, or track to select it for burning.</p>
              <AlbumGallery
                albums={downloadedItems}
                onSelect={handleSelectItem}
                variant={AlbumCardVariant.BURN_SELECTION}
                selectedAlbumId={selectedItemId}
                disabled={burnerStatus.is_burning || isBurningInitiating}
              />
            </>
          )}
        </div>
        {burnerStatus.is_burning && (
          <div className="text-center mb-4">
            <button
              type="button"
              onClick={handleCancelBurn}
              className="py-3 px-6 rounded-lg text-lg font-bold bg-brandError-700 hover:bg-brandError-800 text-white"
            >
              Cancel Burn
            </button>
          </div>
        )}

        {selectedItem && selectedDevice && (
          <div className="w-full">
            {previewLoading && (
              <div className="mt-4 text-slate-600 dark:text-gray-300 text-sm">Generating preview…</div>
            )}
            {previewError && (
              <div className="mt-4 text-brandError-600 dark:text-brandError-400 text-sm">{previewError}</div>
            )}
            {previewPlan && !previewLoading && !previewError && (
              <BurnPreview
                plan={previewPlan}
                initiating={isBurningInitiating}
                inProgress={burnerStatus.is_burning}
                onStart={handleBurnCD}
                canStart={canStartByDevice}
                disabledReason={disableReason}
              />
            )}
          </div>
        )}

        <BurnProgress
          visible={showBurnProgress || burnerStatus.is_burning}
          baseUrl={apiBaseUrl}
          sessionId={activeSessionId}
          onClose={() => setShowBurnProgress(false)}
        />
      </main>
    </div>
  );
};

export default CDBurnerPage;




