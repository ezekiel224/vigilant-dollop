"""
sources/tidal.py — pull favourite artists from TIDAL and expand via similar artists.

tidalapi uses PKCE OAuth. On first run it will print a URL; open it in a
browser, complete login, and the session is saved to TIDAL_SESSION_FILE.
Subsequent runs load from the file and auto-refresh the token.
"""
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def _get_session(cfg):
    """Return an authenticated tidalapi.Session, loading from file if possible."""
    try:
        import tidalapi
    except ImportError:
        log.error("tidalapi not installed — pip install tidalapi")
        return None

    session      = tidalapi.Session()
    session_file = Path(cfg.tidal.session_file)
    session_file.parent.mkdir(parents=True, exist_ok=True)

    # Try loading existing session
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
            loaded = session.load_oauth_session(
                token_type=data["token_type"],
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expiry_time=data.get("expiry_time"),
            )
            if loaded and session.check_login():
                log.info("Tidal: session loaded from %s", session_file)
                return session
            log.info("Tidal: stored session expired, re-authenticating")
        except Exception as exc:
            log.warning("Tidal: could not load session file (%s)", exc)

    # First-time / expired: PKCE login (prints a URL)
    log.info("Tidal: starting PKCE login — open the URL below in a browser")
    try:
        login_url, future = session.pkce_login_url()
        print(f"\n  ▶ Open this URL in a browser to authorise TIDAL:\n  {login_url}\n")
        # Wait for the OAuth callback
        future.result()
        # Persist the session
        session_data = {
            "token_type":    session.token_type,
            "access_token":  session.access_token,
            "refresh_token": session.refresh_token,
            "expiry_time":   session.expiry_time.isoformat() if session.expiry_time else None,
        }
        session_file.write_text(json.dumps(session_data, indent=2))
        log.info("Tidal: session saved to %s", session_file)
        return session
    except Exception as exc:
        log.error("Tidal: login failed — %s", exc)
        return None


def get_favorite_artists(cfg) -> list[str]:
    """Return names of all TIDAL-favourite artists."""
    if not cfg.tidal.enabled:
        log.info("Tidal: disabled")
        return []

    session = _get_session(cfg)
    if not session:
        return []

    try:
        favs    = session.user.favorites
        artists = favs.artists()
        names   = [a.name for a in artists if a.name]
        log.info("Tidal: fetched %d favourite artists", len(names))
        return names
    except Exception as exc:
        log.error("Tidal: could not fetch favourites — %s", exc)
        return []


def get_similar_artists(artist_name: str, cfg, limit: int = 10) -> list[dict]:
    """
    Use TIDAL's own 'similar artists' feature.
    Returns list of dicts: {"name": str, "match": float, "source": "tidal"}
    """
    session = _get_session(cfg)
    if not session:
        return []

    try:
        # Search for the artist on TIDAL first
        results = session.search(artist_name, models=[session.artist.__class__])
        artist_results = results.get("artists") or []
        if not artist_results:
            return []

        tidal_artist = artist_results[0]

        try:
            similar = tidal_artist.get_similar()
            names = [a.name for a in (similar or []) if a.name][:limit]
            return [{"name": n, "match": 0.5, "source": "tidal"} for n in names]
        except Exception:
            return []

    except Exception as exc:
        log.warning("Tidal: similar artists lookup failed for %r — %s", artist_name, exc)
        return []
