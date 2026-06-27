"""
sources/plex.py — pull artists from your Plex music library.

Returns:
  seed_artists  — all artists already in Plex (used to skip re-downloads AND as seeds)
  recommendations — artists similar to your library (via Last.fm, called here so
                    we can cross-reference against library in one place)
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)


def get_library_artists(cfg) -> list[str]:
    """Return all artist names currently in the Plex music library."""
    if not cfg.plex.enabled:
        log.info("Plex: disabled (no PLEX_TOKEN set)")
        return []

    try:
        from plexapi.server import PlexServer
    except ImportError:
        log.error("plexapi not installed — pip install plexapi")
        return []

    try:
        plex   = PlexServer(cfg.plex.url, cfg.plex.token)
        music  = plex.library.section(cfg.plex.library_name)
        artists = [a.title for a in music.all(libtype="artist")]
        log.info("Plex: found %d artists in library '%s'", len(artists), cfg.plex.library_name)
        return artists
    except Exception as exc:
        log.error("Plex: failed to fetch library — %s", exc)
        return []
