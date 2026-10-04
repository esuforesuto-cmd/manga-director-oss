"""Build the single authorized current-publication candidate artifact set."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

from verify_release_artifacts import CANDIDATE_DIRECTORY, CANDIDATE_MANIFEST, _digest, _source_state


def _version_from_source() -> str:
    source = Path("src/manga_director/_version.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "(?P<version>[^"]+)"$', source, re.MULTILINE)
    if match is None:
        raise ValueError("could not read the canonical package version")
    return match.group("version")


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--no-isolation",
        action="store_true",
        help="use an already provisioned local build environment",
    )
    args = parser.parse_args()
    candidate_dir = CANDIDATE_DIRECTORY
    if candidate_dir.exists() and any(candidate_dir.iterdir()):
        print("publication candidate directory must be empty before a fresh build", file=sys.stderr)
        return 1

    try:
        candidate_dir.mkdir(parents=True, exist_ok=True)
        state_before_build = _source_state()
        command = [sys.executable, "-m", "build", "--outdir", str(candidate_dir)]
        if args.no_isolation:
            command.append("--no-isolation")
        subprocess.run(command, check=True)
        version = _version_from_source()
        wheel = candidate_dir / f"manga_director-{version}-py3-none-any.whl"
        sdist = candidate_dir / f"manga_director-{version}.tar.gz"
        if not wheel.is_file() or not sdist.is_file():
            raise ValueError("build did not produce the expected wheel and source distribution")
        if _source_state() != state_before_build:
            raise ValueError("source state changed during candidate build")
        manifest = {
            "format": 1,
            "source_state": state_before_build,
            "version": version,
            "artifacts": {"wheel": _digest(wheel), "sdist": _digest(sdist)},
        }
        (candidate_dir / CANDIDATE_MANIFEST).write_text(
            json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"publication candidate build failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"candidate_directory": candidate_dir.as_posix(), **manifest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
