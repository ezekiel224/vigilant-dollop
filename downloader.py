"""
core/downloader.py — search Tidal via Tidarr for an artist's albums
and queue each one for download.

Strategy:
  1. Search Tidarr /api/search for the artist
  2. Fetch the artist's albums from Tidal via Tidarr search or tidalapi
  3. POST each album to Tidarr /api/save
"""
import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)


class TidarrDownloader:

    def __init__(self, cfg):
        self.url     = cfg.tidarr.url.rstrip("/")
        self.api_key = cfg.tidarr.api_key
        self.cfg     = cfg

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-Api-Key"] = self.api_key
        return h

    def _get(self, path: str, params: dict = None) -> Optional[dict]:
        try:
            r = requests.get(
                f"{self.url}{path}",
                params=params or {},
                headers=self._headers(),
                timeout=15,
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            log.warning("Tidarr GET %s failed: %s", path, exc)
            return None

    def _post(self, path: str, payload: dict) -> bool:
        try:
            r = requests.post(
                f"{self.url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            r.raise_for_status()
            return True
        except Exception as exc:
            log.warning("Tidarr POST %s failed: %s", path, exc)
            return False

    def _search(self, query: str, search_type: str = "artist") -> list:
        """Query Tidarr's Tidal search endpoint."""
        data = self._get("/api/search", {"query": query, "type": search_type})
        if not data:
            return []
        # Tidarr returns a list or an object with a typed key
        if isinstance(data, list):
            return data
        # May be wrapped: {"artists": [...], "albums": [...]}
        return data.get(search_type + "s", data.get(search_type, []))

    def queue_artist_albums(self, artist_name: str) -> int:
        """
        Find the artist on Tidal, then queue each studio album.
        Returns number of albums queued.
        """
        log.info("⬇  Queuing albums for: %s", artist_name)

        # ── 1. Find artist on Tidal ──────────────────────────────────────
        results = self._search(artist_name, "artist")
        if not results:
            log.warning("  No Tidal results for artist: %s", artist_name)
            return 0

        # Pick the best match (first result)
        artist    = results[0]
        artist_id = artist.get("id")
        if not artist_id:
            log.warning("  Could not parse artist ID from search result")
            return 0

        tidal_artist_url = f"https://listen.tidal.com/artist/{artist_id}"
        log.debug("  Resolved to Tidal artist URL: %s", tidal_artist_url)

        # ── 2. Get artist's albums ────────────────────────────────────────
        # Prefer fetching album list via tidalapi for richness;
        # fall back to queuing the artist URL directly (Tidarr will expand it)
        albums_queued = self._queue_via_albums(artist_id, artist_name)
        if albums_queued == 0:
            # Fallback: queue the artist URL and let Tidarr handle expansion
            log.info("  Falling back to artist-level queue")
            ok = self._post("/api/save", {
                "item": {
                    "url":    tidal_artist_url,
                    "type":   "artist",
                    "status": "queue",
                }
            })
            return 1 if ok else 0

        return albums_queued

    def _queue_via_albums(self, artist_id: int, artist_name: str) -> int:
        """
        Fetch all studio albums for the artist via tidalapi and queue each separately.
        This gives Tidarr per-album granularity and better error isolation.
        """
        try:
            import tidalapi
            from sources.tidal import _get_session
        except ImportError:
            return 0

        session = _get_session(self.cfg)
        if not session:
            return 0

        try:
            artist = session.artist(artist_id)
            albums = artist.get_albums()
        except Exception as exc:
            log.warning("  tidalapi album fetch failed for %s: %s", artist_name, exc)
            return 0

        queued = 0
        for album in albums:
            album_url = f"https://listen.tidal.com/album/{album.id}"
            log.debug("  Queuing album: %s – %s", artist_name, album.name)
            ok = self._post("/api/save", {
                "item": {
                    "url":    album_url,
                    "type":   "album",
                    "status": "queue",
                }
            })
            if ok:
                queued += 1

        log.info("  Queued %d albums for %s", queued, artist_name)
        return queued

    def health_check(self) -> bool:
        """Return True if Tidarr is reachable."""
        try:
            r = requests.get(f"{self.url}/api/settings", headers=self._headers(), timeout=5)
            return r.ok
        except Exception:
            return False
