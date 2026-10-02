# Hacking on yomi-cli

Yomi CLI has two runtime components:

- `yomi-cli`: the POSIX shell command that searches, selects episodes, resolves sources, manages playback, and stores history/settings.
- `yomi-relay.py`: a loopback HTTP relay for Yomi/MegaPlay HLS playlists, wrapped MPEG-TS segments, and WebVTT subtitle tracks.

## Prerequisites

Install a POSIX shell, `curl`, `sed`, `grep`, `jq`, `fzf`, Python 3, OpenSSL, and a media player such as mpv or VLC. `yt-dlp` and `ffmpeg` are needed only for downloads.

## Provider flow

The normal playback path is:

1. Search AniList through its GraphQL API.
2. Convert the selected AniList entry into a Yomi slug.
3. Resolve the corresponding MAL identifier for MegaPlay.
4. Open the MegaPlay embed for the selected episode and mode.
5. Resolve the source JSON into an HLS master playlist and subtitle tracks.
6. Select quality and the persisted subtitle preference.
7. Start the relay when the selected player needs local HTTP access.
8. Launch the player and queue menu actions until the current player exits.

When changing a provider endpoint, verify search, episode enumeration, source resolution, subtitle retrieval, and the next/replay/previous transitions separately.

## Shell conventions

- Keep `yomi-cli` POSIX `sh`; do not rely on Bash arrays, process substitution, or Bash-only conditionals.
- Keep external parsing boring and explicit. `jq`, `sed`, `grep`, and `cut` are already project dependencies.
- Preserve cleanup behavior on normal exit, quit, and signals.
- Track the media-player process separately from the relay process. The relay must not make episode transitions wait forever.
- Keep persisted settings under the configured history directory.

## Relay conventions

The relay must:

- send the provider user-agent and MegaPlay referer upstream;
- rewrite relative HLS playlist URLs to loopback URLs;
- strip the provider's image wrapper from MPEG-TS segments;
- normalize MPEG-TS PTS, DTS, and PCR when the CDN starts segments at a non-zero timestamp;
- serve WebVTT with `text/vtt` content type;
- terminate promptly when yomi-cli cleans up.

Test the relay with an actual playlist, at least one segment, and a subtitle track. A successful HTTP response alone is insufficient; validate media timestamps and the `WEBVTT` header.

## Verification

Run the focused checks after changes:

```sh
sh -n yomi-cli
python3 -m py_compile yomi-relay.py
```

Then exercise the changed path against a real episode with a local player or a controlled player wrapper. Do not commit generated `__pycache__` files.

See [ATTRIBUTION.md](ATTRIBUTION.md) for the project's ani-cli credit and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution requirements.
