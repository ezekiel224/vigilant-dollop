"""
sources/spotify.py — pull top artists and followed artists from Spotify.

Auth note: Spotipy uses Authorization Code Flow which requires a one-time
browser redirect. On first run the user visits a URL, pastes back the
redirect URL, and the token is cached. After that it refreshes automatically.

Set SPOTIFY_REDIRECT_URI in your env (e.g. http://localhost:9090) and add it
to your Spotify app's allowed redirect URIs in the developer dashboard.
"""
import logging
import os

log = logging.getLogger(__name__)


def get_top_artists(cfg) -> list[str]:
    """Return user's top Spotify artists."""
    if not cfg.spotify.enabled:
        log.info("Spotify: disabled")
        return []

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        log.error("spotipy not installed — pip install spotipy")
        return []

    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=cfg.spotify.client_id,
            client_secret=cfg.spotify.client_secret,
            redirect_uri=cfg.spotify.redirect_uri,
            scope=cfg.spotify.scope,
            cache_path="/data/.spotify_cache",
            open_browser=False,
        ))

        artists = []

        # Top artists across all three time ranges for maximum coverage
        for time_range in ["short_term", "medium_term", "long_term"]:
            result = sp.current_user_top_artists(limit=cfg.spotify.top_limit, time_range=time_range)
            for item in (result or {}).get("items", []):
                name = item.get("name", "").strip()
                if name and name not in artists:
                    artists.append(name)

        # Also pull followed artists
        result = sp.current_user_followed_artists(limit=50)
        while result:
            for item in result.get("artists", {}).get("items", []):
                name = item.get("name", "").strip()
                if name and name not in artists:
                    artists.append(name)
            # pagination
            next_url = result.get("artists", {}).get("next")
            result   = sp.next(result.get("artists")) if next_url else None

        log.info("Spotify: fetched %d unique artists", len(artists))
        return artists

    except Exception as exc:
        log.error("Spotify: error — %s", exc)
        return []
