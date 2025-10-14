import React, { createContext, useContext, useMemo } from 'react';
import PropTypes from 'prop-types';
import { useQuery } from '@tanstack/react-query';

import { endpoints } from '../../api/client';
import { get } from '../../api/http';

const defaultValue = {
  isLoading: true,
  publicMode: false,
  allowStreamingExport: true,
  enableCdBurner: true,
  features: {},
  error: null,
};

const FeatureFlagsContext = createContext(defaultValue);

export const FeatureFlagsProvider = ({ children }) => {
  const query = useQuery({
    queryKey: ['public-config'],
    queryFn: async () => {
      return get(endpoints.config.public());
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const value = useMemo(
    () => ({
      isLoading: query.isLoading,
      error: query.error ?? null,
      publicMode: Boolean(query.data?.publicMode),
      allowStreamingExport:
        typeof query.data?.allowStreamingExport === 'boolean'
          ? query.data.allowStreamingExport
          : true,
      enableCdBurner:
        typeof query.data?.enableCDBurner === 'boolean'
          ? query.data.enableCDBurner
          : true,
      features: query.data?.features ?? {},
    }),
    [query.data, query.error, query.isLoading],
  );

  return (
    <FeatureFlagsContext.Provider value={value}>
      {children}
    </FeatureFlagsContext.Provider>
  );
};

FeatureFlagsProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export const useFeatureFlags = () => useContext(FeatureFlagsContext);

export default FeatureFlagsContext;
