import { useCallback, useState } from 'react';
import { endpoints } from '../../../api/client';
import { get, del } from '../../../api/http';
import { toDownloadItem } from '../../../api/mappers';

export const useDownloadHistory = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await get(endpoints.downloads.list());
      const next = Array.isArray(data) ? data.map(toDownloadItem) : [];
      setItems(next);
      return next;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  const remove = useCallback(async (id) => {
    const response = await del(endpoints.downloads.remove(id));
    if (response?.success) {
      setItems((prev) => prev.filter((item) => item.id !== id));
      return true;
    }
    return false;
  }, []);

  return {
    items,
    loading,
    error,
    refresh,
    remove,
    setItems,
  };
};

export default useDownloadHistory;
