from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
import time
from uuid import uuid4

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QThread, QTimer, Signal

from ..core.config import atomic_json


class FunctionTask(QThread):
    result = Signal(object)
    error = Signal(str)
    message = Signal(str)

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.result.emit(self.function(self.message.emit))
        except Exception as exc:
            import logging
            logging.exception("Background operation failed")
            self.error.emit(str(exc))


class GenerationController(QObject):
    event = Signal(str, object)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.cancel_at = None
        self.terminal = False

    @property
    def running(self):
        return self.process is not None

    def start(self, project, paths, settings, selected, force=False):
        if self.running:
            raise ValueError("A generation job is already running.")
        executable = settings.inference_python or sys.executable
        if project.backend == "praha" and not settings.inference_python:
            candidate = paths.root / '.praha' / 'Scripts' / 'python.exe'
            if candidate.is_file():
                executable = str(candidate)
        if not Path(executable).is_file():
            raise ValueError("Inference Python executable does not exist. Check Settings.")
        folder = Path(settings.cache_folder or paths.cache) / 'jobs'
        folder.mkdir(parents=True, exist_ok=True)
        name = uuid4().hex
        self.job_file, self.cancel_file = folder / f'{name}.json', folder / f'{name}.cancel'
        atomic_json(self.job_file, {'project': project.to_dict(), 'model_root': str(paths.models),
            'cache': settings.cache_folder or str(paths.cache), 'device': settings.device,
            'ffmpeg': settings.ffmpeg, 'selected': selected, 'force': force,
            'cancel_file': str(self.cancel_file)})
        self.process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert('PYTHONUTF8', '1')
        environment.insert('HF_HOME', str(paths.models / 'hf-cache'))
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(paths.root))
        self.process.setProgram(executable)
        self.process.setArguments(['-u', '-m', 'malayalam_voice_studio.worker_cli', str(self.job_file)])
        self.stdout_buffer = ''
        self.process.start()
        if not self.process.waitForStarted(3000):
            message = self.process.errorString()
            self.process.deleteLater()
            self.process = None
            self.job_file.unlink(missing_ok=True)
            raise ValueError('Could not start inference worker: ' + message)
        self.last_event = time.monotonic()
        self.timeout = settings.timeout_seconds
        self.cancel_at, self.terminal = None, False
        self.timer.start()

    def cancel(self):
        if self.running:
            self.cancel_file.touch()
            self.cancel_at = time.monotonic()
            self.event.emit("message", "Cancelling; completed takes will be kept…")

    def poll(self):
        if not self.process:
            return
        self.stdout_buffer += bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        lines = self.stdout_buffer.split('\n')
        self.stdout_buffer = lines.pop()
        for line in lines:
            if not line.startswith('MVS_EVENT '):
                if line.strip():
                    logging.info('Inference: %s', line)
                continue
            try:
                kind, value = json.loads(line[len('MVS_EVENT '):])
            except (ValueError, TypeError):
                logging.error('Invalid inference event: %s', line)
                continue
            self.last_event = time.monotonic()
            if kind in ("done", "error", "cancelled"):
                self.terminal = True
            self.event.emit(kind, value)
        stderr = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace')
        if stderr.strip():
            logging.info('Inference diagnostics: %s', stderr)
        elapsed = time.monotonic() - self.last_event
        if (self.cancel_at and time.monotonic() - self.cancel_at > 3) or elapsed > self.timeout:
            self.process.kill()
            self.process.waitForFinished(2000)
            if not self.terminal:
                self.event.emit("cancelled" if self.cancel_at else "error",
                                "Generation cancelled." if self.cancel_at else "Generation timed out. Shorten the segment or increase the timeout in Settings.")
            self.terminal = True
        if self.process.state() == QProcess.ProcessState.NotRunning:
            if not self.terminal:
                self.event.emit("error", f"Inference worker stopped unexpectedly (exit {self.process.exitCode()}). Check logs and retry on CPU.")
            self.process.deleteLater()
            self.process = None
            self.job_file.unlink(missing_ok=True)
            self.cancel_file.unlink(missing_ok=True)
            self.timer.stop()
            self.finished.emit()

    def shutdown(self):
        if self.process:
            self.process.kill()
            self.process.waitForFinished(2000)
            self.process.deleteLater()
            self.process = None
            self.job_file.unlink(missing_ok=True)
            self.cancel_file.unlink(missing_ok=True)
        self.timer.stop()
