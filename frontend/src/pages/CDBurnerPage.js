import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import AlbumGallery from '../components/AlbumGallery';
import { AlbumCardVariant } from '../components/AlbumCard';
import DevicesPanel from '../components/DevicesPanel';
import BurnProgress from '../components/BurnProgress';
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

      if (response.data?.last_error) {
        pushMessage({ type: 'error', text: `Burner error: ${response.data.last_error}` });
      } else if (response.data?.current_status === 'Burner Ready') {
        pushMessage({ type: 'info', text: 'CD burner is ready.' });
      }
    } catch (error) {
      console.error('Error polling burner status', error);
    }
  }, [apiBaseUrl, pushMessage]);

  const fetchDevices = useCallback(async () => {
    setLoadingDevices(true);
    try {
      const response = await axios.get(`${apiBaseUrl}/api/cd-burner/devices`);
      setDevices(response.data.devices || []);
    } catch (error) {
      console.error('Error fetching devices', error);
    } finally {
      setLoadingDevices(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    fetchDownloadedItems();
    pollBurnerStatus();
    fetchDevices();

    const statusInterval = setInterval(pollBurnerStatus, 4000);
    const deviceInterval = setInterval(fetchDevices, 8000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(deviceInterval);
    };
  }, [fetchDownloadedItems, pollBurnerStatus, fetchDevices]);

  const selectedItem = useMemo(
    () => downloadedItems.find((item) => item.id === selectedItemId) || null,
    [downloadedItems, selectedItemId],
  );

  const handleSelectItem = useCallback((item) => {
    setSelectedItemId((current) => (current === item.id ? null : item.id));
  }, []);

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
      pushMessage({ type: 'success', text: `Started burning ${selectedItem.name}.` });
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
      pushMessage({ type: 'info', text: 'Cancel requested.' });
      pollBurnerStatus();
    } catch (error) {
      console.error('Failed to cancel burn', error);
      pushMessage({ type: 'error', text: 'Failed to cancel the burn.' });
    }
  }, [activeSessionId, apiBaseUrl, pollBurnerStatus, pushMessage]);

  const handleSelectDevice = useCallback(
    async (device) => {
      try {
        await axios.post(`${apiBaseUrl}/api/cd-burner/select-device`, { device_id: device.id });
        pushMessage({ type: 'success', text: `Selected ${device.display_name || device.id}.` });
        fetchDevices();
        pollBurnerStatus();
      } catch (error) {
        console.error('Failed to select device', error);
        pushMessage({ type: 'error', text: 'Failed to select device.' });
      }
    },
    [apiBaseUrl, fetchDevices, pollBurnerStatus, pushMessage],
  );

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

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <main className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6 text-center">CD Burner</h1>

        {message && (
          <div className="mb-4">
            <Message type={message.type} text={message.text} />
          </div>
        )}

        <DevicesPanel devices={devices} loading={loadingDevices} onSelect={handleSelectDevice} burnerStatus={burnerStatus} />

        <div className="bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Music</h2>
          {isLoadingItems ? (
            <p className="text-gray-400">Loading downloaded items...</p>
          ) : downloadedItems.length === 0 ? (
            <p className="text-gray-400">Download some music first.</p>
          ) : (
            <>
              <p className="text-gray-300 mb-4">Click an album, playlist, or track to select it for burning.</p>
              <AlbumGallery
                albums={downloadedItems}
                onSelect={handleSelectItem}
                variant={AlbumCardVariant.BURN_SELECTION}
                selectedAlbumId={selectedItemId}
              />
            </>
          )}
        </div>

        <div className="text-center flex flex-col items-center justify-center gap-4">
          <div className="flex items-center justify-center gap-4">
            <button
              type="button"
              onClick={handleBurnCD}
              disabled={Boolean(disableReason)}
              className={`py-3 px-8 rounded-lg text-lg font-bold transition duration-200 ${
                disableReason ? 'bg-gray-600 text-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {isBurningInitiating
                ? 'Initiating Burn...'
                : burnerStatus.is_burning
                ? `Burning (${burnerStatus.progress_percentage || 0}%)`
                : 'Start CD Burn'}
            </button>
            {burnerStatus.is_burning && (
              <button
                type="button"
                onClick={handleCancelBurn}
                className="py-3 px-6 rounded-lg text-lg font-bold bg-red-700 hover:bg-red-800 text-white"
              >
                Cancel Burn
              </button>
            )}
          </div>
          {disableReason && <p className="mt-2 text-sm text-gray-400">{disableReason}</p>}
        </div>

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
