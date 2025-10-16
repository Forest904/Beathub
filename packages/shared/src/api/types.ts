export interface DownloadItem {
  id: number;
  spotify_id: string;
  name: string;
  title: string;
  artist: string;
  image_url: string | null;
  spotify_url: string | null;
  local_path: string | null;
  is_favorite: boolean;
  item_type: string;
}

export interface DownloadJob {
  job_id: string;
  link: string;
  status: string;
  attempts: number;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface ArtistSummary {
  id: string;
  name: string;
  genres: string[];
  followers: number;
  popularity: number;
  followers_available: boolean;
  popularity_available: boolean;
  image: string | null;
  external_urls: Record<string, unknown> | null;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface BurnerStatus {
  session_id: string | null;
  is_burning: boolean;
  current_status: string;
  progress_percentage: number;
  last_error: string | null;
  burner_detected: boolean;
  disc_present: boolean;
  disc_blank_or_erasable: boolean;
}

export interface PaginatedArtists {
  artists: ArtistSummary[];
  pagination: Partial<Pagination>;
}
