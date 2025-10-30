import React, { useCallback, useEffect, useRef } from "react";
import { Link, NavLink } from "react-router-dom";
import UserHoverPanel from "./UserHoverPanel.jsx";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../../theme/ThemeContext";
import { useDownloadPanel } from "../../features/downloads/context/DownloadPanelContext.jsx";
import { ReactComponent as LogoLight } from "../../assets/icons/beathub-logo-light.svg";
import { ReactComponent as LogoDark } from "../../assets/icons/beathub-logo-dark.svg";

const NAV_LINKS = [
  { label: "Discover", to: "/browse" },
  { label: "Download", to: "/download" },
  { label: "Burn", to: "/burn-cd" },
];

const DownloadStatusIndicator = () => {
  const { hasActiveDownload, beginPeek, endPeek, registerOverlayHost } = useDownloadPanel();
  const containerRef = useRef(null);
  const overlayHostRef = useRef(null);

  const activateOverlay = useCallback(() => {
    if (!hasActiveDownload) {
      return;
    }
    if (overlayHostRef.current) {
      registerOverlayHost(overlayHostRef.current);
    }
    beginPeek();
  }, [hasActiveDownload, beginPeek, registerOverlayHost]);

  const deactivateOverlay = useCallback(() => {
    endPeek();
    registerOverlayHost(null);
  }, [endPeek, registerOverlayHost]);

  const handleBlur = useCallback((event) => {
    if (!containerRef.current) {
      deactivateOverlay();
      return;
    }
    if (!event.relatedTarget || !containerRef.current.contains(event.relatedTarget)) {
      deactivateOverlay();
    }
  }, [deactivateOverlay]);

  useEffect(() => () => registerOverlayHost(null), [registerOverlayHost]);

  if (!hasActiveDownload) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="relative flex items-center"
      onMouseEnter={activateOverlay}
      onMouseLeave={deactivateOverlay}
      onFocus={activateOverlay}
      onBlur={handleBlur}
    >
      <button
        type="button"
        className="relative flex h-10 w-10 items-center justify-center rounded-full text-brand-600 transition hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:text-brandDark-100 dark:hover:text-brandDark-50 dark:focus:ring-brandDark-300"
      >
        <span
          className="absolute inline-flex h-9 w-9 animate-ping rounded-full bg-brand-500/30 dark:bg-brandDark-400/30"
          aria-hidden="true"
        />
        <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-white shadow-sm dark:bg-slate-900">
          <svg
            className="h-5 w-5 animate-bounce text-brand-600 dark:text-brandDark-100"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 4v10"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M8 10l4 4 4-4"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="M5 19h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </span>
        <span className="sr-only">View download progress</span>
      </button>
      <div
        ref={overlayHostRef}
        className="pointer-events-auto absolute left-1/2 top-full z-50 mt-3 w-[min(90vw,26rem)] -translate-x-1/2"
        onMouseEnter={activateOverlay}
        onMouseLeave={deactivateOverlay}
      />
    </div>
  );
};

const Header = () => {
  const { user, logout } = useAuth();
  const { theme } = useTheme();
  const email = user && typeof user.email === "string" ? user.email : "";

  const handleLogout = async () => {
    await logout();
  };

  const links = user ? NAV_LINKS : [];
  const BrandLogo = theme === "dark" ? LogoDark : LogoLight;

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 text-slate-900 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80 dark:text-slate-100">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-4 md:gap-6 md:px-6">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3">
          <BrandLogo className="h-10 w-auto" aria-hidden="true" focusable="false" />
          <span className="sr-only">BeatHub home</span>
        </Link>

        {/* Navigation */}
        <nav className="ml-4 flex flex-1 justify-center" aria-label="Primary">
          <ul className="flex shrink-0 items-center gap-2 overflow-x-auto whitespace-nowrap text-sm font-medium md:gap-3">
            {links.map((link) => (
              <li key={link.to}>
                <NavLink
                  to={link.to}
                  className={({ isActive }) =>
                    `inline-flex items-center rounded-full px-4 py-2 transition duration-200 ${
                      isActive
                        ? "bg-slate-900 text-white shadow-sm shadow-slate-900/20 dark:bg-white dark:text-slate-900"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Right side */}
        <div className="ml-4 flex items-center gap-3">
          <DownloadStatusIndicator />
          {user ? (
            <>
              <div className="flex items-center gap-2 text-sm font-medium md:hidden">
                <Link
                  to="/settings"
                  className="rounded-full border border-slate-200 px-3 py-1 text-slate-600 transition hover:border-brand-500 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-brandDark-400 dark:hover:text-brandDark-200"
                >
                  Settings
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="rounded-full border border-slate-200 px-3 py-1 text-slate-600 transition hover:border-brand-500 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-brandDark-400 dark:hover:text-brandDark-200"
                >
                  Logout
                </button>
              </div>
              <div className="hidden items-center gap-3 md:flex">
                <UserHoverPanel email={email} onLogout={handleLogout} />
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3 text-sm font-medium">
              <Link
                to="/login"
                className="rounded-full border border-transparent px-3 py-1 text-slate-600 transition hover:text-brand-700 dark:text-slate-200 dark:hover:text-brandDark-200"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="rounded-full bg-brand-600 px-3 py-1 text-white transition hover:bg-brand-500 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
              >
                Create account
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
