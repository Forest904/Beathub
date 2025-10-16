import React from 'react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-brand-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300 border-t border-brand-100 dark:border-transparent">
      <div className="container mx-auto px-4 py-6 text-center">
        <p className="text-sm md:text-base">
          &copy; {currentYear} BeatHub. The hub for your beats.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
