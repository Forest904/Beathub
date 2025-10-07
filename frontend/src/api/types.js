/**
 * @typedef {Object} DownloadItem
 * @property {number} id
 * @property {string} spotify_id
 * @property {string} title
 * @property {string} artist
 * @property {string|null} image_url
 * @property {string|null} spotify_url
 * @property {string|null} local_path
 * @property {boolean} is_favorite
 * @property {string} item_type
 */

/**
 * @typedef {Object} DownloadJob
 * @property {string} job_id
 * @property {string} link
 * @property {string} status
 * @property {number} attempts
 * @property {Object|null} result
 * @property {string|null} error
 */

/**
 * @typedef {Object} ArtistSummary
 * @property {string} id
 * @property {string} name
 * @property {string[]} genres
 * @property {number} followers
 * @property {number} popularity
 * @property {boolean} followers_available
 * @property {boolean} popularity_available
 * @property {string|null} image
 * @property {string|null} external_urls
 */

/**
 * @typedef {Object} Pagination
 * @property {number} page
 * @property {number} limit
 * @property {number} total
 * @property {number} total_pages
 * @property {boolean} has_next
 * @property {boolean} has_prev
 */

/**
 * @typedef {Object} BurnerStatus
 * @property {string|null} session_id
 * @property {boolean} is_burning
 * @property {string} current_status
 * @property {number} progress_percentage
 * @property {string|null} last_error
 * @property {boolean} burner_detected
 * @property {boolean} disc_present
 * @property {boolean} disc_blank_or_erasable
 */

export {}; // JSDoc-only module for editor intellisense.
