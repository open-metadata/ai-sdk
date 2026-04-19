"""Parse git diffs into dbt/OpenMetadata assets for impact analysis."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Sequence


MODEL_EXTENSIONS = {".sql"}
SCHEMA_EXTENSIONS = {".yml", ".yaml"}
DEFAULT_PATH_FILTERS = ("**/models/**/*.sql", "**/models/**/*.yml", "**/models/**/*.yaml")


@dataclass(frozen=True)
class ChangedAsset:
    """A dbt model or schema file changed in a pull request."""

    name: str
    path: str
    kind: str
    change_type: str
    diff: str


def parse_changed_assets(
    diff_output: str,
    path_filters: Sequence[str] | None = None,
) -> list[ChangedAsset]:
    """Extract changed dbt model/schema assets from a unified git diff."""

    filters = tuple(path_filters or DEFAULT_PATH_FILTERS)
    assets: list[ChangedAsset] = []

    for block in _split_diff_blocks(diff_output):
        asset = _parse_diff_block(block, filters)
        if asset is not None:
            assets.append(asset)

    return assets


def split_path_filters(raw_filters: str | None) -> tuple[str, ...] | None:
    """Split a comma-separated path filter string for CLI/GitHub Action use."""

    if not raw_filters:
        return None
    filters = tuple(item.strip() for item in raw_filters.split(",") if item.strip())
    return filters or None


def _split_diff_blocks(diff_output: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in diff_output.splitlines():
        if line.startswith("diff --git "):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)

    if current:
        blocks.append(current)

    return ["\n".join(block).rstrip("\n") for block in blocks]


def _parse_diff_block(block: str, path_filters: Sequence[str]) -> ChangedAsset | None:
    old_path, new_path = _extract_paths(block)
    selected_path = new_path if new_path and new_path != "/dev/null" else old_path
    if selected_path is None or selected_path == "/dev/null":
        return None

    normalized_path = _normalize_path(selected_path)
    if not _matches_path_filters(normalized_path, path_filters):
        return None

    path = PurePosixPath(normalized_path)
    if "models" not in path.parts:
        return None

    kind = _asset_kind(path)
    if kind is None:
        return None

    return ChangedAsset(
        name=path.stem,
        path=normalized_path,
        kind=kind,
        change_type=_change_type(block),
        diff=block,
    )


def _extract_paths(block: str) -> tuple[str | None, str | None]:
    old_path: str | None = None
    new_path: str | None = None

    for line in block.splitlines():
        if line.startswith("--- "):
            old_path = _strip_diff_prefix(line[4:])
        elif line.startswith("+++ "):
            new_path = _strip_diff_prefix(line[4:])

    if old_path is None or new_path is None:
        match = re.match(r"diff --git a/(.*?) b/(.*)", block)
        if match:
            old_path = old_path or match.group(1)
            new_path = new_path or match.group(2)

    return old_path, new_path


def _strip_diff_prefix(path: str) -> str:
    if path in {"/dev/null", "dev/null"}:
        return "/dev/null"
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def _asset_kind(path: PurePosixPath) -> str | None:
    suffix = path.suffix.lower()
    if suffix in MODEL_EXTENSIONS:
        return "model"
    if suffix in SCHEMA_EXTENSIONS:
        return "schema"
    return None


def _change_type(block: str) -> str:
    if "deleted file mode" in block or "\n+++ /dev/null" in block:
        return "deleted"
    if "new file mode" in block or "\n--- /dev/null" in block:
        return "added"
    if "\nrename from " in block and "\nrename to " in block:
        return "renamed"
    return "modified"


def _matches_path_filters(path: str, path_filters: Sequence[str]) -> bool:
    return any(
        fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(f"/{path}", pattern)
        for pattern in path_filters
    )
