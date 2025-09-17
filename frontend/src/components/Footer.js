import React from 'react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-slate-900 text-slate-200">
      <div className="container mx-auto px-4 py-6 text-center">
        <p className="text-sm md:text-base">
          &copy; {currentYear} CD Collector. Built for music lovers everywhere.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
