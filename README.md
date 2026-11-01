# Android TV ADB for Home Assistant

A custom version of Home Assistant's Android Debug Bridge integration with playback detection fixes for Sony TVs running Android 10.

This is an early development version based on Home Assistant Core 2026.10.4.

## Playback fixes

- Recover the foreground app when Sony's window-focus fields are empty.
- Read the foreground app's current media audio players.
- Match media-session data to the exact app and ignore failed or incomplete replies.

The detection is shared across apps. Existing custom commands and state-detection rules retain their priority.

## Installation

This integration uses the `androidtv` domain and replaces the built-in Android Debug Bridge integration while installed. Existing configuration entries, entity IDs, options and ADB keys are retained. Updates to the built-in integration do not apply to this copy automatically.

To install through HACS, add this repository as a custom integration repository, download it and restart Home Assistant. It is not part of the HACS default catalog.

For a manual installation, copy `custom_components/androidtv` into your Home Assistant configuration's `custom_components` directory, then restart Home Assistant. If the TV is already configured, keep its existing entry. Otherwise, add Android Debug Bridge through Settings > Devices & services.

Before a live trial, save a Home Assistant backup. To return to the built-in integration, uninstall this custom integration through HACS, or remove only its `custom_components/androidtv` folder, and restart Home Assistant. Keep the TV configuration entries and ADB keys.

Compatibility is currently tested with Home Assistant 2026.10.4. Review compatibility before upgrading Home Assistant.

## Development environment

The Compose file runs the same HA version in a Linux container, with its web interface bound to the local computer at http://127.0.0.1:18123.

```sh
python3 scripts/prepare_dev.py
docker compose up -d homeassistant
```

It starts with a separate configuration and no TV connections or automations. Development data lives in `../_data/ha-androidtv-adb/`. Set `HA_DEV_DATA_DIR` and `HA_DEV_PORT` in your environment or a local `.env` file to change those defaults.

Run the integration tests:

```sh
docker compose --profile test run --rm tests
```

Stop the development instance with `docker compose stop homeassistant`. Its configuration stays in the data directory.

## Testing

Recorded replies from a Sony XBR-65A8H running Android 10 cover TiviMate, YouTube and Angel. Integration tests replay these replies through the packaged library and actual Home Assistant entities. Power flags come from the captures; volume inputs are synthetic. Config-flow loading, options, entity IDs, reloads and recovery from a simulated ADB disconnect are checked separately.

The backend has also been tested against the physical TV and its full test suite runs on Linux with Python 3.14. This does not establish a completed live Home Assistant trial.

Audio-player data cannot reliably distinguish buffering from a deliberate pause. Netflix and Prime Video playback have not been tested.

## Sources

The backend is included under the integration's private `_androidtv` package. Its files are copied unchanged from the [backend fork](https://github.com/simonmainguy/python-androidtv). This keeps the patched implementation separate from Home Assistant's installed `androidtv` package.

`UPSTREAM.json` records the exact Home Assistant and library revisions and file hashes. Verify them with:

```sh
python3 scripts/sync_upstream.py --check
```

To regenerate the imported sources, run `python3 scripts/sync_upstream.py`. This downloads the pinned source files and uses Docker to extract the matching compiled English and French translations.

Home Assistant integration code is licensed under Apache 2.0. The original [python-androidtv library](https://github.com/JeffLIrion/python-androidtv) and its contributors retain their MIT license. Both licenses are included with the integration.
