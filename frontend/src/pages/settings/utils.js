export const deriveUsername = (user) => {
  if (!user) return "";
  if (user.username && typeof user.username === "string" && user.username.trim().length > 0) {
    return user.username.trim();
  }
  if (user.email && typeof user.email === "string") {
    const prefix = user.email.split("@")[0];
    return prefix || user.email;
  }
  return "";
};

export const formatErrors = (errors) => {
  if (!errors) return "";
  if (typeof errors === "string") return errors;
  if (Array.isArray(errors)) return errors.join(" ");
  return Object.values(errors)
    .flat()
    .join(" ");
};

export const clampThreads = (value) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return 1;
  }
  return Math.min(12, Math.max(1, Math.round(numeric)));
};

export const normalizeApiKeysMeta = (raw, fields, defaultsFactory) => {
  if (!raw || typeof raw !== "object") {
    return defaultsFactory();
  }
  return fields.reduce((acc, field) => {
    const value = raw[field.key];
    const stored = Boolean(value?.stored);
    acc[field.key] = {
      stored,
      preview: stored && typeof value?.preview === "string" ? value.preview : "",
    };
    return acc;
  }, defaultsFactory());
};
