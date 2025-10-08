export const FAVORITE_TOKENS = Object.freeze({
  icon: Object.freeze({
    active: '★',
    inactive: '☆',
  }),
  iconClasses: Object.freeze({
    base: 'transition-colors duration-150 ease-in-out text-2xl',
    active: 'text-brandWarning-500 drop-shadow-sm dark:text-brandWarning-300',
    inactive: 'text-slate-400 hover:text-brandWarning-400 dark:text-gray-500 dark:hover:text-brandWarning-400',
  }),
  badgeClasses: Object.freeze({
    base: 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide',
    active: 'bg-brandWarning-100 text-brandWarning-700 dark:bg-brandWarning-700/30 dark:text-brandWarning-300',
    inactive: 'bg-slate-200 text-slate-600 dark:bg-gray-700 dark:text-gray-300',
  }),
});

export const FAVORITE_TYPES = Object.freeze(['artist', 'album', 'track']);

export default FAVORITE_TOKENS;
