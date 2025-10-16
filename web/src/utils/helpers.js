// web/src/utils/helpers.js
export const formatDuration = (ms) => {
    if (ms === undefined || ms === null) return 'N/A';
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(0);
    return minutes + ":" + (seconds < 10 ? '0' : '') + seconds;
};
