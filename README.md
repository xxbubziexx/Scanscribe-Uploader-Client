# ScanScribe Uploader (client)

Console client that watches a folder and uploads audio files to a ScanScribe server.

## Functionality
- Has a file-size watcher that waits for the file-size to stablize until sending. This makes it compatible with Proscan. 
- Audio file rejection operates here aswell. Supports file-size and audio length limits.
- After the audio-file is sent to scanscribe, its deleted from the machine hosting the watcher unless disabled.


## Quick start

```bash
pip install -r requirements.txt
python scanscribe_client_console.py --setup
python scanscribe_client_console.py
```
Configure the uploader client with the scanscribe config.yml.

Alternatively, you can use the configuration stored at `~/.scanscribe-client.json` (override with `--config`).

## Documentation

| Doc | Purpose |
|-----|---------|
| [README-CONSOLE.md](README-CONSOLE.md) | CLI usage, arguments, Wine/GUI notes |
| [BUILD.md](BUILD.md) | Windows PyInstaller builds |
| [BUILD-LINUX.md](BUILD-LINUX.md) | Building the Windows `.exe` from Linux via Wine |

Some older build examples refer to `scanscribe_client.py` (windowed GUI). This repository ships the **console** entrypoint `scanscribe_client_console.py`; PyInstaller packaging for that target is defined in `ScanScribe-Client.spec` and `build-wine.sh`.

## Requirements

See [requirements.txt](requirements.txt). Python 3 is required for development; end users who only run the built `.exe` do not need Python installed.

## Repository layout

- `scanscribe_client_console.py` — main application
- `ScanScribe-Client.spec` — PyInstaller spec for one-file console EXE
- `build-wine.sh` — automated Wine build on Linux
