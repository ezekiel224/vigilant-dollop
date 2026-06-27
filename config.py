"""
music-autodl — configuration
All settings are read from environment variables or a .env file.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlexConfig:
    url:            str = os.getenv("PLEX_URL",   "http://localhost:32400")
    token:          str = os.getenv("PLEX_TOKEN", "")
    library_name:   str = os.getenv("PLEX_MUSIC_LIBRARY", "Music")
    enabled:        bool = bool(os.getenv("PLEX_TOKEN"))


@dataclass
class LastFmConfig:
    api_key:        str = os.getenv("LASTFM_API_KEY",  "")
    username:       str = os.getenv("LASTFM_USERNAME", "")
    # How far back to look: overall | 7day | 1month | 3month | 6month | 12month
    period:         str = os.getenv("LASTFM_PERIOD",   "1month")
    top_limit:      int = int(os.getenv("LASTFM_TOP_LIMIT", "50"))
    enabled:        bool = bool(os.getenv("LASTFM_API_KEY") and os.getenv("LASTFM_USERNAME"))


@dataclass
class SpotifyConfig:
    client_id:      str = os.getenv("SPOTIFY_CLIENT_ID",     "")
    client_secret:  str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    redirect_uri:   str = os.getenv("SPOTIFY_REDIRECT_URI",  "http://localhost:9090")
    # Scope needed to read top artists and recently played
    scope:          str = "user-top-read user-read-recently-played user-follow-read"
    time_range:     str = os.getenv("SPOTIFY_TIME_RANGE", "medium_term")  # short_term / medium_term / long_term
    top_limit:      int = int(os.getenv("SPOTIFY_TOP_LIMIT", "50"))
    enabled:        bool = bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET"))


@dataclass
class TidalConfig:
    # tidalapi uses PKCE OAuth — session is stored in a file after first login
    session_file:   str = os.getenv("TIDAL_SESSION_FILE", "/data/tidal_session.json")
    enabled:        bool = bool(os.getenv("TIDAL_ENABLED", "true").lower() in ("1", "true", "yes"))


@dataclass
class TidarrConfig:
    url:            str = os.getenv("TIDARR_URL",  "http://tidarr:8484")
    api_key:        str = os.getenv("TIDARR_KEY",  "")
    enabled:        bool = True


@dataclass
class RecommendationConfig:
    # Number of similar artists to fetch per seed artist
    similar_per_artist:     int = int(os.getenv("SIMILAR_PER_ARTIST",   "10"))
    # Minimum Last.fm similarity score (0-1) to include
    min_similarity:         float = float(os.getenv("MIN_SIMILARITY",    "0.3"))
    # Skip artists already in Plex
    skip_existing:          bool = os.getenv("SKIP_EXISTING", "true").lower() in ("1", "true", "yes")
    # How many new artists to download per run (0 = unlimited)
    max_new_per_run:        int = int(os.getenv("MAX_NEW_PER_RUN", "0"))
    # Cron-style schedule (used in Docker). Default: 3am daily
    schedule:               str = os.getenv("SCHEDULE", "0 3 * * *")
    # Path where we persist what we've already downloaded
    seen_db:                str = os.getenv("SEEN_DB", "/data/seen_artists.json")


@dataclass
class AppConfig:
    plex:           PlexConfig           = field(default_factory=PlexConfig)
    lastfm:         LastFmConfig         = field(default_factory=LastFmConfig)
    spotify:        SpotifyConfig        = field(default_factory=SpotifyConfig)
    tidal:          TidalConfig          = field(default_factory=TidalConfig)
    tidarr:         TidarrConfig         = field(default_factory=TidarrConfig)
    rec:            RecommendationConfig = field(default_factory=RecommendationConfig)
    log_level:      str = os.getenv("LOG_LEVEL", "INFO")


# Singleton
cfg = AppConfig()
