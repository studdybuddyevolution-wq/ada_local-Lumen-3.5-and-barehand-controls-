# Barehands integration for Lumen

Lumen can optionally control [Barehands](https://github.com/jaredrhod/barehands), the webcam-based hand-tracked board. Barehands remains a separate upstream checkout; this repository contains only a small local bridge.

## Install on Windows

From the Lumen repository root:

\`\`\`powershell
New-Item -ItemType Directory -Force integrations | Out-Null
git clone https://github.com/jaredrhod/barehands.git integrations\\barehands
\`\`\`

The upstream checkout is ignored by Git so its runtime files and media are not committed. Retain its own license and notices. If installed elsewhere, set the LUMEN_BAREHANDS_DIR environment variable to its folder before launching Lumen.

The bridge uses only the Python standard library and requests to 127.0.0.1. Barehands itself uses the browser webcam and may download frontend dependencies from public CDNs on first use; no paid AI API key is required.

## Operations

- status: check whether the server is installed and running.
- start: start the local server.
- open: open its stage page in the browser.
- present / add_card: add a text card.
- add_image: show a file already inside the configured media folder.
- board_state: read the latest board snapshot.
- clear / reset: clear the scene; these require an explicit confirm=true parameter.

Image paths must be relative to the configured media directory. Absolute paths, parent traversal, hidden paths, unsupported extensions, and files outside the media folder are rejected.

Set LUMEN_BAREHANDS_DISABLED=1 to disable the bridge. If the Barehands checkout is missing, Lumen still starts normally and reports that the board is not installed.
