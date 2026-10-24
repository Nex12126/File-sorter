from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


RULES_FILE = "classification_rules.json"
PROTECTED_EXTENSIONS = {
    ".exe", ".msi", ".msix", ".msixbundle", ".appx", ".appxbundle", ".msp", ".mst",
    ".lnk", ".url", ".appref-ms", ".com", ".scr", ".dll", ".sys", ".ocx", ".drv",
    ".bat", ".cmd", ".ps1", ".psm1", ".psd1", ".vbs", ".vbe", ".wsf", ".reg", ".inf",
}


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path
    reason: str


def _group_key(path: Path) -> str:
    stem = path.stem.casefold()
    stem = re.sub(r"\s*\(\d+\)$", "", stem)
    stem = re.sub(r"(?:[ _.-]+(?:copy|kopie))$", "", stem)
    return " ".join(re.sub(r"[\W_]+", " ", stem).split())


def _available_path(path: Path, reserved: set[Path]) -> Path:
    candidate = path
    index = 2
    while candidate.exists() or candidate in reserved:
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        index += 1
    reserved.add(candidate)
    return candidate


def _rules_path() -> Path:
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return bundle_dir / RULES_FILE


def _load_rules() -> dict:
    with _rules_path().open(encoding="utf-8") as rules_file:
        return json.load(rules_file)


def _target_path(target: str) -> Path:
    path = Path(target)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Ungültiger Zielordner in den Regeln: {target}")
    return path


def _is_protected(path: Path) -> bool:
    return path.is_symlink() or path.suffix.casefold() in PROTECTED_EXTENSIONS


def count_protected_files(folder: Path) -> int:
    return sum(1 for item in folder.iterdir() if item.is_file() and _is_protected(item))


def _classify(path: Path, rules: dict) -> tuple[Path, str]:
    extension = path.suffix.lstrip(".").casefold()
    for category_name, category in rules["categories"].items():
        for rule_name, rule in category.items():
            extensions = {item.casefold().lstrip(".") for item in rule["extensions"]}
            if extension not in extensions:
                continue
            if any(re.search(pattern, path.stem) for pattern in rule["name_patterns"]):
                return _target_path(rule["target_directory"]), f"{category_name} / {rule_name}"

    for fallback_name, fallback in rules["fallback_rules"].items():
        extensions = {item.casefold().lstrip(".") for item in fallback.get("extensions", [])}
        if extension in extensions:
            return _target_path(fallback["target_directory"]), f"Unsortiert / {fallback_name}"
    default = rules["fallback_rules"]["default"]
    return _target_path(default["target_directory"]), "Unsortiert / Sonstiges"


def build_plan(folder: Path) -> list[Move]:
    files = sorted(
        (item for item in folder.iterdir() if item.is_file() and not _is_protected(item)),
        key=lambda item: item.name.casefold(),
    )
    rules = _load_rules()
    classifications = {path: _classify(path, rules) for path in files}
    families: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        key = _group_key(path)
        if key:
            families[key].append(path)

    grouped = {path for family in families.values() if len(family) > 1 for path in family}
    reserved: set[Path] = set()
    family_destinations: dict[str, Path] = {}
    plan: list[Move] = []

    for path in files:
        if path in grouped:
            key = _group_key(path)
            if key not in family_destinations:
                folder_name = re.sub(r"[<>:\"/\\|?*]", "_", path.stem).strip(" .") or "Dateigruppe"
                target_roots = {classifications[item][0] for item in families[key]}
                group_root = next(iter(target_roots)) if len(target_roots) == 1 else Path("Related")
                destination_folder = _available_path(folder / group_root / folder_name, reserved)
                family_destinations[key] = destination_folder
            target = _available_path(family_destinations[key] / path.name, reserved)
            plan.append(Move(path, target, "Zusammengehörige Dateien"))
            continue

        target_root, reason = classifications[path]
        target = _available_path(folder / target_root / path.name, reserved)
        plan.append(Move(path, target, reason))

    return plan


def apply_plan(plan: list[Move]) -> int:
    completed: list[tuple[Path, Path]] = []
    try:
        for move in plan:
            if not move.source.is_file():
                raise FileNotFoundError(f"Datei wurde nicht gefunden: {move.source}")
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            destination = move.destination
            if destination.exists():
                destination = _available_path(destination, set())
            move.source.rename(destination)
            completed.append((move.source, destination))
    except OSError as error:
        for source, destination in reversed(completed):
            source.parent.mkdir(parents=True, exist_ok=True)
            if not source.exists():
                destination.rename(source)
        raise OSError(f"Sortieren abgebrochen; ausgeführte Verschiebungen wurden zurückgesetzt. {error}") from error
    return len(completed)