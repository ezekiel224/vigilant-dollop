# music-autodl

A fully hands-off music recommendation and auto-download system. Ingests your listening history from **Plex, Last.fm, Spotify, and TIDAL**, finds similar artists you don't have yet, and queues every album for download through **Tidarr** automatically.

```
Plex library ──┐
Last.fm      ──┼─► Recommender ─► Filter ─► Score ─► Tidarr ─► Tidal ─► /music
Spotify      ──┤   (similar              (not in           (queue
TIDAL favs   ──┘    artists)              library)          albums)
```

---

## How it works

1. **Seed collection** — pulls your artists from every enabled source
2. **Expansion** — for each seed, fetches similar artists via Last.fm and TIDAL's own similarity engine
3. **Filtering** — removes anything already in your Plex library or previously queued
4. **Scoring** — ranks candidates by how many sources agree on them × their similarity score
5. **Downloading** — queues each new artist's albums in Tidarr one album at a time (for better error isolation)
6. **Persistence** — remembers what was queued so it never re-downloads

---

## Quick start

### 1. Copy and fill in the env file

```bash
cp .env.example .env
nano .env   # fill in your keys
```

You only need to fill in the sources you want. Any source with an empty key is automatically skipped.

### 2. First-time OAuth flows

**Spotify** — on first run, a URL will be printed. Open it, log in, then paste the redirected URL back into the terminal. The token is cached at `/data/.spotify_cache` for future runs.

**TIDAL** — on first run, a URL will be printed. Open it in a browser and complete the login. The session is saved to `/data/tidal_session.json`.

### 3. Run once to test

```bash
# Preview candidates without downloading anything
python main.py --dry-run

# Run one full cycle
python main.py
```

### 4. Deploy with Docker

```bash
# Build and start (runs on schedule)
docker compose up -d --build

# Check logs
docker logs -f music-autodl
```

---

## API keys you need

| Source | Where to get it |
|---|---|
| **Plex** | Plex Web → Account → Plex token (see [Plex support](https://support.plex.tv/articles/204059436)) |
| **Last.fm** | [last.fm/api/account/create](https://www.last.fm/api/account/create) — free, instant |
| **Spotify** | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) → Create App → add `http://localhost:9090` as redirect URI |
| **TIDAL** | No key needed — uses device login (PKCE OAuth via tidalapi) |
| **Tidarr** | `docker exec tidarr cat /shared/.tidarr-api-key` |

---

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `TIDARR_URL` | `http://tidarr:8484` | Tidarr base URL |
| `TIDARR_KEY` | _(empty)_ | Tidarr API key |
| `PLEX_URL` | `http://localhost:32400` | Plex server URL |
| `PLEX_TOKEN` | _(empty)_ | Plex auth token — leave blank to disable |
| `PLEX_MUSIC_LIBRARY` | `Music` | Exact name of your music library in Plex |
| `LASTFM_API_KEY` | _(empty)_ | Last.fm API key — leave blank to disable |
| `LASTFM_USERNAME` | _(empty)_ | Last.fm username |
| `LASTFM_PERIOD` | `1month` | History period: `overall` `7day` `1month` `3month` `6month` `12month` |
| `SPOTIFY_CLIENT_ID` | _(empty)_ | Spotify app client ID — leave blank to disable |
| `SPOTIFY_CLIENT_SECRET` | _(empty)_ | Spotify app client secret |
| `TIDAL_ENABLED` | `true` | Set `false` to disable TIDAL |
| `SIMILAR_PER_ARTIST` | `10` | How many similar artists to fetch per seed |
| `MIN_SIMILARITY` | `0.3` | Last.fm similarity threshold (0–1) |
| `SKIP_EXISTING` | `true` | Skip artists already in Plex |
| `MAX_NEW_PER_RUN` | `0` | Cap new artists per run (0 = unlimited) |
| `SCHEDULE` | `0 3 * * *` | Cron schedule for daemon mode (UTC) |
| `LOG_LEVEL` | `INFO` | `INFO` or `DEBUG` |

---

## File layout

```
music-autodl/
├── main.py              # entry point + orchestration
├── config.py            # all configuration
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── core/
│   ├── seen_db.py       # persistent set of already-queued artists
│   ├── recommender.py   # aggregation, expansion, scoring
│   └── downloader.py    # Tidarr API client
└── sources/
    ├── plex.py          # Plex library reader
    ├── lastfm.py        # Last.fm top artists + similar
    ├── spotify.py       # Spotify top + followed artists
    └── tidal.py         # TIDAL favourites + similar
```

---

## Tips

**Too many downloads at once?** Set `MAX_NEW_PER_RUN=20` to cap each run. Combined with `SCHEDULE=0 3 * * *` it'll drip-feed 20 artists per night.

**Lower quality noise?** Raise `MIN_SIMILARITY=0.5` to only queue artists with a strong Last.fm similarity match.

**Just testing?** Run `python main.py --dry-run` to see the candidate list with scores without queuing anything.

**See what's been queued?** The seen DB is plain JSON at `SEEN_DB` path — you can view or edit it directly to un-queue an artist for re-download.
