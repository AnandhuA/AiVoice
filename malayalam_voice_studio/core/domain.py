from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from uuid import uuid4


def new_id() -> str:
    return uuid4().hex


EMOTIONS = ["Neutral", "Happy", "Sad", "Angry", "Controlled anger", "Fear", "Suspicious",
            "Threatening", "Calm", "Excited", "Frustrated", "Confused", "Sarcastic", "Whisper",
            "Shouting", "Crying", "Tired", "Drunk", "Custom"]
STYLES = ["Natural", "Casual", "Cinematic", "Dramatic", "Rough", "Soft", "Aggressive", "Slow", "Fast"]


@dataclass
class Performance:
    emotion: str = "Neutral"
    intensity: float = 0.5
    style: str = "Natural"
    speed: float = 1.0
    pitch: float = 0.0
    energy: float = 0.7
    breathiness: float = 0.0
    pause_strength: float = 1.0
    volume_db: float = 0.0
    emphasis: str = ""
    breath: str = "None"
    ending: str = "Auto"
    direction: str = ""
    cfg_weight: float = 0.5

    def validate(self) -> None:
        for key, lo, hi in [("intensity", 0, 1), ("speed", 0.5, 2), ("pitch", -12, 12),
                            ("energy", 0, 1), ("breathiness", 0, 1),
                            ("pause_strength", 0, 3), ("volume_db", -60, 12), ("cfg_weight", 0, 1)]:
            if not lo <= getattr(self, key) <= hi:
                raise ValueError(f"{key} must be between {lo} and {hi}.")


@dataclass
class Character:
    name: str = "Custom Character"
    gender: str = "Male"
    age: str = "Adult"
    voice_type: str = "Warm"
    accent: str = "Malayalam"
    speaker: str = "Harish"
    description: str = "An original character voice."
    reference: str = ""
    reference_text: str = ""
    performance: Performance = field(default_factory=Performance)

    @classmethod
    def from_dict(cls, data: dict) -> Character:
        return cls(**{**data, "performance": Performance(**data.get("performance", {}))})


@dataclass
class Segment:
    text: str
    character: str = "Custom Character"
    id: str = field(default_factory=new_id)
    line_id: str = field(default_factory=new_id)
    performance: Performance = field(default_factory=Performance)
    # A boundary is owned by the segment to its right. Final silence lives on Project.
    pause_before_ms: int = 0
    raw_path: str = ""
    processed_path: str = ""
    audio_key: str = ""
    duration: float = 0.0
    seed: int = 42
    manual: bool = False
    status: str = "Not generated"

    @classmethod
    def from_dict(cls, data: dict) -> Segment:
        return cls(**{**data, "performance": Performance(**data.get("performance", {}))})


@dataclass
class Effects:
    normalize: bool = True
    highpass: bool = False
    lowpass: bool = False
    eq: bool = False
    compression: bool = False
    noise_reduction: bool = False
    reverb: bool = False
    saturation: bool = False
    ambience: str = ""
    ambience_db: float = -34.0


@dataclass
class Project:
    name: str = "Untitled scene"
    schema_version: int = 1
    original: str = ""
    characters: dict[str, Character] = field(default_factory=dict)
    segments: list[Segment] = field(default_factory=list)
    tail_pause_ms: int = 0
    backend: str = "parler"
    effects: Effects = field(default_factory=Effects)
    substitutions: dict[str, str] = field(default_factory=dict)
    breath_assets: dict[str, str] = field(default_factory=dict)
    model_revision: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported project version. Open with the matching studio version.")
        result = cls(**{**data,
            "characters": {k: Character.from_dict(v) for k, v in data["characters"].items()},
            "segments": [Segment.from_dict(s) for s in data["segments"]],
            "effects": Effects(**data.get("effects", {}))})
        ids = [s.id for s in result.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate segment identifiers in project.")
        for segment in result.segments:
            segment.performance.validate()
            if segment.character not in result.characters:
                raise ValueError(f"Unknown character: {segment.character}")
            if not 0 <= segment.pause_before_ms <= 60000:
                raise ValueError("Pause must be 0–60000 ms.")
        if not 0 <= result.tail_pause_ms <= 60000:
            raise ValueError("Final pause must be 0–60000 ms.")
        return result


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
