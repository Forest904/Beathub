export const createMessageManager = () => {
  let lastText = null;
  return {
    push(current, setter) {
      if (!setter) return;
      if (!current) {
        lastText = null;
        setter(null);
        return;
      }
      if (current.text && current.text === lastText) return;
      lastText = current.text || null;
      setter(current);
    },
  };
};
