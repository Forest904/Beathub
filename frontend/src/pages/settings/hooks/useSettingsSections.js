import { useCallback, useEffect, useRef, useState } from "react";

const INITIAL_SECTIONS = {
  profile: true,
  downloads: false,
  apiKeys: false,
  email: false,
  password: false,
};

export const useSettingsSections = ({ userId, focusTarget, shouldOpenApiKeys }) => {
  const [sectionsOpen, setSectionsOpen] = useState(INITIAL_SECTIONS);
  const focusHandledRef = useRef(false);

  useEffect(() => {
    setSectionsOpen((prev) => ({ ...INITIAL_SECTIONS, ...prev, profile: true }));
  }, []);

  useEffect(() => {
    focusHandledRef.current = false;
  }, [userId]);

  useEffect(() => {
    if (!userId) {
      return;
    }
    if (focusHandledRef.current) {
      return;
    }
    if (focusTarget === "apiKeys" || shouldOpenApiKeys) {
      setSectionsOpen((prev) => ({ ...prev, apiKeys: true }));
      focusHandledRef.current = true;
    }
  }, [focusTarget, shouldOpenApiKeys, userId]);

  const toggleSection = useCallback((key) => {
    setSectionsOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  return { sectionsOpen, toggleSection };
};
