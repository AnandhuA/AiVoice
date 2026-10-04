import csv
import json
from copy import deepcopy
from pathlib import Path

from .acting_engine import analyze
from .domain import EMOTIONS, Project


def import_batch(path: Path, project: Project) -> int:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = json.load(stream) if path.suffix.lower() == ".json" else list(csv.DictReader(stream))
    if not isinstance(rows, list):
        raise ValueError("Batch JSON must be an array of dialogue objects.")
    pending = []
    originals = []
    previous_tail = project.tail_pause_ms
    for number, row in enumerate(rows, 1):
        try:
            name = row["character"]
            if name not in project.characters:
                raise ValueError(f"Unknown character '{name}'. Create the character first.")
            emotion = next((e for e in EMOTIONS if e.lower() == str(row["emotion"]).lower()), None)
            if emotion is None:
                raise ValueError("Unknown emotion.")
            intensity = float(row["intensity"]) / 100
            base = deepcopy(project.characters[name].performance)
            base.emotion, base.intensity = emotion, intensity
            base.validate()
            text = row["dialogue"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Dialogue cannot be empty.")
            result = analyze(text, name, base, project.substitutions)
            if (pending or project.segments) and result.segments:
                result.segments[0].pause_before_ms = max(result.segments[0].pause_before_ms, previous_tail or 300)
            pending.extend(result.segments)
            previous_tail = result.tail_pause_ms
            originals.append(text)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Batch row {number}: {exc}") from exc
    project.segments.extend(pending)
    project.tail_pause_ms = previous_tail
    project.original += ("\n" if project.original else "") + "\n".join(originals)
    return len(rows)
