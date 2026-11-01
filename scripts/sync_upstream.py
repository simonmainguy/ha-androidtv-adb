#!/usr/bin/env python3
"""Import the pinned integration and backend sources, or verify their hashes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = Path("custom_components/androidtv")
HA_VERSION = "2026.10.4"
HA_COMMIT = "357cae5c598dfcd7a0ea7dc5b1facccd4ec6037b"
LIBRARY_COMMIT = "b8a2f4f0ec1b1f0e6ed2811988df4fa3d297b6a6"
IMAGE = (
    "ghcr.io/home-assistant/home-assistant:2026.10.4"
    "@sha256:23f4dfbb69ce76315dbc4de7915504f1c2dcecd7ca2648113a493a385972e133"
)
VERSION = "0.1.0b2"
REPOSITORY_URL = "https://github.com/simonmainguy/ha-androidtv-adb"
HA_FILES = (
    "__init__.py",
    "config_flow.py",
    "const.py",
    "diagnostics.py",
    "entity.py",
    "icons.json",
    "manifest.json",
    "media_player.py",
    "remote.py",
    "services.py",
    "services.yaml",
)
LIBRARY_FILES = (
    "__init__.py",
    "adb_manager/__init__.py",
    "adb_manager/adb_manager_async.py",
    "adb_manager/adb_manager_sync.py",
    "androidtv/__init__.py",
    "androidtv/androidtv_async.py",
    "androidtv/androidtv_sync.py",
    "androidtv/base_androidtv.py",
    "basetv/__init__.py",
    "basetv/basetv.py",
    "basetv/basetv_async.py",
    "basetv/basetv_sync.py",
    "constants.py",
    "exceptions.py",
    "firetv/__init__.py",
    "firetv/base_firetv.py",
    "firetv/firetv_async.py",
    "firetv/firetv_sync.py",
    "setup_async.py",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(repository, revision, path):
    url = f"https://raw.githubusercontent.com/{repository}/{revision}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "ha-androidtv-adb"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def check():
    lock = json.loads((ROOT / "UPSTREAM.json").read_text())
    failures = []
    for relative, record in lock["files"].items():
        path = ROOT / relative
        if not path.is_file() or digest(path.read_bytes()) != record["sha256"]:
            failures.append(relative)
    component = ROOT / COMPONENT
    expected = {p for p in lock["files"] if p.startswith(str(COMPONENT) + "/")}
    actual = {
        str(p.relative_to(ROOT))
        for p in component.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
    failures.extend(sorted(actual - expected - {str(COMPONENT / "NOTICE")}))
    manifest = json.loads((component / "manifest.json").read_text())
    if manifest["version"] != VERSION:
        failures.append("manifest version")
    if failures:
        raise SystemExit("Source verification failed: " + ", ".join(failures))
    print(f"Verified {len(lock['files'])} pinned source files.")


def sync(library_repo, docker):
    tasks = []
    for name in HA_FILES:
        tasks.append(("ha", name))
    tasks.append(("ha_license", "LICENSE.md"))
    for name in LIBRARY_FILES:
        tasks.append(("library", name))
    tasks.append(("library_license", "LICENSE"))
    for name in (
        "sony_android10.json",
        "sony_android10_audio.json",
        "sony_android10_playback.json",
        "google_tv_playback.json",
    ):
        tasks.append(("fixture", name))

    def obtain(task):
        kind, name = task
        if kind.startswith("ha"):
            path = (
                "LICENSE.md"
                if kind == "ha_license"
                else f"homeassistant/components/androidtv/{name}"
            )
            data = download("home-assistant/core", HA_COMMIT, path)
        else:
            path = (
                f"tests/fixtures/{name}"
                if kind == "fixture"
                else "LICENSE"
                if kind == "library_license"
                else f"androidtv/{name}"
            )
            if library_repo:
                data = subprocess.check_output(
                    ["git", "-C", str(library_repo), "show", f"{LIBRARY_COMMIT}:{path}"]
                )
            else:
                data = download("simonmainguy/python-androidtv", LIBRARY_COMMIT, path)
        return kind, name, path, data

    lock = {
        "home_assistant": {
            "repository": "home-assistant/core",
            "version": HA_VERSION,
            "commit": HA_COMMIT,
        },
        "androidtv": {
            "repository": "simonmainguy/python-androidtv",
            "commit": LIBRARY_COMMIT,
        },
        "translation_image": IMAGE,
        "files": {},
    }

    def save(destination, data, origin, source_path, source_data=None):
        relative = str(destination)
        path = ROOT / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        lock["files"][relative] = {
            "origin": origin,
            "source_path": source_path,
            "source_sha256": digest(data if source_data is None else source_data),
            "sha256": digest(data),
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        for kind, name, path, original in pool.map(obtain, tasks):
            data = original
            if kind == "ha":
                destination = COMPONENT / name
                if name.endswith(".py"):
                    data = data.replace(b"from androidtv", b"from ._androidtv")
                elif name == "manifest.json":
                    manifest = json.loads(data)
                    manifest.update(
                        version=VERSION,
                        codeowners=["@simonmainguy"],
                        documentation=REPOSITORY_URL,
                        issue_tracker=f"{REPOSITORY_URL}/issues",
                        loggers=["adb_shell", "custom_components.androidtv._androidtv"],
                        requirements=[
                            "adb-shell[async]==0.4.4",
                            "aiofiles==25.1.0",
                            "async-timeout==4.0.3",
                            "pure-python-adb==0.3.0.dev0",
                        ],
                    )
                    manifest = {
                        "domain": manifest.pop("domain"),
                        "name": manifest.pop("name"),
                        **dict(sorted(manifest.items())),
                    }
                    data = (json.dumps(manifest, indent=2) + "\n").encode()
            elif kind == "ha_license":
                save(Path("LICENSE"), data, kind, path)
                destination = COMPONENT / "LICENSE"
            elif kind == "library":
                destination = COMPONENT / "_androidtv" / name
            elif kind == "fixture":
                destination = Path("tests/fixtures") / name
            else:
                destination = COMPONENT / "_androidtv" / "LICENSE"
            save(destination, data, kind, path, original)

    translation_script = (
        "import importlib.util,json,pathlib;"
        "p=pathlib.Path(importlib.util.find_spec('homeassistant').origin).parent"
        "/'components/androidtv/translations';"
        "print(json.dumps({lang:(p/(lang+'.json')).read_text()"
        " for lang in ['en','fr']}))"
    )
    translations = json.loads(
        subprocess.check_output(
            [
                docker,
                "run",
                "--rm",
                "--entrypoint",
                "python",
                IMAGE,
                "-c",
                translation_script,
            ],
            text=True,
        )
    )
    for language, content in translations.items():
        save(
            COMPONENT / "translations" / f"{language}.json",
            content.encode(),
            "ha_translation",
            language,
        )
    (ROOT / "UPSTREAM.json").write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n"
    )
    check()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify files without downloading or changing them.",
    )
    parser.add_argument(
        "--library-repo",
        type=Path,
        help="Read the pinned library revision from a local Git checkout.",
    )
    parser.add_argument(
        "--docker",
        default="docker",
        help="Docker CLI used to extract compiled translations.",
    )
    args = parser.parse_args()
    if args.check:
        check()
    else:
        sync(args.library_repo, args.docker)
