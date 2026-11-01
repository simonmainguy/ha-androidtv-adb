# Test scope

The development environment is pinned to Home Assistant 2026.10.4 and its official container image digest. On Apple Silicon it runs Linux ARM64 and Python 3.14.9.

Integration tests bootstrap real Home Assistant instances in temporary directories. Each instance loads the custom `androidtv` component, creates a configuration entry and registers media-player and remote entities. The ADB connection is replaced with a local replay transport.

Captured window, activity, package, audio-player and media-session replies are passed through the library's generated shell queries and normal parsing and update methods. Power flags come from the captures; volume is supplied as a synthetic peripheral input. No network connection to a TV is opened.

The playback fixture contains 19 captures covering YouTube, Angel and TiviMate, plus menus and standby. Expected states were established during the physical-device trials. The original fixture provenance is retained.

Additional checks cover configuration-flow loading, options-driven reloads, stable entity registry IDs, a simulated disconnect and the next successful poll. The tests also check that importing the custom backend leaves the separately installed `androidtv` module intact.

The full backend suite can be run separately from its checkout using the same official HA container. Its source revision is recorded in `UPSTREAM.json`, and every bundled Python file must match that revision byte for byte.

## Live Home Assistant trial

A controlled trial on 2026-11-01 used the packaged integration in the separate Mac development instance, running the pinned Home Assistant 2026.10.4 image on Linux ARM64 with Python 3.14.9. The commands went through Home Assistant services and the entities used their normal update methods. YouTube pause and resume were also observed through normal polling without forced updates.

| Device | Checks | Result |
| --- | --- | --- |
| Sony XBR-65A8H, Android 10 | TiviMate, YouTube and Angel play/pause/resume; menus | Expected playback and idle states were reported. Angel checks used an episode after its ads. |
| Sony XBR-65A8H, Android 10 | Volume, mute and standby/wake | Volume changes were read back correctly. Muted playback stayed `playing`. Power services completed a standby/wake cycle. |
| Google TV Streamer, Android 14 | TiviMate pause/resume and standby/wake | Expected states were reported. |
| Google TV Streamer, Android 14 | YouTube play/pause/resume | Controls reached the app, but the entity remained `idle`. The original production library showed the same limitation. |
| Google TV Streamer, Android 14 | Volume and mute | Requests did not change the reported HDMI stream volume or mute values. Physical TV volume control was not established by this test. |
| Both devices | Configuration-entry reload and full development-instance restart | Both ADB connections reopened without new approval. Media-player and remote entity IDs, registry IDs and unique IDs were unchanged. |

The Streamer's media-session replies used named states such as `PLAYING(3)` and `PAUSED(2)`. Both the installed original library and the bundled backend failed to parse those values. Their non-Sony query strings and session-state regular expressions were identical. This is an existing limitation, outside the Sony Android 10 changes.

TV power and reported volume settings were restored after testing, along with the living-room lighting settings. No custom integration was installed on the main instance. Private addresses, ADB keys, credentials and raw UI captures are not included in this repository.

## Before installing on the main instance

The separate-instance trial is complete within the scope above. A live upgrade of existing production entries has not been tested. Save a backup before that installation, compare the existing entity IDs and saved options afterward, and observe normal use before retiring an existing playback detector. Reopening ADB connections was tested through reloads and restart; unexpected network-loss recovery remains covered by the simulated-disconnect tests.

Buffering can pause Android's audio player. A paused player therefore does not establish that the viewer pressed Pause. These checks do not claim compatibility with every app or TV.
