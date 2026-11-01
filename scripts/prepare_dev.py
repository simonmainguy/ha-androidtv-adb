"""Prepare the separate development configuration without replacing existing data."""

import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
settings = {}
environment_file = ROOT / ".env"
if environment_file.is_file():
    for line in environment_file.read_text().splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and name in {"HA_DEV_DATA_DIR", "HA_DEV_PORT"}:
            settings[name] = value.strip().strip("'\"")
value = os.environ.get(
    "HA_DEV_DATA_DIR", settings.get("HA_DEV_DATA_DIR", "../_data/ha-androidtv-adb")
)
data = Path(value)
if not data.is_absolute():
    data = (ROOT / data).resolve()
data.mkdir(parents=True, exist_ok=True)
(data / "custom_components").mkdir(exist_ok=True)
target = data / "configuration.yaml"
if target.exists() and not target.is_file():
    raise SystemExit(f"Development configuration must be a file: {target}")
# Docker can leave an empty mount target after an interrupted first start.
if not target.exists() or target.stat().st_size == 0:
    shutil.copyfile(ROOT / "development/configuration.yaml", target)
print(f"Development data: {data}")
