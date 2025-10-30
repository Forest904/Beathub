import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DATE_OF_BIRTH_STORAGE_KEY } from "../constants";
import { deriveUsername, formatErrors } from "../utils";
import { useAutoDismiss } from "./useAutoDismiss";

const getStoredDateOfBirth = () => {
  if (typeof window === "undefined") {
    return "";
  }
  try {
    return window.localStorage.getItem(DATE_OF_BIRTH_STORAGE_KEY) || "";
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn("Failed to read date of birth from storage", error);
    return "";
  }
};

export const useAccountSettings = ({ user, updateProfile, changeEmail, changePassword }) => {
  const initialUsername = useMemo(() => deriveUsername(user), [user?.id, user?.username, user?.email]);
  const profileBaselineRef = useRef(initialUsername);

  const [dateOfBirth, setDateOfBirth] = useState(getStoredDateOfBirth);
  const [profileForm, setProfileForm] = useState(() => ({ username: initialUsername }));
  const [profileStatus, setProfileStatus] = useState(null);

  const [emailForm, setEmailForm] = useState({ newEmail: user?.email ?? "", currentPassword: "" });
  const [emailStatus, setEmailStatus] = useState(null);

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordStatus, setPasswordStatus] = useState(null);

  useEffect(() => {
    if (profileBaselineRef.current === initialUsername) {
      return;
    }
    profileBaselineRef.current = initialUsername;
    setProfileForm({ username: initialUsername });
  }, [initialUsername]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      if (dateOfBirth && dateOfBirth.length > 0) {
        window.localStorage.setItem(DATE_OF_BIRTH_STORAGE_KEY, dateOfBirth);
      } else {
        window.localStorage.removeItem(DATE_OF_BIRTH_STORAGE_KEY);
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn("Failed to persist date of birth to storage", error);
    }
  }, [dateOfBirth]);

  useEffect(() => {
    setEmailForm((prev) => ({ ...prev, newEmail: user?.email ?? "" }));
  }, [user?.email]);

  useAutoDismiss(profileStatus, setProfileStatus);
  useAutoDismiss(emailStatus, setEmailStatus);
  useAutoDismiss(passwordStatus, setPasswordStatus);

  const handleDateOfBirthChange = useCallback((event) => {
    setDateOfBirth(event.target.value);
  }, []);

  const handleProfileChange = useCallback((event) => {
    const { name, value } = event.target;
    setProfileForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleProfileSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setProfileStatus({ type: "pending" });
      const payload = { username: profileForm.username.trim() };
      const result = await updateProfile(payload);
      if (result.ok) {
        const nextUsername = deriveUsername(result.user) || payload.username;
        profileBaselineRef.current = nextUsername;
        setProfileForm({ username: nextUsername });
        setProfileStatus({ type: "success", message: "Profile updated successfully." });
      } else {
        setProfileStatus({ type: "error", message: formatErrors(result.errors) || "Unable to update profile." });
      }
    },
    [profileForm, updateProfile]
  );

  const handleEmailChange = useCallback((event) => {
    const { name, value } = event.target;
    setEmailForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleEmailSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setEmailStatus({ type: "pending" });
      const result = await changeEmail({
        newEmail: emailForm.newEmail.trim().toLowerCase(),
        currentPassword: emailForm.currentPassword,
      });

      if (result.ok) {
        setEmailStatus({ type: "success", message: "Email updated." });
        setEmailForm({ newEmail: result.user?.email ?? "", currentPassword: "" });
      } else {
        setEmailStatus({ type: "error", message: formatErrors(result.errors) || "Unable to update email." });
      }
    },
    [changeEmail, emailForm]
  );

  const handlePasswordChange = useCallback((event) => {
    const { name, value } = event.target;
    setPasswordForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handlePasswordSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setPasswordStatus({ type: "pending" });
      if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        setPasswordStatus({ type: "error", message: "Passwords do not match." });
        return;
      }
      const result = await changePassword(passwordForm);
      if (result.ok) {
        setPasswordStatus({ type: "success", message: "Password updated." });
        setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      } else {
        setPasswordStatus({ type: "error", message: formatErrors(result.errors) || "Unable to update password." });
      }
    },
    [changePassword, passwordForm]
  );

  return {
    profile: {
      form: profileForm,
      status: profileStatus,
      onChange: handleProfileChange,
      onSubmit: handleProfileSubmit,
      dateOfBirth,
      onDateOfBirthChange: handleDateOfBirthChange,
    },
    email: {
      form: emailForm,
      status: emailStatus,
      onChange: handleEmailChange,
      onSubmit: handleEmailSubmit,
    },
    password: {
      form: passwordForm,
      status: passwordStatus,
      onChange: handlePasswordChange,
      onSubmit: handlePasswordSubmit,
    },
  };
};
