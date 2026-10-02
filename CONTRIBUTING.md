# Contributing to yomi-cli

## Before submitting a change

- Keep the project focused on the yomi-cli command, its relay helper, and their documentation.
- Preserve POSIX shell compatibility in `yomi-cli`.
- Run `sh -n yomi-cli` after shell changes.
- Run `python3 -m py_compile yomi-relay.py` after relay changes.
- Exercise the affected user path, not only syntax checks.
- Update `README.md` and `yomi-cli.1` when behavior or configuration changes.
- Keep the `ani-cli` attribution and GPL-3.0 license intact.
- Do not add provider credentials, hosted media, or copyrighted media to the repository.

## Pull requests

Describe the user-visible behavior, affected files, and verification performed. For playback changes, include the player used, operating system, provider route, episode selection, and whether subtitles were enabled.

Keep unrelated formatting and provider changes out of the same pull request. Avoid committing generated files such as `__pycache__` contents.

## Issues

Include:

- `yomi-cli --version` output
- operating system and shell
- player and menu frontend
- command and episode that reproduce the issue
- relevant terminal output
- whether the browser version at Yomi.to behaves differently

Do not include personal history files, cookies, or authentication data.
