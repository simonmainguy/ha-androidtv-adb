# Test scope

The development environment is pinned to Home Assistant 2026.10.4 and its official container image digest. On Apple Silicon it runs Linux ARM64 and Python 3.14.9.

Integration tests bootstrap real Home Assistant instances in temporary directories. Each instance loads the custom `androidtv` component, creates a configuration entry and registers media-player and remote entities. The ADB connection is replaced with a local replay transport.

Captured window, activity, package, audio-player and media-session replies are passed through the library's generated shell queries and normal parsing and update methods. Power flags come from the captures; volume is supplied as a synthetic peripheral input. No network connection to a TV is opened.

The Sony playback fixture contains 19 captures covering YouTube, Angel and TiviMate, plus menus and standby. A second fixture contains four reduced Google TV Streamer captures covering YouTube play, pause, resume and menus. Its audio reply is deliberately empty, so the test must recover playback from the media session. Expected states were established during the physical-device trials, and fixture provenance is retained.

Additional checks cover configuration-flow loading, options-driven reloads, stable entity registry IDs, a simulated disconnect and the next successful poll. The tests also check that importing the custom backend leaves the separately installed `androidtv` module intact.

The full backend suite can be run separately from its checkout using the same official HA container. Its source revision is recorded in `UPSTREAM.json`, and every bundled Python file must match that revision byte for byte.

## Initial live Home Assistant trial (0.1.0b1)

A controlled trial on 2026-11-01 used the packaged integration in the separate Mac development instance, running the pinned Home Assistant 2026.10.4 image on Linux ARM64 with Python 3.14.9. The commands went through Home Assistant services and the entities used their normal update methods. YouTube pause and resume were also observed through normal polling without forced updates.

| Device | Checks | Result |
| --- | --- | --- |
| Sony XBR-65A8H, Android 10 | TiviMate, YouTube and Angel play/pause/resume; menus | Expected playback and idle states were reported. Angel checks used an episode after its ads. |
| Sony XBR-65A8H, Android 10 | Volume, mute and standby/wake | Volume changes were read back correctly. Muted playback stayed `playing`. Power services completed a standby/wake cycle. |
| Google TV Streamer, Android 14 | TiviMate pause/resume and standby/wake | Expected states were reported. |
| Google TV Streamer, Android 14 | YouTube play/pause/resume | Controls reached the app, but the entity remained `idle`. The original production library showed the same limitation. |
| Google TV Streamer, Android 14 | Volume and mute | Requests did not change the reported HDMI stream volume or mute values. Physical TV volume control was not established by this test. |
| Both devices | Configuration-entry reload and full development-instance restart | Both ADB connections reopened without new approval. Media-player and remote entity IDs, registry IDs and unique IDs were unchanged. |

During the initial trial, the Streamer's media-session replies used named states such as `PLAYING(3)` and `PAUSED(2)`. Both the installed original library and the 0.1.0b1 backend failed to parse those values. Their non-Sony query strings and session-state regular expressions were identical. That finding prompted the follow-up below.

TV power and reported volume settings were restored after testing, along with the living-room lighting settings. No custom integration was installed on the main instance. Private addresses, ADB keys, credentials and raw UI captures are not included in this repository.

## Named media-session states (0.1.0b2)

The shared session parser now accepts both numeric and named state formats, retaining the numeric code used by the existing state-detection logic. It requires a complete named value and rejects malformed replies. This follows [Android's PlaybackState string format](https://android.googlesource.com/platform/frameworks/base/+/master/media/java/android/media/session/PlaybackState.java) and does not add app-specific rules or shell queries.

The new Google TV replay failed for playing, paused and resumed states with the old packaged parser. It passed after the backend update. The full backend suite passed with 301 tests successful and one skipped; all nine Home Assistant integration tests passed, including the existing Sony captures.

A follow-up live trial on the Google TV Streamer verified YouTube play, pause, resume and return to an idle menu. YouTube controls used the development instance's normal Home Assistant service/update path. A separate TiviMate pause/resume cycle used an external controller while the development instance made state reads only, confirming that its periodic polling picked up both transitions. The 0.1.0b1-to-0.1.0b2 development restart retained ADB authorization and all four media-player/remote entity registry records.

The Kitchen TV's own integration supplied temporary mute during these tests. Its original power, volume and mute settings were restored afterward. The main instance still uses the original integration and existing automations. The earlier HDMI stream volume limitation is separate from this parser change.

## Before installing on the main instance

The separate-instance trial is complete within the scope above. A live upgrade of existing production entries has not been tested. Save a backup before that installation, compare the existing entity IDs and saved options afterward, and observe normal use before retiring an existing playback detector. Reopening ADB connections was tested through reloads and restart; unexpected network-loss recovery remains covered by the simulated-disconnect tests.

Buffering can pause Android's audio player. A paused player therefore does not establish that the viewer pressed Pause. These checks do not claim compatibility with every app or TV.
