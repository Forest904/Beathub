import { useCallback } from 'react';
import { useDownloadHistoryQuery, useRemoveDownloadMutation } from '../../../api';

export const useDownloadHistory = () => {
  const query = useDownloadHistoryQuery();
  const removeMutation = useRemoveDownloadMutation();

  const refresh = useCallback(async ({ silent = false } = {}) => {
    const result = await query.refetch({
      throwOnError: !silent,
      cancelRefetch: false,
    });
    if (result.error) {
      throw result.error;
    }
    return result.data ?? [];
  }, [query]);

  const remove = useCallback(async (id) => {
    const success = await removeMutation.mutateAsync(id);
    return success;
  }, [removeMutation]);

  return {
    items: query.data ?? [],
    loading: query.isLoading || query.isFetching,
    error: query.error ?? null,
    refresh,
    remove,
    isRemoving: removeMutation.isPending,
  };
};

export default useDownloadHistory;
