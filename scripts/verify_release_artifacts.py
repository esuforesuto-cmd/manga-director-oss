"""Verify frozen historical evidence or the explicitly selected publication candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from collections import Counter, defaultdict
from email.message import Message
from email.parser import BytesParser
from pathlib import Path
from stat import S_ISREG

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

INTERNAL_SDIST_MEMBERS = (
    "docs/roadmap/MD_POST_LTS_RFC_01_IMPLEMENTATION_PLAN.md",
    "docs/roadmap/MD_POST_LTS_RFC_01_PROVIDER_NEUTRAL_REAL_IMAGE_GENERATION_DELIVERY.md",
)
FROZEN_ARTIFACTS = {
    "wheel": (
        Path("dist/manga_director-6.0.0-py3-none-any.whl"),
        "b1ff393f8102982b654b5d5c876a1a398e3781e43a57b6a858f76b77fec8778e",
    ),
    "sdist": (
        Path("dist/manga_director-6.0.0.tar.gz"),
        "e34077a6d894fd803f3565a2d45f028879e88759d7861dca4d4a37d751300bd9",
    ),
}
CANDIDATE_DIRECTORY = Path("build/publication-candidate")
CANDIDATE_MANIFEST = "publication-candidate.json"


def _version_from_source() -> str:
    source = Path("src/manga_director/_version.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "(?P<version>[^"]+)"$', source, re.MULTILINE)
    if match is None:
        raise ValueError("could not read the canonical package version")
    return match.group("version")


def _metadata(payload: bytes) -> Message:
    return BytesParser().parsebytes(payload)


def _wheel_metadata(path: Path) -> Message:
    with zipfile.ZipFile(path) as archive:
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError(f"{path}: expected one wheel METADATA file")
        return _metadata(archive.read(metadata[0]))


def _sdist_metadata_and_members(path: Path) -> tuple[Message, set[str]]:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getnames()
        metadata = [name for name in members if name.endswith("/PKG-INFO")]
        if len(metadata) != 1:
            raise ValueError(f"{path}: expected one source-distribution PKG-INFO file")
        metadata_file = archive.extractfile(metadata[0])
        if metadata_file is None:
            raise ValueError(f"{path}: could not read PKG-INFO")
        prefix = metadata[0].removesuffix("/PKG-INFO") + "/"
        relative_members = {name.removeprefix(prefix) for name in members}
        return _metadata(metadata_file.read()), relative_members


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_metadata() -> dict[str, object]:
    with Path("pyproject.toml").open("rb") as source:
        project = tomllib.load(source).get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml has no project metadata table")
    return project


MarkerExpression = tuple[object, ...]
RequirementIdentity = tuple[str, tuple[str, ...], str, str | None, MarkerExpression | None]


def _combine_marker_expressions(operator: str, expressions: list[MarkerExpression]) -> MarkerExpression:
    flattened: list[MarkerExpression] = []
    for expression in expressions:
        if expression[0] == operator:
            for child in expression[1:]:
                if not isinstance(child, tuple):
                    raise ValueError("package metadata contains an invalid marker expression")
                flattened.append(child)
        else:
            flattened.append(expression)
    if len(flattened) == 1:
        return flattened[0]
    return (operator, *sorted(flattened, key=repr))


def _is_publication_extra_selector(atom: tuple[object, ...], extra: str) -> bool:
    if len(atom) != 3:
        return False
    variable, operator, value = (str(part) for part in atom)
    return (
        operator == "=="
        and variable == "extra"
        and canonicalize_name(value) == canonicalize_name(extra)
    )


def _marker_components(
    markers: list[object], publication_extra: str | None
) -> tuple[list[MarkerExpression | None], list[str], int]:
    operands: list[MarkerExpression | None] = []
    operators: list[str] = []
    removed = 0
    for item in markers:
        if isinstance(item, str):
            if item not in {"and", "or"}:
                raise ValueError("package metadata contains an unsupported marker operator")
            operators.append(item)
        else:
            expression, removed_count = _marker_expression(item, publication_extra)
            operands.append(expression)
            removed += removed_count
    if len(operands) != len(operators) + 1:
        raise ValueError("package metadata contains an invalid marker expression")
    return operands, operators, removed


def _marker_expression(
    markers: object, publication_extra: str | None = None
) -> tuple[MarkerExpression | None, int]:
    if isinstance(markers, tuple):
        if publication_extra is not None and _is_publication_extra_selector(markers, publication_extra):
            return None, 1
        return ("atom", *(str(part) for part in markers)), 0
    if not isinstance(markers, list):
        raise ValueError("package metadata contains an unsupported marker expression")
    if not markers:
        return None, 0
    operands, operators, removed = _marker_components(markers, publication_extra)
    if removed and "or" in operators:
        raise ValueError("publication extra selector cannot be removed from an OR marker")
    remaining = [operand for operand in operands if operand is not None]
    if not remaining:
        return None, removed
    if not operators or removed:
        return _combine_marker_expressions("and", remaining), removed

    groups: list[list[MarkerExpression]] = [[remaining[0]]]
    for operator, operand in zip(operators, remaining[1:], strict=True):
        if operator == "and":
            groups[-1].append(operand)
        else:
            groups.append([operand])
    conjunctions = [_combine_marker_expressions("and", group) for group in groups]
    return _combine_marker_expressions("or", conjunctions), removed


def _extra_selectors(markers: object) -> list[str]:
    if isinstance(markers, tuple):
        if len(markers) == 3 and str(markers[0]) == "extra" and str(markers[1]) == "==":
            return [canonicalize_name(str(markers[2]))]
        return []
    if not isinstance(markers, list):
        raise ValueError("package metadata contains an unsupported marker expression")
    return [selector for item in markers if not isinstance(item, str) for selector in _extra_selectors(item)]


def _requirement_identity(
    requirement: str, publication_extra: str | None = None
) -> RequirementIdentity:
    parsed = Requirement(requirement)
    marker = parsed.marker._markers if parsed.marker is not None else []
    marker_expression, removed_selectors = _marker_expression(marker, publication_extra)
    if publication_extra is not None and removed_selectors != 1:
        raise ValueError("optional artifact requirement must have exactly one publication extra selector")
    return (
        canonicalize_name(parsed.name),
        tuple(sorted(canonicalize_name(extra) for extra in parsed.extras)),
        str(parsed.specifier),
        parsed.url,
        marker_expression,
    )


def _string_list(project: dict[str, object], field: str) -> list[str]:
    value = project.get(field, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"pyproject.toml {field} must be a string list")
    return value


def _extra_name(requirement: Requirement) -> str | None:
    selectors = _extra_selectors(requirement.marker._markers if requirement.marker is not None else [])
    if len(selectors) > 1:
        raise ValueError("optional artifact requirement has multiple publication extra selectors")
    return selectors[0] if selectors else None


def _extras_from_metadata(metadata: Message) -> dict[str, Counter[RequirementIdentity]]:
    extras: dict[str, Counter[RequirementIdentity]] = defaultdict(Counter)
    for raw_requirement in metadata.get_all("Requires-Dist", []):
        requirement = Requirement(raw_requirement)
        extra = _extra_name(requirement)
        if extra is not None:
            extras[extra][_requirement_identity(raw_requirement, extra)] += 1
    return dict(extras)


def _expected_extras(project: dict[str, object]) -> dict[str, Counter[RequirementIdentity]]:
    optional_dependencies = project["optional-dependencies"]
    if not isinstance(optional_dependencies, dict):
        raise ValueError("pyproject.toml optional dependencies are invalid")
    if not all(
        isinstance(extra, str)
        and isinstance(requirements, list)
        and all(isinstance(requirement, str) for requirement in requirements)
        for extra, requirements in optional_dependencies.items()
    ):
        raise ValueError("pyproject.toml optional dependencies must be string lists")
    return {
        canonicalize_name(extra): Counter(_requirement_identity(requirement) for requirement in requirements)
        for extra, requirements in optional_dependencies.items()
    }


def _base_requirements_from_metadata(metadata: Message) -> Counter[RequirementIdentity]:
    return Counter(
        _requirement_identity(requirement)
        for requirement in metadata.get_all("Requires-Dist", [])
        if _extra_name(Requirement(requirement)) is None
    )


def _requirement_counts_for_json(
    requirements: Counter[RequirementIdentity],
) -> list[dict[str, object]]:
    return [
        {"requirement": list(identity), "count": count}
        for identity, count in sorted(requirements.items())
    ]


def _extra_requirement_counts_for_json(
    extras: dict[str, Counter[RequirementIdentity]],
) -> dict[str, list[dict[str, object]]]:
    return {extra: _requirement_counts_for_json(requirements) for extra, requirements in sorted(extras.items())}


def _verify_metadata(metadata: Message, expected_version: str, project: dict[str, object]) -> dict[str, int]:
    expected_fields = {
        "Name": project["name"],
        "Version": expected_version,
        "Summary": project["description"],
        "Requires-Python": project["requires-python"],
    }
    mismatches = {
        field: {"expected": expected, "actual": metadata[field]}
        for field, expected in expected_fields.items()
        if metadata[field] != expected
    }
    expected_base_requirements = Counter(
        _requirement_identity(requirement) for requirement in _string_list(project, "dependencies")
    )
    actual_base_requirements = _base_requirements_from_metadata(metadata)
    actual_extras = _extras_from_metadata(metadata)
    expected_extras = _expected_extras(project)
    actual_provided_extras = {
        canonicalize_name(extra) for extra in metadata.get_all("Provides-Extra", [])
    }
    if (
        mismatches
        or actual_base_requirements != expected_base_requirements
        or actual_extras != expected_extras
        or actual_provided_extras != set(expected_extras)
    ):
        raise ValueError(
            json.dumps(
                {
                    "metadata_mismatches": mismatches,
                    "expected_base_requirements": _requirement_counts_for_json(
                        expected_base_requirements
                    ),
                    "actual_base_requirements": _requirement_counts_for_json(
                        actual_base_requirements
                    ),
                    "expected_extras": _extra_requirement_counts_for_json(expected_extras),
                    "actual_extras": _extra_requirement_counts_for_json(actual_extras),
                    "expected_provided_extras": sorted(expected_extras),
                    "actual_provided_extras": sorted(actual_provided_extras),
                },
                default=sorted,
                sort_keys=True,
            )
        )
    return {
        "source_runtime_dependency_count": len(expected_base_requirements),
        "artifact_requires_dist_count": len(metadata.get_all("Requires-Dist", [])),
    }


def _git_text_output(arguments: list[str]) -> str:
    output = subprocess.run(
        ["git", *arguments], check=True, capture_output=True, text=True
    ).stdout
    if not isinstance(output, str):
        raise ValueError("git text output had an unexpected type")
    return output


def _git_binary_output(arguments: list[str]) -> bytes:
    output = subprocess.run(["git", *arguments], check=True, capture_output=True).stdout
    if not isinstance(output, bytes):
        raise ValueError("git binary output had an unexpected type")
    return output


def _source_state() -> dict[str, object]:
    try:
        root = Path(_git_text_output(["rev-parse", "--show-toplevel"]).strip()).resolve()
        head = _git_text_output(["rev-parse", "HEAD"]).strip()
        diff = _git_binary_output(["diff", "--binary", "HEAD"])
        untracked = _git_binary_output(["ls-files", "--others", "--exclude-standard", "-z"])
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"could not determine current source state: {error}") from error
    untracked_files: list[dict[str, str]] = []
    for raw_path in filter(None, untracked.split(b"\0")):
        relative = Path(raw_path.decode("utf-8", "surrogateescape"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("git reported an unsafe untracked path")
        path = root / relative
        if not path.exists() or not S_ISREG(path.lstat().st_mode):
            raise ValueError(f"untracked repository entry is not a regular file: {relative.as_posix()}")
        untracked_files.append({"path": relative.as_posix(), "sha256": _digest(path)})
    untracked_files.sort(key=lambda entry: entry["path"])
    return {
        "head": head,
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "untracked_files": untracked_files,
    }


def _verify_source_state(expected_source_state: object) -> None:
    if expected_source_state != _source_state():
        raise ValueError("current publication candidate has stale or inconsistent provenance")


def _candidate_directory(candidate_dir: Path) -> Path:
    authorized = CANDIDATE_DIRECTORY.resolve()
    if candidate_dir.resolve() != authorized:
        raise ValueError(f"current publication candidate must be {CANDIDATE_DIRECTORY.as_posix()}")
    return authorized


def _verify_historical_baseline() -> dict[str, object]:
    result: dict[str, object] = {"artifact_classification": "FROZEN_HISTORICAL"}
    for kind, (path, expected_digest) in FROZEN_ARTIFACTS.items():
        if not path.is_file() or _digest(path) != expected_digest:
            raise ValueError(f"frozen {kind} does not match its canonical baseline digest")
        result[kind] = {"path": path.as_posix(), "sha256": expected_digest}
    return result


def _verify_current_candidate(candidate_dir: Path) -> dict[str, object]:
    candidate_dir = _candidate_directory(candidate_dir)
    if not candidate_dir.is_dir():
        raise ValueError("current publication candidate directory is missing")

    expected_version = _version_from_source()
    wheel = candidate_dir / f"manga_director-{expected_version}-py3-none-any.whl"
    sdist = candidate_dir / f"manga_director-{expected_version}.tar.gz"
    manifest_path = candidate_dir / CANDIDATE_MANIFEST
    expected_entries = {wheel.name, sdist.name, manifest_path.name}
    actual_entries = {entry.name for entry in candidate_dir.iterdir()}
    if actual_entries != expected_entries:
        raise ValueError("current publication candidate is missing or ambiguous")
    if not wheel.is_file() or not sdist.is_file() or not manifest_path.is_file():
        raise ValueError("current publication candidate must contain regular artifact files and a manifest")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("current publication candidate manifest is invalid")
    _verify_source_state(manifest.get("source_state"))
    expected_manifest = {
        "format": 1,
        "source_state": _source_state(),
        "version": expected_version,
        "artifacts": {"wheel": _digest(wheel), "sdist": _digest(sdist)},
    }
    if manifest != expected_manifest:
        raise ValueError("current publication candidate is stale or has inconsistent provenance")

    project = _project_metadata()
    wheel_metadata = _wheel_metadata(wheel)
    sdist_metadata, sdist_members = _sdist_metadata_and_members(sdist)
    wheel_metadata_result = _verify_metadata(wheel_metadata, expected_version, project)
    sdist_metadata_result = _verify_metadata(sdist_metadata, expected_version, project)
    excluded_members = sorted(set(INTERNAL_SDIST_MEMBERS) & sdist_members)
    if excluded_members:
        raise ValueError(f"internal sdist members present: {excluded_members}")

    subprocess.run(
        [sys.executable, "-m", "twine", "check", str(wheel), str(sdist)], check=True
    )
    return {
        "artifact_classification": "CURRENT_PUBLICATION_CANDIDATE",
        "package_version_verification": "PASS",
        "version": expected_version,
        "wheel": {"path": wheel.as_posix(), "sha256": _digest(wheel)},
        "sdist": {"path": sdist.as_posix(), "sha256": _digest(sdist)},
        "wheel_metadata": wheel_metadata_result,
        "sdist_metadata": sdist_metadata_result,
        "extras": _extra_requirement_counts_for_json(_expected_extras(project)),
        "internal_sdist_members": "ABSENT",
        "twine_check": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("historical-baseline")
    candidate = modes.add_parser("current-candidate")
    candidate.add_argument("--candidate-dir", type=Path, default=CANDIDATE_DIRECTORY)
    args = parser.parse_args()

    try:
        result = (
            _verify_historical_baseline()
            if args.mode == "historical-baseline"
            else _verify_current_candidate(args.candidate_dir)
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
        tarfile.TarError,
    ) as error:
        print(f"artifact verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, default=sorted, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
