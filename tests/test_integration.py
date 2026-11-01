"""Exercise the packaged integration in Home Assistant with recorded TV replies.

Only the ADB transport and peripheral power/volume inputs are simulated. App
queries, playback parsing, config entries, entities and HA state updates are real.
"""

import asyncio
import json
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
import unittest
from unittest.mock import AsyncMock, patch

import androidtv as installed_androidtv

from homeassistant import bootstrap, loader
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_component import async_update_entity
from homeassistant.setup import async_setup_component

import custom_components.androidtv as integration
from custom_components.androidtv._androidtv.setup_async import AndroidTVAsync

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = json.loads(
    (ROOT / "tests/fixtures/sony_android10_playback.json").read_text()
)["samples"]

REPLAY_SHELL = """
dumpsys() {
    case "$*" in
        'window windows') printf '%s' "$REPLAY_WINDOW" ;;
        'activity activities') printf '%s' "$REPLAY_ACTIVITY" ;;
        'media_session') printf '%s' "$REPLAY_MEDIA" ;;
        'audio') printf '%s' "$REPLAY_AUDIO" ;;
        *) printf 'Unexpected dumpsys request' >&2; return 1 ;;
    esac
}
cmd() {
    case "$*" in
        'package list packages -U '*) printf '%s' "$REPLAY_PACKAGES" ;;
        *) printf 'Unexpected package request' >&2; return 1 ;;
    esac
}
"""


class RecordedADB:
    """Return local fixture data without opening a connection to a TV."""

    def __init__(self, sample):
        self.sample = sample
        self.available = True
        self.connects = 0
        self.closes = 0
        self.failure = None
        self.commands = []

    async def connect(self, *args, **kwargs):
        self.connects += 1
        self.available = True
        return True

    async def close(self):
        self.closes += 1
        self.available = False

    async def shell(self, command):
        if self.failure:
            error, self.failure = self.failure, None
            raise error
        self.commands.append(command)
        sample = self.sample
        env = {
            **os.environ,
            "REPLAY_WINDOW": sample["window"],
            "REPLAY_ACTIVITY": sample["activity"],
            "REPLAY_MEDIA": sample["media"],
            "REPLAY_AUDIO": sample["audio"],
            "REPLAY_PACKAGES": sample["packages"],
        }
        process = await asyncio.create_subprocess_exec(
            "bash",
            "--posix",
            "-c",
            REPLAY_SHELL + command,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if stderr:
            raise AssertionError(stderr.decode())
        return stdout.decode().strip()


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Load the custom component through HA and exercise its normal update path."""

    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        config = Path(self.directory.name)
        (config / "custom_components").symlink_to(
            ROOT / "custom_components", target_is_directory=True
        )
        self.hass = HomeAssistant(str(config))
        self.addAsyncCleanup(self.hass.async_stop, force=True)
        loader.async_setup(self.hass)
        result = await bootstrap.async_from_config_dict(
            {
                "homeassistant": {
                    "name": "ADB tests",
                    "time_zone": "UTC",
                    "latitude": 0,
                    "longitude": 0,
                    "elevation": 0,
                    "country": "CA",
                    "unit_system": "metric",
                },
                "http": {},
            },
            hass=self.hass,
        )
        self.assertIs(result, self.hass)
        self.sample = SAMPLES["youtube_play"]
        self.connections = []
        self.connection_patch = patch.object(
            integration,
            "async_connect_androidtv",
            new=AsyncMock(side_effect=self.connect),
        )
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.assertTrue(await async_setup_component(self.hass, "homeassistant", {}))
        self.entry = ConfigEntry(
            domain="androidtv",
            title="Recorded TV",
            version=1,
            minor_version=2,
            data={
                "host": "192.0.2.10",
                "port": 5555,
                "device_class": "androidtv",
                "name": "Recorded TV",
            },
            options={"get_sources": False, "screencap_interval": 0},
            source="user",
            unique_id="02:00:00:00:00:01",
            discovery_keys=MappingProxyType({}),
            subentries_data=(),
        )
        await self.hass.config_entries.async_add(self.entry)
        await self.hass.async_block_till_done()
        self.assertEqual(self.entry.state.value, "loaded")
        media = self.hass.states.async_all("media_player")
        self.assertEqual(len(media), 1)
        self.entity_id = media[0].entity_id

    async def connect(self, hass, config, *, state_detection_rules=None, **kwargs):
        self.tv = AndroidTVAsync(
            config["host"],
            port=config["port"],
            state_detection_rules=state_detection_rules,
        )
        self.tv.device_properties = {
            "manufacturer": "Sony",
            "model": "BRAVIA 4K UR3",
            "sw_version": "10",
            "ethmac": "02:00:00:00:00:01",
        }
        self.tv.max_volume = 100
        self.transport = RecordedADB(self.sample)
        self.tv._adb = self.transport

        # Power flags come from the captures; volume is a synthetic peripheral input.
        async def power():
            sample = self.transport.sample
            return sample["screen_on"], sample["awake"], sample["wake_locks"]

        async def volume():
            return "speaker", self.muted, 10, 0.1

        self.muted = False
        self.tv.screen_on_awake_wake_lock_size = power
        self.tv.stream_music_properties = volume
        self.tv.get_hdmi_input = AsyncMock(return_value=None)
        self.connections.append(self.tv)
        return self.tv, None

    async def refresh(self, sample):
        self.sample = sample
        self.transport.sample = sample
        await async_update_entity(self.hass, self.entity_id)
        await self.hass.async_block_till_done()
        return self.hass.states.get(self.entity_id)

    async def test_recorded_apps_reach_ha_states(self):
        for name, sample in SAMPLES.items():
            with self.subTest(capture=name):
                self.muted = "muted_play" in name
                state = await self.refresh(sample)
                self.assertEqual(state.state, sample["expected_state"])
                self.assertEqual(state.attributes.get("app_id"), sample["expected_app"])
                if sample["screen_on"] and sample["awake"]:
                    self.assertEqual(state.attributes["is_volume_muted"], self.muted)
                    self.assertEqual(state.attributes["volume_level"], 0.1)

    async def test_transport_failure_recovers_on_next_poll(self):
        self.transport.failure = ConnectionResetError("Simulated ADB disconnect")
        state = await self.refresh(SAMPLES["youtube_play"])
        self.assertEqual(state.state, "unavailable")
        self.assertEqual(self.transport.closes, 1)
        state = await self.refresh(SAMPLES["youtube_pause"])
        self.assertEqual(state.state, "paused")
        self.assertEqual(self.transport.connects, 1)

    async def test_reload_preserves_entity_id_and_unique_id(self):
        before = entity_registry.async_get(self.hass).async_get(self.entity_id)
        unique_id = before.unique_id
        original_id = before.id
        self.sample = SAMPLES["youtube_pause"]
        self.assertTrue(
            await self.hass.config_entries.async_reload(self.entry.entry_id)
        )
        await self.hass.async_block_till_done()
        after = entity_registry.async_get(self.hass).async_get(self.entity_id)
        self.assertEqual(after.unique_id, unique_id)
        self.assertEqual(after.id, original_id)
        state = await self.refresh(self.sample)
        self.assertEqual(state.state, "paused")
        self.assertGreaterEqual(len(self.connections), 2)

    async def test_custom_state_rules_survive_options_reload(self):
        self.sample = SAMPLES["angel_play"]
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={
                **self.entry.options,
                "state_detection_rules": {"com.angel.tv": ["paused"]},
            },
        )
        await self.hass.async_block_till_done()
        state = await self.refresh(self.sample)
        self.assertEqual(state.state, "paused")
        self.assertEqual(state.attributes["app_id"], "com.angel.tv")

    async def test_config_flow_form_loads(self):
        result = await self.hass.config_entries.flow.async_init(
            "androidtv", context={"source": "user"}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")
        self.hass.config_entries.flow.async_abort(result["flow_id"])

    async def test_scoped_backend_does_not_replace_installed_library(self):
        self.assertEqual(installed_androidtv.__version__, "0.0.75")
        self.assertTrue(
            type(self.tv).__module__.startswith(
                "custom_components.androidtv._androidtv."
            )
        )
        self.assertFalse(
            installed_androidtv.AndroidTVSync.__module__.startswith(
                "custom_components."
            )
        )

    async def test_busy_connection_does_not_mark_tv_unavailable(self):
        from custom_components.androidtv._androidtv.exceptions import (
            LockNotAcquiredException,
        )

        await self.refresh(SAMPLES["youtube_play"])
        self.transport.failure = LockNotAcquiredException("Simulated busy connection")
        state = await self.refresh(SAMPLES["youtube_play"])
        self.assertEqual(state.state, "playing")
        self.assertEqual(self.transport.closes, 0)

    async def test_media_services_use_backend_controls(self):
        await self.refresh(SAMPLES["youtube_play"])
        cases = [
            ("media_play", "media_play", {}, ()),
            ("media_pause", "media_pause", {}, ()),
            ("turn_on", "turn_on", {}, ()),
            ("turn_off", "turn_off", {}, ()),
            ("volume_set", "set_volume_level", {"volume_level": 0.05}, (0.05,)),
        ]
        for service, method, data, arguments in cases:
            with self.subTest(service=service), patch.object(
                self.tv, method, new_callable=AsyncMock
            ) as control:
                await self.hass.services.async_call(
                    "media_player",
                    service,
                    {"entity_id": self.entity_id, **data},
                    blocking=True,
                )
                control.assert_awaited_once_with(*arguments)
