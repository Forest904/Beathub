import { useEffect } from "react";

export const useAutoDismiss = (status, setter, delay = 3000) => {
  useEffect(() => {
    if (!status || status.type === "pending") return undefined;
    const timer = setTimeout(() => setter(null), delay);
    return () => clearTimeout(timer);
  }, [status, setter, delay]);
};
