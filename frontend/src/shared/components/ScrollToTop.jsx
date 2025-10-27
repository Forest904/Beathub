import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const ScrollToTop = () => {
  const location = useLocation();

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const { history } = window;
    if (!history || !('scrollRestoration' in history)) {
      return undefined;
    }

    const originalRestoration = history.scrollRestoration;
    history.scrollRestoration = 'manual';

    return () => {
      history.scrollRestoration = originalRestoration;
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const scrollToTop = () => {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      window.scrollTo(0, 0);
    };

    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(scrollToTop);
    } else {
      scrollToTop();
    }
  }, [location.pathname, location.search]);

  return null;
};

export default ScrollToTop;
