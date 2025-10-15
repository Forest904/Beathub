#!/usr/bin/env python
"""
Centralized configuration schema and SpotDL settings loader.

Merges defaults from config.Config with environment variables and
provides helpers to build SpotDL downloader options.
"""

from __future__ import annotations

import os
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from config import Config


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _parse_audio_providers(value: Optional[object]) -> List[str]:
    """Normalize audio provider configuration into a unique ordered list with safe fallbacks."""
    if value is None:
        tokens: List[str] = []
    elif isinstance(value, str):
        tokens = [token.strip() for token in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        tokens = [str(token).strip() for token in value]
    else:
        tokens = [str(value).strip()]

    aliases = {
        "ytmusic": "youtube-music",
        "youtube music": "youtube-music",
        "yt music": "youtube-music",
        "yt": "youtube",
        "yt-dlp": "youtube",
    }
    normalized: List[str] = []
    for token in tokens:
        if not token:
            continue
        key = token.lower()
        key = aliases.get(key, key)
        if key and key not in normalized:
            normalized.append(key)

    if not normalized:
        normalized = ["youtube-music", "youtube"]
    else:
        # Always keep a general YouTube fallback so SpotDL can retry when music-only links fail.
        if "youtube" not in normalized:
            normalized.append("youtube")

    return normalized

class AppSettings(BaseModel):
    """Application-wide settings with SpotDL-related options."""

    # App
    base_output_dir: str = Field(default=Config.BASE_OUTPUT_DIR)

    # Spotify credentials
    spotify_client_id: Optional[str] = Field(default=Config.SPOTIPY_CLIENT_ID)
    spotify_client_secret: Optional[str] = Field(default=Config.SPOTIPY_CLIENT_SECRET)

    # SpotDL downloader options
    audio_providers: List[str] = Field(default_factory=lambda: _parse_audio_providers(Config.SPOTDL_AUDIO_SOURCE))
    format: str = Field(default=Config.SPOTDL_FORMAT)
    threads: int = Field(default=Config.SPOTDL_THREADS)
    overwrite: str = Field(default="skip")
    preload: bool = Field(default=_env_bool("SPOTDL_PRELOAD", False))
    filter_results: bool = Field(default=_env_bool('SPOTDL_FILTER_RESULTS', True))
    cookie_file: Optional[str] = Field(default=os.getenv('SPOTDL_COOKIE_FILE'))
    yt_dlp_args: Optional[str] = Field(default=os.getenv('SPOTDL_YTDLP_ARGS'))

    # Lyrics via SpotDL providers (we'll favor Genius if token present)
    lyrics_providers: List[str] = Field(
        default_factory=lambda: ["genius"] if Config.GENIUS_ACCESS_TOKEN else []
    )
    genius_token: Optional[str] = Field(default=Config.GENIUS_ACCESS_TOKEN)

    # Subprocess/console output suppression for SpotDL + children
    suppress_subprocess_output: bool = Field(default=_env_bool("SPOTDL_SUPPRESS_OUTPUT", False))

    @field_validator("overwrite")
    @classmethod
    def _validate_overwrite(cls, v: str) -> str:
        allowed = {"skip", "force", "metadata"}
        if v not in allowed:
            return "skip"
        return v

    @field_validator("audio_providers", mode="before")
    @classmethod
    def _normalize_audio_providers(cls, value):
        return _parse_audio_providers(value)


def load_app_settings() -> AppSettings:
    """Load settings merging config defaults with environment overrides."""
    return AppSettings()


def build_spotdl_downloader_options(settings: AppSettings):
    """Construct SpotDL DownloaderOptionalOptions from AppSettings.

    Note: This import is local to avoid importing spotdl at module import time
    if not installed, and to keep this helper optional until the refactor path
    is enabled.
    """

    # Avoid import-time errors if spotdl is not yet installed at runtime
    try:
        from spotdl.types.options import DownloaderOptionalOptions
    except Exception:  # pragma: no cover - exercised via tests without spotdl
        class DownloaderOptionalOptions:  # type: ignore
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

    return DownloaderOptionalOptions(
        output=None,
        format=settings.format,
        audio_providers=settings.audio_providers,
        threads=settings.threads,
        overwrite=settings.overwrite,
        lyrics_providers=settings.lyrics_providers,
        preload=settings.preload,
        genius_token=settings.genius_token,
        filter_results=settings.filter_results,
        cookie_file=settings.cookie_file,
        yt_dlp_args=settings.yt_dlp_args,
    )


__all__ = [
    "AppSettings",
    "load_app_settings",
    "build_spotdl_downloader_options",
]
