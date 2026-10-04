from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil


@dataclass
class Settings:
    device: str = "Auto"
    backend: str = "praha"
    inference_python: str = ""
    sample_rate: int = 48000
    bit_depth: int = 24
    channels: int = 1
    mp3_bitrate: int = 192
    default_voice: str = "Harish"
    default_speed: float = 1.0
    default_emotion: str = "Calm"
    ffmpeg: str = ""
    output_folder: str = ""
    cache_folder: str = ""
    timeout_seconds: int = 900


class Paths:
    def __init__(self, root: Path | None = None):
        self.root = (root or Path(os.environ.get("MVS_HOME", Path.cwd()))).resolve()
        for name in ("models", "voices", "projects", "exports", "cache", "logs"):
            path = self.root / name
            path.mkdir(parents=True, exist_ok=True)
            setattr(self, name, path)

    def load_settings(self) -> Settings:
        file = self.root / "settings.json"
        if not file.exists():
            return Settings(output_folder=str(self.exports), cache_folder=str(self.cache))
        return Settings(**json.loads(file.read_text(encoding="utf-8")))

    def save_settings(self, settings: Settings) -> None:
        atomic_json(self.root / "settings.json", asdict(settings))


def atomic_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def find_ffmpeg(configured: str = "") -> str:
    if configured:
        return configured
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def clean_temp(cache: Path) -> int:
    root = cache.resolve()
    folder = root / "temporary"
    count = 0
    if folder.is_dir() and not folder.is_symlink() and folder.resolve().parent == root:
        for file in folder.iterdir():
            if file.is_file() and not file.is_symlink() and file.resolve().parent == folder.resolve():
                file.unlink()
                count += 1
    return count
