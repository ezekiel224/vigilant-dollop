"""
core/recommender.py — aggregate seed artists from all sources,
expand via similarity, deduplicate, score, and return ranked candidates.
"""
import logging
from collections import defaultdict
from typing import NamedTuple

log = logging.getLogger(__name__)


class Candidate(NamedTuple):
    name:       str
    score:      float       # higher = more sources / higher similarity
    sources:    list[str]   # which sources mentioned this artist


def build_recommendations(cfg, existing_artists: set[str]) -> list[Candidate]:
    """
    Full pipeline:
      1. Collect seed artists from Plex, Last.fm, Spotify, Tidal
      2. Use Last.fm + Tidal 'similar artist' to expand the seed list
      3. Filter out anything already in the library
      4. Score by how many sources agree on an artist
      5. Return ranked list of Candidate objects
    """
    from sources.plex    import get_library_artists
    from sources.lastfm  import get_top_artists as lfm_top, get_similar_artists as lfm_similar
    from sources.spotify import get_top_artists as sp_top
    from sources.tidal   import get_favorite_artists as tidal_favs, get_similar_artists as tidal_similar

    # ── Step 1: Gather seed artists ────────────────────────────────────────
    seeds: set[str] = set()

    plex_artists = get_library_artists(cfg)
    # Plex library is both the existing check AND seeds for similar-artist expansion
    seeds.update(plex_artists)
    existing_artists.update(a.lower() for a in plex_artists)

    for name in lfm_top(cfg):
        seeds.add(name)

    for name in sp_top(cfg):
        seeds.add(name)

    for name in tidal_favs(cfg):
        seeds.add(name)

    log.info("Recommender: %d unique seed artists collected", len(seeds))

    # ── Step 2: Expand via similarity ──────────────────────────────────────
    # votes[artist_lower] = list of (score, source_label)
    votes: dict[str, list[tuple[float, str]]] = defaultdict(list)

    seeds_list = list(seeds)
    total      = len(seeds_list)

    for i, seed in enumerate(seeds_list, 1):
        log.debug("Expanding %d/%d: %s", i, total, seed)

        # Last.fm similar
        if cfg.lastfm.enabled:
            for rec in lfm_similar(
                seed,
                cfg.lastfm.api_key,
                limit=cfg.rec.similar_per_artist,
                min_match=cfg.rec.min_similarity,
            ):
                votes[rec["name"].lower()].append((rec["match"], f"lastfm~{seed}"))

        # Tidal similar
        if cfg.tidal.enabled:
            for rec in tidal_similar(seed, cfg, limit=cfg.rec.similar_per_artist):
                votes[rec["name"].lower()].append((rec["match"], f"tidal~{seed}"))

    log.info("Recommender: %d candidate artists from similarity expansion", len(votes))

    # ── Step 3: Filter out existing library artists ────────────────────────
    filtered = {
        name: vote_list
        for name, vote_list in votes.items()
        if name not in existing_artists
    }

    log.info("Recommender: %d candidates after filtering library", len(filtered))

    # ── Step 4: Score and deduplicate ──────────────────────────────────────
    # Score = number of unique sources that mentioned this artist × average similarity
    candidates = []
    for name_lower, vote_list in filtered.items():
        unique_sources = list({v[1] for v in vote_list})
        avg_match      = sum(v[0] for v in vote_list) / len(vote_list)
        score          = len(unique_sources) * avg_match
        # Recover a properly-cased name from the first vote's source tag
        # (we store lower for dedup but want to display original casing)
        display_name   = vote_list[0][1]  # "lastfm~Radiohead" — extract original below
        # use the raw name from the vote source label isn't available here;
        # we'll re-lookup from votes dict which only has lowercased keys.
        # Instead we stored it: rebuild from original votes dict
        candidates.append(Candidate(
            name=_recover_name(name_lower, votes),
            score=score,
            sources=unique_sources,
        ))

    # Sort descending by score
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Optional cap
    if cfg.rec.max_new_per_run > 0:
        candidates = candidates[:cfg.rec.max_new_per_run]

    log.info("Recommender: returning %d ranked candidates", len(candidates))
    return candidates


# Helper — we store keys as lowercase for dedup, but want display casing.
# We cache the first-seen original casing when collecting.
_original_casing: dict[str, str] = {}


def register_casing(name: str):
    """Call this when we first see an artist name to preserve casing."""
    _original_casing[name.lower()] = name


def _recover_name(name_lower: str, votes: dict) -> str:
    return _original_casing.get(name_lower, name_lower.title())
