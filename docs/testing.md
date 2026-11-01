# Test scope

The development environment is pinned to Home Assistant 2026.10.4 and its official container image digest. On Apple Silicon it runs Linux ARM64 and Python 3.14.9.

Integration tests bootstrap real Home Assistant instances in temporary directories. Each instance loads the custom `androidtv` component, creates a configuration entry and registers media-player and remote entities. The ADB connection is replaced with a local replay transport.

Captured window, activity, package, audio-player and media-session replies are passed through the library's generated shell queries and normal parsing and update methods. Power flags come from the captures; volume is supplied as a synthetic peripheral input. No network connection to a TV is opened.

The playback fixture contains 19 captures covering YouTube, Angel and TiviMate, plus menus and standby. Expected states were established during the physical-device trials. The original fixture provenance is retained.

Additional checks cover configuration-flow loading, options-driven reloads, stable entity registry IDs, a simulated disconnect and the next successful poll. The tests also check that importing the custom backend leaves the separately installed `androidtv` module intact.

The full backend suite can be run separately from its checkout using the same official HA container. Its source revision is recorded in `UPSTREAM.json`, and every bundled Python file must match that revision byte for byte.

## Before installing on the main instance

Complete a controlled live trial of setup, play/pause/resume, power, volume, reconnect and restart behavior. Check both the Sony and a Google TV device. Confirm the main instance's entity IDs and saved options remain intact, then observe normal use before retiring an existing playback detector.

Buffering can pause Android's audio player. A paused player therefore does not establish that the viewer pressed Pause. These checks do not claim compatibility with every app or TV.
