"""
sources/lastfm.py — pull top artists from scrobble history and expand via similar artists.
"""
import logging
import requests

log = logging.getLogger(__name__)

LASTFM_API = "https://ws.audioscrobbler.com/2.0/"


def _call(params: dict) -> dict:
    params["format"] = "json"
    try:
        r = requests.get(LASTFM_API, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("Last.fm API error: %s", exc)
        return {}


def get_top_artists(cfg) -> list[str]:
    """Return the user's most-scrobbled artists over the configured period."""
    if not cfg.lastfm.enabled:
        log.info("Last.fm: disabled")
        return []

    data = _call({
        "method":  "user.getTopArtists",
        "user":    cfg.lastfm.username,
        "period":  cfg.lastfm.period,
        "limit":   cfg.lastfm.top_limit,
        "api_key": cfg.lastfm.api_key,
    })

    artists = []
    for a in data.get("topartists", {}).get("artist", []):
        name = a.get("name", "").strip()
        if name:
            artists.append(name)

    log.info("Last.fm: fetched %d top artists (period=%s)", len(artists), cfg.lastfm.period)
    return artists


def get_similar_artists(artist_name: str, api_key: str, limit: int = 10, min_match: float = 0.3) -> list[dict]:
    """
    Returns list of dicts: {"name": str, "match": float, "source": "lastfm"}
    """
    data = _call({
        "method":      "artist.getSimilar",
        "artist":      artist_name,
        "autocorrect": 1,
        "limit":       limit * 3,   # fetch extra to allow filtering by min_match
        "api_key":     api_key,
    })

    results = []
    for a in data.get("similarartists", {}).get("artist", []):
        name  = a.get("name", "").strip()
        match = float(a.get("match", 0))
        if name and match >= min_match:
            results.append({"name": name, "match": match, "source": "lastfm"})

    # sort by match descending, take top `limit`
    results.sort(key=lambda x: x["match"], reverse=True)
    return results[:limit]
