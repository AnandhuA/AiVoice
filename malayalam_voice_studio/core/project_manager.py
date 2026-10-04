from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

from .config import atomic_json
from .domain import Project


def save_project(project: Project, directory: Path) -> None:
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    for sub in ("audio/segments", "references", "exports"):
        (directory / sub).mkdir(parents=True, exist_ok=True)
    data = deepcopy(project.to_dict())

    def asset(path: str, category: str) -> str:
        if not path:
            return ""
        source = Path(path).resolve()
        if not source.is_file():
            raise ValueError(f"Missing asset: {source}. Restore it or remove the reference before saving.")
        if source.is_relative_to(directory):
            return source.relative_to(directory).as_posix()
        name = sha256(source.read_bytes()).hexdigest()[:16] + source.suffix.lower()
        target = directory / category / name
        if not target.exists():
            shutil.copy2(source, target)
        return target.relative_to(directory).as_posix()

    for character in data["characters"].values():
        character["reference"] = asset(character["reference"], "references")
    for segment in data["segments"]:
        for field in ("raw_path", "processed_path"):
            segment[field] = asset(segment[field], "audio/segments")
    data["breath_assets"] = {k: asset(v, "references") for k, v in data["breath_assets"].items()}
    data["effects"]["ambience"] = asset(data["effects"]["ambience"], "references")
    # project.json is the authoritative transaction; dialogue.json is a human-readable export.
    atomic_json(directory / "dialogue.json", data["segments"])
    atomic_json(directory / "project.json", data)


def load_project(directory: Path) -> tuple[Project, list[str]]:
    directory = directory.resolve()
    data = json.loads((directory / "project.json").read_text(encoding="utf-8"))
    warnings: list[str] = []

    def asset(path: str) -> str:
        if not path:
            return ""
        result = (directory / path).resolve()
        if not result.is_relative_to(directory):
            raise ValueError(f"Project asset escapes its directory: {path}")
        if not result.is_file():
            warnings.append(f"Missing asset: {path}")
        return str(result)

    for character in data["characters"].values():
        character["reference"] = asset(character["reference"])
    for segment in data["segments"]:
        for field in ("raw_path", "processed_path"):
            segment[field] = asset(segment[field])
        if segment["raw_path"] and not Path(segment["raw_path"]).exists():
            segment.update(raw_path="", processed_path="", audio_key="", duration=0, status="Missing audio")
    data["breath_assets"] = {k: asset(v) for k, v in data.get("breath_assets", {}).items()}
    data.setdefault("effects", {})["ambience"] = asset(data.get("effects", {}).get("ambience", ""))
    return Project.from_dict(data), warnings
