from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
import logging
from pathlib import Path

import soundfile as sf
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QInputDialog,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QScrollArea, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..audio.exporter import export_audio
from ..audio.mixer import mix
from ..audio.processor import master, process_segment
from ..core.acting_engine import analyze, to_ssml
from ..core.batch import import_batch
from ..core.config import Paths, atomic_json, clean_temp
from ..core.domain import Character, Performance, Project, digest
from ..core.presets import characters
from ..core.project_manager import load_project, save_project
from ..core.segment_manager import invalidate, merge, reorder, split
from ..core.text_normalizer import natural_suggestion
from ..tts.device import detect
from .acting_panel import ActingPanel
from .character_panel import CharacterPanel
from .dialogue_editor import DialogueEditor
from .dialogs import EffectsDialog, ReferenceDialog, SettingsDialog, edit_text
from .model_manager import ModelManagerDialog
from .tasks import FunctionTask, GenerationController
from .timeline import Timeline
from .waveform import Waveform
from .widgets import button, combo, heading, number


class MainWindow(QMainWindow):
    def __init__(self, paths: Paths):
        super().__init__()
        self.paths = paths
        self.settings = paths.load_settings()
        self.project = self.empty_project()
        self.directory = None
        self.dirty = False
        self.refreshing = False
        self.snapshot = {}
        self.tasks = []
        self.rendering = False
        self.setWindowTitle("Malayalam Voice Studio · Untitled scene")
        self.resize(1200, 800)
        self.setMinimumSize(900, 650)
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.errorOccurred.connect(lambda error, text: self.error(text))
        self.generation = GenerationController(self)
        self.generation.event.connect(self.generation_event)
        self.generation.finished.connect(self.generation_finished)
        self.build_ui()
        self.refresh_characters()
        self.refresh()
        self.update_capabilities()
        QTimer.singleShot(100, self.hardware)

    def empty_project(self):
        cast = characters()
        cast["Custom Character"].speaker = self.settings.default_voice
        cast["Custom Character"].performance.speed = self.settings.default_speed
        cast["Custom Character"].performance.emotion = self.settings.default_emotion
        return Project(characters=cast, backend=self.settings.backend)

    def build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 14, 18, 8)
        for title, entries in [
            ("File", [("New scene", self.new_project), ("Open project…", self.open_project),
                      ("Save project", self.save), ("Export audio…", self.export), ("Export SSML…", self.export_ssml)]),
            ("Tools", [("Batch import…", self.batch), ("Models…", self.models), ("Audio effects…", self.effects),
                       ("Settings…", self.configure), ("Clean temporary files", lambda: self.statusBar().showMessage(
                           f"Removed {clean_temp(Path(self.settings.cache_folder))} temporary files"))])]:
            menu = self.menuBar().addMenu(title)
            for name, callback in entries:
                action = menu.addAction(name)
                action.triggered.connect(lambda checked=False, fn=callback: self.guard(fn))
        content = QVBoxLayout()
        header = QHBoxLayout()
        title = QLabel("Malayalam Voice Studio")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(button("Save project", lambda: self.guard(self.save)))
        header.addWidget(button("Export audio", lambda: self.guard(self.export)))
        header.addWidget(QLabel("Engine"))
        self.backend = combo(["praha", "parler", "indicf5"])
        self.backend.setCurrentText(self.project.backend)
        self.backend.currentTextChanged.connect(self.backend_changed)
        header.addWidget(self.backend)
        content.addLayout(header)
        self.hardware_label = QLabel("Checking PyTorch / CUDA…")
        self.hardware_label.setObjectName("muted")
        content.addWidget(self.hardware_label)
        self.tabs = QTabWidget()
        create = QWidget()
        create_layout = QVBoxLayout(create)
        hint = QLabel("1  Choose a character     →     2  Write your dialogue     →     3  Generate & play")
        hint.setObjectName("muted")
        create_layout.addWidget(hint)
        panels = QSplitter(Qt.Orientation.Horizontal)
        self.character = CharacterPanel()
        self.editor = DialogueEditor()
        self.acting = ActingPanel()
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setWidget(self.editor)
        editor_scroll.setMinimumWidth(350)
        panels.addWidget(editor_scroll)
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(self.character)
        controls_layout.addWidget(self.acting)
        controls_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(300)
        panels.addWidget(scroll)
        panels.setSizes([730, 340])
        create_layout.addWidget(panels, 1)
        self.tabs.addTab(create, "Create dialogue")
        self.editor.action.connect(lambda action: self.guard(lambda: self.editor_action(action)))
        self.editor.editor.textChanged.connect(self.text_changed)
        self.character.selected.connect(self.select_character)
        self.character.save_requested.connect(lambda: self.guard(self.save_character))
        self.character.reference_requested.connect(lambda: self.guard(self.reference))
        self.acting.apply_requested.connect(lambda: self.guard(self.apply_performance))
        self.acting.save_preset.connect(lambda: self.guard(self.save_preset))
        self.acting.load_preset.connect(lambda: self.guard(self.load_preset))

        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 5, 0, 0)
        tools = QHBoxLayout()
        lower_layout.addWidget(heading("SEGMENTS · Select a line to edit its delivery in Create dialogue"))
        take_tools = QHBoxLayout()
        for label, action in [("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                              ("Split", self.split_segment), ("Merge next", self.merge_segment), ("Delete", self.delete_segment),
                              ("Play raw", lambda: self.play_segment(False)), ("Play processed", lambda: self.play_segment(True)),
                              ("Regenerate selected", lambda: self.generate(True, True)), ("Retry failed", self.retry_failed)]:
            target = take_tools if label in ("Play raw", "Play processed", "Regenerate selected", "Retry failed") else tools
            target.addWidget(button(label, lambda checked=False, fn=action: self.guard(fn)))
        lower_layout.addLayout(tools)
        lower_layout.addLayout(take_tools)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["#", "Character", "Dialogue / double-click to edit", "Emotion", "Speed", "Pause before", "Take status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(2, 360)
        self.table.setMinimumHeight(140)
        self.table.itemSelectionChanged.connect(self.segment_selected)
        self.table.itemChanged.connect(self.item_changed)
        lower_layout.addWidget(self.table, 1)
        pauses = QHBoxLayout()
        self.before, self.after = number(0, 60000, 0, 50, 0), number(0, 60000, 0, 50, 0)
        pauses.addWidget(QLabel("Selected boundary timing"))
        pauses.addWidget(QLabel("Before · ms"))
        pauses.addWidget(self.before)
        pauses.addWidget(QLabel("After · ms"))
        pauses.addWidget(self.after)
        pauses.addWidget(button("Apply pauses", lambda: self.guard(self.apply_pauses)))
        lower_layout.addLayout(pauses)
        self.timeline = Timeline()
        self.timeline.selected.connect(self.table.selectRow)
        self.timeline.reordered.connect(lambda source, target: self.guard(lambda: self.reorder(source, target)))
        self.timeline.pause_changed.connect(lambda index, value: self.guard(lambda: self.change_boundary(index, value)))
        lower_layout.addWidget(self.timeline)
        self.wave = Waveform()
        lower_layout.addWidget(self.wave)
        self.tabs.addTab(lower, "Segments & timeline")
        content.addWidget(self.tabs, 1)
        transport = QHBoxLayout()
        for label, action in [("▶ Full dialogue", lambda: self.preview(True)), ("Raw mix", lambda: self.preview(False)),
                              ("Pause", self.player.pause), ("■ Stop", self.player.stop), ("Cancel generation", self.generation.cancel)]:
            transport.addWidget(button(label, lambda checked=False, fn=action: self.guard(fn)))
        self.progress = QProgressBar()
        self.progress.setValue(0)
        transport.addWidget(self.progress, 1)
        content.addLayout(transport)
        outer.addLayout(content, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Ready · write dialogue and click Generate voice. Fine-tune timing in Segments & timeline.")
        for name, shortcut, fn in [("Save", QKeySequence.StandardKey.Save, self.save), ("Open", QKeySequence.StandardKey.Open, self.open_project)]:
            action = QAction(name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked=False, callback=fn: self.guard(callback))
            self.addAction(action)

    def guard(self, action):
        try:
            action()
        except Exception as exc:
            logging.exception("Studio operation failed")
            self.error(str(exc))

    def error(self, message):
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "Studio needs attention", message)

    def changed(self):
        self.dirty = True
        self.setWindowTitle(f"Malayalam Voice Studio · {self.project.name} *")

    def text_changed(self):
        self.project.original = self.editor.editor.toPlainText()
        self.changed()

    def refresh_characters(self, selected="Arthur"):
        self.character.selector.blockSignals(True)
        self.character.selector.clear()
        self.character.selector.addItems(list(self.project.characters))
        self.character.selector.setCurrentText(selected)
        self.character.selector.blockSignals(False)
        self.select_character(self.character.selector.currentText())

    def select_character(self, name):
        if name in self.project.characters:
            self.character.set_character(self.project.characters[name])
            self.acting.set_value(self.project.characters[name].performance)

    def save_character(self):
        old_name = self.character.selector.currentText()
        character = deepcopy(self.project.characters[old_name])
        self.character.update_character(character)
        if not character.name:
            raise ValueError("Character name is required.")
        character.performance = self.acting.value()
        self.project.characters[character.name] = character
        if character.name == old_name:
            for segment in self.project.segments:
                if segment.character == old_name:
                    invalidate(segment)
        self.refresh_characters(character.name)
        self.changed()
        self.refresh()

    def selected_index(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.project.segments):
            raise ValueError("Select a performance segment first.")
        return row

    def refresh(self, selection=None):
        self.refreshing = True
        current = self.table.currentRow() if selection is None else selection
        self.table.setRowCount(len(self.project.segments))
        for row, segment in enumerate(self.project.segments):
            values = [str(row + 1), segment.character, segment.text, segment.performance.emotion,
                      f"{segment.performance.speed:.2f}×", f"{segment.pause_before_ms} ms", segment.status]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col != 2:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)
        self.timeline.refresh(self.project)
        self.refreshing = False
        if self.project.segments:
            self.table.selectRow(max(0, min(current, len(self.project.segments) - 1)))

    def segment_selected(self):
        if self.refreshing or self.table.currentRow() < 0:
            return
        index = self.table.currentRow()
        segment = self.project.segments[index]
        self.acting.set_value(segment.performance)
        self.before.setValue(segment.pause_before_ms)
        self.after.setValue(self.project.segments[index + 1].pause_before_ms if index + 1 < len(self.project.segments) else self.project.tail_pause_ms)

    def item_changed(self, item):
        if not self.refreshing and item.column() == 2:
            segment = self.project.segments[item.row()]
            segment.text = item.text()
            segment.manual = True
            invalidate(segment)
            self.changed()
            self.timeline.refresh(self.project)

    def apply_performance(self):
        segment = self.project.segments[self.selected_index()]
        previous = segment.performance
        updated = self.acting.value()
        native = ("emotion", "intensity", "style", "breathiness", "emphasis", "ending", "direction")
        if (self.project.backend == "parler" and any(getattr(previous, k) != getattr(updated, k) for k in native)) or (self.project.backend == "praha" and any(getattr(previous, k) != getattr(updated, k) for k in ("intensity", "cfg_weight"))):
            invalidate(segment)
        else:
            segment.processed_path = ""
            segment.status = "Needs processing" if segment.raw_path else "Not generated"
        segment.performance = updated
        segment.manual = True
        self.changed()
        self.refresh()

    def apply_pauses(self):
        index = self.selected_index()
        before, after = int(self.before.value()), int(self.after.value())
        self.change_boundary(index, before)
        self.change_boundary(index + 1, after)

    def change_boundary(self, index, value):
        if index == len(self.project.segments):
            self.project.tail_pause_ms = value
        else:
            self.project.segments[index].pause_before_ms = value
            self.project.segments[index].manual = True
        self.changed()
        self.refresh()

    def editor_action(self, action):
        if action == "clear":
            self.editor.editor.clear()
        elif action == "add":
            self.analyze(append=True)
        elif action == "analyze":
            self.analyze()
        elif action == "generate":
            self.generate()
        elif action == "regenerate":
            self.generate(True, True)
        elif action == "preview":
            self.preview(True)
        elif action == "adapt":
            original = self.editor.editor.toPlainText()
            value = edit_text(self, "Natural Malayalam · review before using", natural_suggestion(original),
                              "Original:\n" + original + "\n\nConservative local suggestions only. Save uses the edited natural version; Cancel keeps the original.")
            if value is not None:
                self.editor.editor.setPlainText(value)
        elif action == "pronunciations":
            value = edit_text(self, "Editable pronunciation substitutions", json.dumps(self.project.substitutions, ensure_ascii=False, indent=2),
                              'JSON mapping of written text to spoken text, e.g. {"Dr.": "ഡോക്ടർ"}. Applied only during analysis.')
            if value is not None:
                mapping = json.loads(value)
                if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
                    raise ValueError("Use a JSON object with text keys and text values.")
                self.project.substitutions = mapping
                self.changed()

    def analyze(self, append=False):
        source = self.editor.editor.toPlainText()
        result = analyze(source, self.character.selector.currentText(), self.acting.value(), self.project.substitutions)
        if not result.segments:
            raise ValueError("Enter Malayalam dialogue first.")
        if append:
            self.project.segments.extend(result.segments)
        else:
            manual = [s for s in self.project.segments if s.manual]
            if manual:
                answer = QMessageBox.question(self, "Preserve manual performance", "Replace existing manually edited segments with a new analysis? Choose No to preserve them.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
            self.project.segments = result.segments
        self.project.tail_pause_ms = result.tail_pause_ms
        self.changed()
        self.refresh(0)

    def move(self, direction):
        index = self.selected_index()
        target = max(0, min(len(self.project.segments) - 1, index + direction))
        self.reorder(index, target)

    def reorder(self, source, target):
        reorder(self.project, source, target)
        self.changed()
        self.refresh(target)

    def split_segment(self):
        index = self.selected_index()
        text = self.project.segments[index].text
        words = text.split()
        if len(words) < 2:
            raise ValueError("This segment needs at least two words to split.")
        count, accepted = QInputDialog.getInt(self, "Split segment", "Split after word number:", max(1, len(words) // 2), 1, len(words) - 1)
        if accepted:
            import re
            spans = list(re.finditer(r"\S+", text))
            split(self.project, index, spans[count - 1].end())
            self.changed()
            self.refresh(index)

    def merge_segment(self):
        index = self.selected_index()
        merge(self.project, index)
        self.changed()
        self.refresh(index)

    def delete_segment(self):
        del self.project.segments[self.selected_index()]
        self.changed()
        self.refresh()

    def backend_changed(self, name):
        if name == self.project.backend:
            return
        self.project.backend = name
        for segment in self.project.segments:
            invalidate(segment)
        self.changed()
        self.refresh()
        self.update_capabilities()

    def update_capabilities(self):
        self.acting.capability_note.setText(
            "Praha: optional 5–10s reference audio; no transcript needed. Intensity controls native exaggeration. Named emotions use analysis-time timing suggestions, not native emotion labels."
            if self.project.backend == "praha" else
            "Parler: emotion, emphasis and endings use descriptive prompts (approximate). Speed, pitch and gain use audio processing. No reference cloning."
            if self.project.backend == "parler" else
            "IndicF5: reference audio + transcript required. Emotion uses analysis-time speed/pitch/energy suggestions only. Emphasis, endings and breathiness are not native controls.")
        for key in ("ending", "breathiness", "direction"):
            self.acting.fields[key].setEnabled(self.project.backend == "parler")
        self.acting.fields["emphasis"].setToolTip("Adds mild gain to this entire segment; Parler also receives word emphasis guidance. Use markup to isolate a phrase.")
        self.acting.fields["cfg_weight"].setEnabled(self.project.backend == "praha")
        self.character.fields["speaker"].setEnabled(self.project.backend == "parler")

    def generate(self, selected=False, force=False, ids=None):
        if self.generation.running or self.rendering:
            raise ValueError("Wait for the current audio job or cancel it first.")
        if not self.project.segments:
            self.analyze()
        if any(not s.text.strip() or "[" in s.text or "]" in s.text for s in self.project.segments):
            raise ValueError("Segments must contain speech text only. Enter markup in the dialogue editor and analyze it first.")
        if ids is None:
            ids = [self.project.segments[self.selected_index()].id] if selected else [s.id for s in self.project.segments]
        self.snapshot = {s.id: self.fingerprint(s) for s in self.project.segments if s.id in ids}
        self.failures = []
        self.progress.setValue(0)
        self.generation.start(self.project, self.paths, self.settings, ids, force)

    def fingerprint(self, segment):
        data = asdict(segment)
        for field in ("status", "raw_path", "processed_path", "audio_key", "duration", "pause_before_ms", "manual"):
            data.pop(field)
        return digest({"segment": data, "character": asdict(self.project.characters[segment.character]), "backend": self.project.backend})

    def generation_event(self, kind, value):
        if kind == "message":
            self.statusBar().showMessage(value)
        elif kind == "progress":
            self.progress.setValue(value)
        elif kind == "segment":
            segment = next((s for s in self.project.segments if s.id == value["id"]), None)
            if segment and self.snapshot.get(segment.id) == self.fingerprint(segment):
                for key in ("raw_path", "processed_path", "audio_key", "duration", "status"):
                    setattr(segment, key, value[key])
                self.project.model_revision = value["revision"]
                self.changed()
                self.refresh()
            else:
                self.statusBar().showMessage("Ignored a completed take because its segment was edited during generation.")
        elif kind == "failed":
            self.failures.append(value["error"])
            logging.error(value["trace"])
            for segment in self.project.segments:
                if segment.id == value["id"]:
                    segment.status = "Failed: " + value["error"]
            self.refresh()
        elif kind == "error":
            self.failures.append(value)
        elif kind == "trace":
            logging.error(value)
        elif kind == "cancelled":
            self.statusBar().showMessage(value)

    def generation_finished(self):
        if self.failures:
            self.error("\n\n".join(dict.fromkeys(self.failures)))
        else:
            self.statusBar().showMessage("Audio job finished. Completed takes are ready to preview.")

    def retry_failed(self):
        ids = [s.id for s in self.project.segments if s.status.startswith("Failed")]
        if not ids:
            raise ValueError("No failed segments to retry.")
        self.generate(ids=ids)

    def task(self, function, callback):
        task = FunctionTask(function, self)
        self.tasks.append(task)
        task.message.connect(self.statusBar().showMessage)
        task.result.connect(callback)
        task.error.connect(self.error)
        task.finished.connect(lambda: self.tasks.remove(task))
        task.start()
        return task

    def render(self, processed, callback):
        if self.rendering or self.generation.running:
            raise ValueError("Wait for the current audio job before rendering.")
        self.rendering = True
        project = deepcopy(self.project)
        settings = deepcopy(self.settings)
        def work(message):
            message("Assembling dialogue…")
            for segment in project.segments:
                if processed and segment.raw_path:
                    path = Path(settings.cache_folder) / "takes" / f"{segment.id}-{digest(asdict(segment.performance))[:16]}.wav"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    process_segment(Path(segment.raw_path), path, segment.performance, settings.ffmpeg)
                    segment.processed_path = str(path)
            audio = mix(project, settings.sample_rate, processed)
            if processed:
                audio = master(audio, settings.sample_rate, project.effects, Path(settings.cache_folder) / "temporary", settings.ffmpeg)
            return audio, settings
        task = self.task(work, callback)
        task.finished.connect(lambda: setattr(self, "rendering", False))

    def preview(self, processed=True):
        def ready(result):
            audio, settings = result
            path = Path(settings.cache_folder) / "preview.wav"
            sf.write(path, audio, settings.sample_rate, subtype="PCM_24")
            self.play(str(path))
        self.render(processed, ready)

    def play(self, path):
        self.player.stop()
        self.wave.load(path)
        self.player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        self.player.play()
        self.statusBar().showMessage("Playing · " + Path(path).name)

    def play_segment(self, processed):
        segment = self.project.segments[self.selected_index()]
        if not segment.raw_path:
            raise ValueError("Generate this segment first.")
        if processed:
            if not segment.processed_path:
                path = Path(self.settings.cache_folder) / "takes" / f"{segment.id}-preview.wav"
                process_segment(Path(segment.raw_path), path, segment.performance, self.settings.ffmpeg)
                segment.processed_path = str(path)
            self.play(segment.processed_path)
        else:
            self.play(segment.raw_path)

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export dialogue", str(Path(self.settings.output_folder) / "dialogue.wav"), "WAV (*.wav);;MP3 (*.mp3)")
        if not path:
            return
        def ready(result):
            audio, settings = result
            def write():
                export_audio(audio, Path(path), settings.sample_rate, settings.bit_depth,
                             settings.channels, settings.mp3_bitrate, settings.ffmpeg)
                self.statusBar().showMessage("Export finished: " + path)
            self.guard(write)
        self.render(True, ready)

    def export_ssml(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export SSML for supporting engines", "dialogue.ssml", "SSML (*.ssml)")
        if path:
            Path(path).write_text(to_ssml(self.project.segments, self.project.tail_pause_ms), encoding="utf-8")

    def save(self):
        if self.directory is None:
            path = QFileDialog.getExistingDirectory(self, "Choose project folder (create a new folder for each scene)", str(self.paths.projects))
            if not path:
                return False
            self.directory = Path(path)
            self.project.name = self.directory.name
        save_project(self.project, self.directory)
        self.dirty = False
        self.setWindowTitle(f"Malayalam Voice Studio · {self.project.name}")
        self.statusBar().showMessage("Project saved · " + str(self.directory))
        return True

    def may_discard(self):
        if self.generation.running or self.rendering:
            raise ValueError("Finish or cancel the current audio job first.")
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, "Unsaved scene", "Save changes before leaving this scene?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return self.save() if answer == QMessageBox.StandardButton.Save else answer == QMessageBox.StandardButton.Discard

    def new_project(self):
        if self.may_discard():
            self.project = self.empty_project()
            self.directory = None
            self.editor.editor.clear()
            self.backend.setCurrentText(self.project.backend)
            self.refresh_characters()
            self.refresh()
            self.dirty = False
            self.setWindowTitle("Malayalam Voice Studio · Untitled scene")

    def open_project(self):
        if not self.may_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open scene", str(self.paths.projects), "Project (project.json)")
        if path:
            project, warnings = load_project(Path(path).parent)
            self.project, self.directory = project, Path(path).parent
            self.editor.editor.setPlainText(project.original)
            self.backend.setCurrentText(project.backend)
            self.refresh_characters()
            self.refresh()
            self.dirty = False
            self.setWindowTitle("Malayalam Voice Studio · " + project.name)
            if warnings:
                self.error("\n".join(warnings))

    def batch(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import batch", "", "Dialogue (*.csv *.json)")
        if path:
            count = import_batch(Path(path), self.project)
            self.editor.editor.setPlainText(self.project.original)
            self.changed()
            self.refresh()
            self.statusBar().showMessage(f"Imported {count} lines. Generate to process the batch; Retry failed preserves successful takes.")

    def reference(self):
        name = self.character.selector.currentText()
        original = deepcopy(self.project.characters[name])
        dialog = ReferenceDialog(self.project.characters[name], self.paths, self.settings, self)
        if dialog.exec():
            if original != self.project.characters[name] and self.project.backend in ("indicf5", "praha"):
                for segment in self.project.segments:
                    if segment.character == name:
                        invalidate(segment)
            self.character.set_character(self.project.characters[name])
            self.changed()

    def effects(self):
        dialog = EffectsDialog(self.project.effects, self.project.breath_assets, self)
        if dialog.exec():
            self.project.effects, self.project.breath_assets = dialog.value()
            self.changed()

    def configure(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.value()
            for path in (self.settings.output_folder, self.settings.cache_folder):
                if not path:
                    raise ValueError("Output and cache folders must not be empty.")
                Path(path).mkdir(parents=True, exist_ok=True)
            self.paths.save_settings(self.settings)
            self.hardware()

    def models(self):
        if self.generation.running:
            raise ValueError("Stop generation before managing model files.")
        ModelManagerDialog(self.paths, self.settings, self).exec()

    def hardware(self):
        def ready(info):
            self.hardware_label.setText(f"CUDA: {'Available' if info['available'] else 'Not available'}   ·   {info['gpu']}   ·   VRAM {info['vram_gb']} GB   ·   Device: {self.settings.device}")
        self.task(lambda message: detect(), ready)

    def save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save performance preset", str(self.paths.voices / "performance.json"), "JSON (*.json)")
        if path:
            atomic_json(Path(path), asdict(self.acting.value()))

    def load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load performance preset", str(self.paths.voices), "JSON (*.json)")
        if path:
            performance = Performance(**json.loads(Path(path).read_text(encoding="utf-8")))
            performance.validate()
            self.acting.set_value(performance)

    def closeEvent(self, event):
        try:
            if any(task.isRunning() for task in self.tasks):
                self.statusBar().showMessage("Wait for background audio work before closing.")
                event.ignore()
            elif self.may_discard():
                self.generation.shutdown()
                self.player.stop()
                event.accept()
            else:
                event.ignore()
        except Exception as exc:
            self.error(str(exc))
            event.ignore()
