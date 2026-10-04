from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from uuid import uuid4

import soundfile as sf
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QVBoxLayout)

from ..audio.processor import read_audio, run_ffmpeg
from ..core.config import Settings
from ..core.domain import Effects
from .waveform import Waveform
from .widgets import button, combo, number


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Studio settings")
        self.resize(580, 580)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.fields = {
            "backend": combo(["praha", "parler", "indicf5"]), "device": combo(["Auto", "CUDA", "CPU"]),
            "inference_python": QLineEdit(),
            "sample_rate": combo(["22050", "44100", "48000"]), "bit_depth": combo(["16", "24"]),
            "channels": combo(["1", "2"]), "mp3_bitrate": combo(["128", "192", "256", "320"]),
            "default_voice": combo(["Harish", "Anjali", "Anju"]),
            "default_speed": number(.5, 2, settings.default_speed), "default_emotion": QLineEdit(),
            "ffmpeg": QLineEdit(), "output_folder": QLineEdit(), "cache_folder": QLineEdit(),
            "timeout_seconds": number(30, 7200, settings.timeout_seconds, 60, 0),
        }
        for key, field in self.fields.items():
            value = getattr(settings, key)
            if hasattr(field, "setCurrentText"):
                field.setCurrentText(str(value))
            elif hasattr(field, "setText"):
                field.setText(str(value))
            form.addRow(key.replace("_", " ").title(), field)
        layout.addLayout(form)
        layout.addWidget(QLabel("Game dialogue preset: 48000 Hz · 24-bit · 1 channel\nLeave FFmpeg blank to use the bundled fallback.\nDefaults apply to new scenes; current scene backend is in the top bar."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> Settings:
        values = {}
        for key, field in self.fields.items():
            values[key] = field.currentText() if hasattr(field, "currentText") else field.value() if hasattr(field, "value") else field.text()
        for key in ("sample_rate", "bit_depth", "channels", "mp3_bitrate", "timeout_seconds"):
            values[key] = int(values[key])
        return Settings(**values)


class ReferenceDialog(QDialog):
    def __init__(self, character, paths, settings, parent=None):
        super().__init__(parent)
        self.character, self.paths, self.settings = character, paths, settings
        self.path = character.reference
        self.setWindowTitle("Voice reference · use audio you have permission to use")
        self.resize(760, 470)
        layout = QVBoxLayout(self)
        self.label = QLabel(self.path or "Import a WAV, MP3 or FLAC reference")
        layout.addWidget(self.label)
        self.wave = Waveform()
        layout.addWidget(self.wave)
        form = QFormLayout()
        self.start, self.end = number(0, 36000, 0), number(0, 36000, 0)
        form.addRow("Trim start · seconds", self.start)
        form.addRow("Trim end · seconds", self.end)
        layout.addLayout(form)
        self.wave.selection_changed.connect(lambda a, b: (self.start.setValue(a), self.end.setValue(b)))
        self.transcript = QPlainTextEdit(character.reference_text)
        self.transcript.setPlaceholderText("Exact words spoken in the trimmed reference (required by IndicF5)")
        layout.addWidget(self.transcript)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.errorOccurred.connect(lambda error, text: QMessageBox.warning(self, "Playback failed", text))
        row = QHBoxLayout()
        for label, action in [("Import", self.import_audio), ("Play", self.play), ("Pause", self.player.pause),
                              ("Stop", self.player.stop), ("Apply trim", self.trim), ("Clear reference", self.clear_reference)]:
            row.addWidget(button(label, action))
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if self.path and Path(self.path).exists():
            self.load()

    def load(self):
        self.wave.load(self.path)
        self.start.setValue(0)
        self.end.setValue(len(self.wave.samples) / self.wave.rate)
        self.label.setText(self.path)

    def import_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import reference", "", "Audio (*.wav *.mp3 *.flac)")
        if not path:
            return
        try:
            target = self.paths.voices / f"reference-{uuid4().hex}.wav"
            run_ffmpeg(["-i", path, "-ac", "1", "-ar", "24000", str(target)], self.settings.ffmpeg)
            read_audio(target)
            self.path = str(target)
            self.load()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid audio", str(exc))

    def play(self):
        if self.path:
            self.player.setSource(QUrl.fromLocalFile(self.path))
            self.player.play()

    def clear_reference(self):
        import numpy as np
        self.player.stop()
        self.path = ''
        self.transcript.clear()
        self.wave.samples = np.zeros(0)
        self.wave.update()
        self.label.setText('No reference: Praha uses its built-in voice conditioning.')

    def trim(self):
        try:
            audio, rate = read_audio(Path(self.path))
            begin, end = round(self.start.value() * rate), round(self.end.value() * rate)
            if not 0 <= begin < end <= len(audio):
                raise ValueError("Choose a valid non-empty trim interval.")
            target = self.paths.voices / f"trim-{uuid4().hex}.wav"
            sf.write(target, audio[begin:end], rate, subtype="PCM_24")
            self.path = str(target)
            self.load()
        except Exception as exc:
            QMessageBox.warning(self, "Trim failed", str(exc))

    def save(self):
        self.character.reference = self.path
        self.character.reference_text = self.transcript.toPlainText()
        self.accept()

    def done(self, code):
        self.player.stop()
        super().done(code)


class EffectsDialog(QDialog):
    def __init__(self, effects, breath_assets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio finishing · subtle processing")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.fields = {}
        for key, value in asdict(effects).items():
            if isinstance(value, bool):
                field = QCheckBox()
                field.setChecked(value)
            elif isinstance(value, float):
                field = number(-60, 0, value, 1)
            else:
                field = QLineEdit(value)
            self.fields[key] = field
            form.addRow(key.replace("_", " ").title(), field)
        self.breath_fields = {}
        for kind in ("Short", "Medium", "Heavy"):
            row = QHBoxLayout()
            field = QLineEdit(breath_assets.get(kind, ""))
            self.breath_fields[kind] = field
            row.addWidget(field)
            row.addWidget(button("Browse", lambda checked=False, f=field: self.browse(f)))
            form.addRow(f"{kind} breath WAV", row)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse(self, field):
        path, _ = QFileDialog.getOpenFileName(self, "Choose breath", "", "Audio (*.wav *.flac)")
        if path:
            field.setText(path)

    def value(self):
        values = {k: f.isChecked() if isinstance(f, QCheckBox) else f.value() if hasattr(f, "value") else f.text() for k, f in self.fields.items()}
        return Effects(**values), {k: f.text() for k, f in self.breath_fields.items() if f.text()}


def edit_text(parent, title: str, text: str, label: str = "") -> str | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(720, 440)
    layout = QVBoxLayout(dialog)
    if label:
        caption = QLabel(label)
        caption.setWordWrap(True)
        layout.addWidget(caption)
    editor = QPlainTextEdit(text)
    layout.addWidget(editor)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return editor.toPlainText() if dialog.exec() else None
