import React from 'react';
import { Link, NavLink } from 'react-router-dom';

const NAV_LINKS = [
  { label: 'Artists', to: '/browse' },
  { label: 'Download', to: '/download' },
  { label: 'Burner', to: '/burn-cd' },
];

const Header = () => (
  <header className="relative isolate overflow-hidden bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-lg">
    <div
      className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.28),transparent_60%)]"
      aria-hidden
    />
    <div className="container relative z-10 mx-auto px-4">
      <div className="flex flex-col gap-6 py-6 md:flex-row md:items-center md:justify-between">
        <div>
          <Link
            to="/"
            className="group inline-flex items-center gap-3 text-3xl font-semibold tracking-tight text-white transition hover:text-sky-200"
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-sky-500/15 text-2xl text-sky-300 ring-1 ring-inset ring-sky-400/40 transition group-hover:bg-sky-500/25">
              💿
            </span>
            <span>CD Collector</span>
          </Link>
        </div>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:gap-8">
          <nav aria-label="Primary">
            <ul className="flex flex-col gap-2 text-sm font-medium md:flex-row md:items-center md:gap-4 md:text-base">
              {NAV_LINKS.map((link) => (
                <li key={link.to}>
                  <NavLink
                    to={link.to}
                    className={({ isActive }) =>
                      `block rounded-full px-4 py-2 transition duration-200 ${
                        isActive
                          ? 'bg-slate-800/90 text-sky-200 ring-1 ring-sky-400/60'
                          : 'text-slate-200 hover:bg-slate-800/60 hover:text-white'
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
      </div>
    </div>
    <div
      className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-sky-400/70 to-transparent"
      aria-hidden
    />
  </header>
);

export default Header;
