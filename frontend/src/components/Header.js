import React from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle.jsx';
import CompilationToggle from '../compilation/CompilationToggle.jsx';
import { useAuth } from '../hooks/useAuth';

const NAV_LINKS = [
  { label: 'Discover', to: '/browse' },
  { label: 'Download', to: '/download' },
  { label: 'Burn', to: '/burn-cd' },
];

const Header = () => {
  const location = useLocation();
  const pathname = location.pathname || '';
  const showCompilation = /^\/(?:$|browse|artist\/|album\/)/.test(pathname);
  const { user, logout } = useAuth();
  const displayName = user
    ? (user.email && typeof user.email === 'string' && user.email.includes('@')
        ? user.email.split('@')[0]
        : user.username || user.name || '')
    : '';

  const handleLogout = async () => {
    await logout();
  };

  const links = NAV_LINKS.filter((link) => (user ? true : link.to !== '/download'));

  return (
  <header className="relative bg-white text-slate-900 shadow dark:bg-slate-950 dark:text-slate-100 border-b border-brand-100 dark:border-transparent">
    <div className="container mx-auto px-4">
      <div className="flex items-center justify-between py-6">
        {/* Left: Brand */}
        <div className="min-w-0">
          <Link
            to="/"
            className="inline-flex items-center gap-3 text-3xl font-semibold tracking-tight text-brand-800 transition hover:text-brand-700 dark:text-slate-100 dark:hover:text-slate-300"
          >
            <span>BeatHub</span>
          </Link>
        </div>

        {/* Center: Navigation */}
        <div className="mx-4 flex flex-1 justify-center">
          <nav aria-label="Primary">
            <ul className="flex items-center gap-2 text-sm font-medium md:gap-4 md:text-base">
              {links.map((link) => (
                <li key={link.to}>
                  <NavLink
                    to={link.to}
                    className={({ isActive }) =>
                      `block rounded-full px-4 py-2 transition duration-200 ${
                        isActive
                          ? 'bg-brand-100 text-brand-800 ring-1 ring-brand-300 dark:bg-brandDark-900/50 dark:text-brandDark-200 dark:ring-brandDark-400/40'
                          : 'text-slate-700 hover:bg-brand-50 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
                      }`
                    }
                  >
                    {link.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        {/* Right: Compilation (discovery only) + Theme toggle */}
        <div className="flex items-center gap-3">
          {showCompilation && user && <CompilationToggle />}
          <ThemeToggle />
          {user ? (
            <div className="flex items-center gap-2">
              <span className="hidden text-sm text-slate-600 dark:text-slate-200 sm:inline">
                {displayName || 'User'}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-full border border-slate-200 px-3 py-1 text-sm font-medium text-slate-600 transition hover:border-brand-500 hover:text-brand-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-brandDark-400 dark:hover:text-brandDark-200"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm font-medium">
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
    </div>
  </header>
);
}

export default Header;
