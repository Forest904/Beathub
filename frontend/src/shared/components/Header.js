import React from "react";
import { Link, NavLink } from "react-router-dom";
import ThemeToggle from "./ThemeToggle.jsx";
import UserHoverPanel from "./UserHoverPanel.jsx";
import { useAuth } from "../hooks/useAuth";

const NAV_LINKS = [
  { label: "Discover", to: "/browse" },
  { label: "Download", to: "/download" },
  { label: "Burn", to: "/burn-cd" },
];

const Header = () => {
  const { user, logout } = useAuth();
  const email = user && typeof user.email === "string" ? user.email : "";

  const handleLogout = async () => {
    await logout();
  };

  const links = user ? NAV_LINKS : NAV_LINKS.filter((link) => link.to !== "/download");

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 text-slate-900 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80 dark:text-slate-100">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-4 md:gap-6 md:px-6">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3">
          <span className="text-3xl text-slate-900 transition-colors dark:text-white">
            <svg
              aria-hidden="true"
              className="h-7 w-7"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 3v11.5a3 3 0 1 1-2-2.83V5.5l10-2v9.96a3 3 0 1 1-2-2.83V4.25L9 5.5" />
            </svg>
          </span>
          <div className="flex flex-col">
            <span className="text-xl font-semibold tracking-tight md:text-2xl">BeatHub</span>
          </div>
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
          {user ? (
            <>
              <div className="flex items-center gap-2 text-sm font-medium md:hidden">
                <ThemeToggle />
                <Link
                  to="/account"
                  className="rounded-full border border-slate-200 px-3 py-1 text-slate-600 transition hover:border-brand-500 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-brandDark-400 dark:hover:text-brandDark-200"
                >
                  Account
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
                <ThemeToggle />
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3 text-sm font-medium">
              <ThemeToggle />
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
