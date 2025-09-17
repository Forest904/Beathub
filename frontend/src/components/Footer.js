import React from 'react';
import { Link, NavLink } from 'react-router-dom';

const FOOTER_LINKS = [
  { label: 'Artists', to: '/browse' },
  { label: 'Download', to: '/download' },
  { label: 'Burner', to: '/burn-cd' },
];

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative isolate overflow-hidden bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-slate-200 shadow-lg">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,rgba(56,189,248,0.2),transparent_62%)]"
        aria-hidden
      />
      <div className="container relative z-10 mx-auto px-4 py-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <Link
              to="/"
              className="inline-flex items-center gap-3 text-lg font-semibold text-white transition hover:text-sky-200"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-sky-500/10 text-xl text-sky-300 ring-1 ring-inset ring-sky-400/40">
                💿
              </span>
              <span>CD Collector</span>
            </Link>
            <p className="text-sm text-slate-300 md:text-base">
              © {currentYear} CD Collector. Built for music lovers everywhere.
            </p>
          </div>
          <nav aria-label="Footer">
            <ul className="flex flex-wrap items-center gap-2 text-sm font-medium md:justify-end md:gap-4">
              {FOOTER_LINKS.map((link) => (
                <li key={link.to}>
                  <NavLink
                    to={link.to}
                    className={({ isActive }) =>
                      `rounded-full px-4 py-2 transition duration-200 ${
                        isActive
                          ? 'bg-slate-800/80 text-sky-200 ring-1 ring-sky-400/60'
                          : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
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
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/70 to-transparent"
        aria-hidden
      />
    </footer>
  );
};

export default Footer;
