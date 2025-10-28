#!/usr/bin/env python
"""
Centralized configuration schema and SpotDL settings loader.

Merges defaults from config.Config with environment variables and
provides helpers to build SpotDL downloader options.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from config import Config


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _parse_audio_providers(value: Optional[object]) -> List[str]:
    """Normalize audio provider configuration into a unique ordered list."""
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
        if key not in normalized:
            normalized.append(key)
    if not normalized:
        return ["youtube-music"]
    return normalized


class AppSettings(BaseModel):
    """Application-wide settings with SpotDL-related options."""

    model_config = ConfigDict(extra="ignore")

    # App
    base_output_dir: str

    # Spotify credentials
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None

    # SpotDL downloader options
    audio_providers: List[str] = Field(default_factory=lambda: ["youtube-music"])
    format: str = "mp3"
    threads: int = 6
    overwrite: str = "skip"
    preload: bool = False
    simple_tui: bool = Field(default=Config.SPOTDL_SIMPLE_TUI)

    # Lyrics via SpotDL providers (we'll favor Genius if token present)
    lyrics_providers: List[str] = Field(default_factory=list)
    genius_token: Optional[str] = None

    # Subprocess/console output suppression for SpotDL + children
    suppress_subprocess_output: bool = True

    @field_validator("overwrite")
    @classmethod
    def _validate_overwrite(cls, value: str) -> str:
        allowed = {"skip", "force", "metadata"}
        if value not in allowed:
            return "skip"
        return value

    @field_validator("audio_providers", mode="before")
    @classmethod
    def _normalize_audio_providers(cls, value: Optional[object]) -> List[str]:
        return _parse_audio_providers(value)

    @field_validator("threads", mode="before")
    @classmethod
    def _coerce_threads(cls, value: object) -> int:
        try:
            threads = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 1
        return max(1, min(threads, 32))

    @field_validator("preload", mode="before")
    @classmethod
    def _coerce_preload(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
        return bool(value)


def load_app_settings(overrides: Optional[Dict[str, Any]] = None) -> AppSettings:
    """Load settings merging config defaults with optional runtime overrides."""
    data: Dict[str, Any] = {
        "base_output_dir": Config.BASE_OUTPUT_DIR,
        "spotify_client_id": Config.SPOTIPY_CLIENT_ID,
        "spotify_client_secret": Config.SPOTIPY_CLIENT_SECRET,
        "audio_providers": Config.SPOTDL_AUDIO_SOURCE,
        "format": Config.SPOTDL_FORMAT,
        "threads": Config.SPOTDL_THREADS,
        "preload": getattr(Config, "SPOTDL_PRELOAD", False),
        "simple_tui": getattr(Config, "SPOTDL_SIMPLE_TUI", True),
        "lyrics_providers": ["genius"] if Config.GENIUS_ACCESS_TOKEN else [],
        "genius_token": Config.GENIUS_ACCESS_TOKEN,
        "suppress_subprocess_output": _env_bool("SPOTDL_SUPPRESS_OUTPUT", True),
    }
    if overrides:
        data.update(overrides)
    return AppSettings.model_validate(data)


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
        simple_tui=settings.simple_tui,
        genius_token=settings.genius_token,
    )


__all__ = [
    "AppSettings",
    "load_app_settings",
    "build_spotdl_downloader_options",
]
