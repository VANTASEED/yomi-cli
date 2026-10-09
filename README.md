# yomi-cli

`yomi-cli` is a POSIX shell interface for searching and watching anime from the terminal. It uses [Yomi.to](https://yomi.to/) for metadata and [MegaPlay](https://megaplay.buzz/) for playback sources.

## Features

- Search anime through AniList metadata.
- Play subbed or dubbed episodes.
- Select video quality.
- Watch with mpv, VLC, IINA, Syncplay, or another URL-capable player.
- Choose subtitle tracks from the episode menu, disable subtitles, and persist the selection.
- Continue from history.
- Select individual episodes or ranges.
- Download episodes with `yt-dlp` or `ffmpeg`.
- Use `ani-skip` with mpv to skip openings when supported.
- Relay Yomi/MegaPlay HLS streams and WebVTT subtitles locally when required by the player.

## Installation

Install from a checked-out copy of this project:

```sh
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/man/man1"
install -m 755 yomi-cli "$HOME/.local/bin/yomi-cli"
install -m 755 yomi-relay.py "$HOME/.local/bin/yomi-relay.py"
install -m 644 yomi-cli.1 "$HOME/.local/share/man/man1/yomi-cli.1"
```

Ensure `$HOME/.local/bin` is in `PATH`, then run:

```sh
yomi-cli --help
yomi-cli "smoking behind the supermarket with you"
```

For a system-wide installation, replace the destination directories with `/usr/local/bin` and `/usr/local/share/man/man1` and run the install commands with appropriate permissions.

Yomi CLI does not publish distro packages in this repository. Install the dependencies for your platform, then use the source-install commands above.

### Debian and Ubuntu

```sh
sudo apt update
sudo apt install curl grep sed jq fzf mpv python3 ffmpeg openssl
```

Install `yt-dlp` separately if you want the download command and it is not available from your release:

```sh
sudo apt install yt-dlp
```

### Fedora

Enable the repositories that provide your preferred media player, then install:

```sh
sudo dnf install curl grep sed jq fzf mpv python3 ffmpeg openssl
```

Use `vlc` instead of or in addition to `mpv` if VLC is your preferred player.

### Arch Linux and SteamOS

On Arch Linux:

```sh
sudo pacman -S --needed curl grep sed jq fzf mpv python ffmpeg openssl
```

On Steam Deck, install `io.mpv.Mpv` from Discover or Flathub, and install the remaining command-line dependencies through the package manager available in Desktop Mode. Then use the source-install commands above.

### openSUSE

```sh
sudo zypper install curl grep sed jq fzf mpv python3 ffmpeg openssl
```

### FreeBSD

```sh
sudo pkg install curl jq fzf mpv python3 ffmpeg openssl
```

`grep` and `sed` are provided by the base system. Install VLC instead of mpv if preferred.

### macOS

Install [Homebrew](https://brew.sh/) first, then:

```sh
brew install curl jq fzf mpv python ffmpeg openssl
```

Optional players and download tools:

```sh
brew install --cask iina vlc
brew install yt-dlp
```

The built-in `sh`, `grep`, and `sed` are sufficient. Run the source-install commands from a terminal after installing the dependencies.

### Android with Termux

Install [Termux](https://termux.com/) and update its packages:

```sh
pkg update
pkg install curl grep sed jq fzf python openssl
```

Install mpv or VLC separately from a compatible Android source. Yomi CLI can launch the Android player integrations when the required app is installed. Use the source-install commands above inside Termux.

### Windows and WSL

The recommended Windows setup is WSL2 with a Linux distribution. Follow the Debian/Ubuntu instructions inside WSL and make sure `mpv.exe` or `vlc.exe` is available on the Windows `PATH`.

Git Bash can also run the script. Install `jq`, `fzf`, Python, and a media player with a package manager such as Scoop; Git Bash already provides the usual shell utilities. Keep the player executable on `PATH`.

### iSH on iOS

This is an advanced setup. Install the available packages in iSH:

```sh
apk add curl grep sed jq fzf python3 openssl
```

Install VLC from the App Store and use the source-install commands above. Package availability varies by iSH/Alpine version; the local Python relay is required for wrapped Yomi streams.

## Dependencies

Required for normal interactive playback:

- POSIX-compatible `sh`
- `curl`
- `sed`
- `grep`
- `jq`
- `fzf` (or configure `rofi`/`dmenu`)
- `mpv` or `VLC`
- `python3` for the local HLS/subtitle relay
- `openssl` for encrypted MegaPlay source responses

Optional:

- `yt-dlp` or `ffmpeg` for downloads
- `iina` on macOS
- `Syncplay`
- `ani-skip` for mpv intro skipping

If Yomi.to is protected by its CDN, an impersonating curl build may be required. Set the curl executable through the existing system `PATH` or adapt the script for the curl implementation available on your platform.

## Usage

```sh
# Search and choose interactively
yomi-cli "one piece"

# Play a specific episode
yomi-cli -e 9 "smoking behind the supermarket with you"

# Play a range
yomi-cli "blue lock" -e 5-8

# Choose the second search result
yomi-cli -S 2 "one piece"

# Use VLC
yomi-cli --vlc "one piece"

# Use a specific quality
yomi-cli -q 720p "one piece"

# Play dubbed episodes
yomi-cli --dub "one piece"

# Continue from history
yomi-cli --continue

# Download instead of playing
yomi-cli --download -e 2 "cyberpunk edgerunners"
```

Run `yomi-cli --help` for the complete option list. The interactive episode menu provides `next`, `replay`, `previous`, episode selection, quality selection, subtitle selection, and quit. A selected navigation action waits for the current player to close before launching the next action.

## Metadata and playback

Search and episode metadata are retrieved from AniList. Yomi.to and MegaPlay resolve the actual HLS video and subtitle streams. If AniList does not publish a total episode count for an airing series, `yomi-cli` derives the released episode count from the next scheduled episode so valid current episodes remain selectable.

## Subtitles

Subtitles start enabled and prefer the `English` track. After an episode starts, choose `subtitles` from the episode menu to select another available track or choose `off`.

The selection is saved and reused for later episodes. The settings file is:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/yomi-cli/settings
```

The history directory can be changed with `YOMI_CLI_HIST_DIR`.

The defaults can also be set through the environment:

```sh
YOMI_CLI_SUBTITLES=1
YOMI_CLI_SUBTITLE_LANGUAGE=English
yomi-cli "one piece"
```

VLC receives a temporary local WebVTT file. mpv and other URL-capable players receive the local relay URL directly.

## Configuration

All configuration uses the `YOMI_CLI_*` prefix:

| Variable | Purpose | Default |
| --- | --- | --- |
| `YOMI_CLI_MODE` | `sub` or `dub` playback mode | `sub` |
| `YOMI_CLI_QUALITY` | `best`, `worst`, or a listed height | `best` |
| `YOMI_CLI_PLAYER` | Player command or special player name | platform dependent |
| `YOMI_CLI_PLAYER_FLAGS` | Additional player flags | empty |
| `YOMI_CLI_MENU` | `fzf`, `rofi`, `dmenu`, or another menu command | `fzf` |
| `YOMI_CLI_MENU_FLAGS` | Additional menu flags | empty |
| `YOMI_CLI_HIST_DIR` | History and subtitle settings directory | `$XDG_STATE_HOME/yomi-cli` or `$HOME/.local/state/yomi-cli` |
| `YOMI_CLI_DEFAULT_SOURCE` | `search` or `history` | `search` |
| `YOMI_CLI_SUBTITLES` | Start with subtitles enabled (`0` or `1`) | `1` |
| `YOMI_CLI_SUBTITLE_LANGUAGE` | Initial preferred subtitle label | `English` |
| `YOMI_CLI_RELAY_SCRIPT` | Local relay helper path | beside `yomi-cli` |
| `YOMI_CLI_DOWNLOAD_DIR` | Download destination | current directory |
| `YOMI_CLI_LOG` | Playback logging (`0` or `1`) | `1` |
| `YOMI_CLI_SKIP_INTRO` | Enable `ani-skip` (`0` or `1`) | `0` |
| `YOMI_CLI_NO_DETACH` | Keep the player attached (`0` or `1`) | `0` |
| `YOMI_CLI_EXIT_AFTER_PLAY` | Return after player exit (`0` or `1`) | `0` |

## Disclaimer

Yomi CLI only requests and plays resources supplied by external websites. It does not host or distribute video or subtitle files. Use the software only where permitted by applicable law and the terms of the services involved. See [disclaimer.md](disclaimer.md).

## Attribution

Yomi CLI is a derivative work of [ani-cli](https://github.com/pystardust/ani-cli). The original project provided the shell-based terminal workflow, player integration patterns, history flow, and GPL-3.0-licensed foundation from which this project was developed. This project keeps the original credit and GPL-3.0 license; see [ATTRIBUTION.md](ATTRIBUTION.md) and [LICENSE](LICENSE).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Keep the executable, relay helper, man page, and README behaviorally consistent.
