import json

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout

from ..tts.model_manager import MODELS, download_plan, inspect_install, install, remove
from .tasks import FunctionTask
from .widgets import button


class ModelManagerDialog(QDialog):
    def __init__(self, paths, settings, parent=None):
        super().__init__(parent)
        self.paths, self.settings = paths, settings
        self.task = None
        self.setWindowTitle("Local model library")
        self.resize(1000, 500)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Model", "Installed", "Size", "Device", "Language", "Reference", "Emotion", "Status"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        self.status = QLabel("Downloads require your approval. Gated models may require Hugging Face login and accepted terms.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.buttons = []
        for label, action in [("Install / resume…", self.plan), ("Remove", self.remove), ("Refresh", self.refresh), ("Set default", self.default)]:
            b = button(label, action)
            row.addWidget(b)
            self.buttons.append(b)
        layout.addLayout(row)
        self.refresh()

    def selected(self):
        return list(MODELS)[max(0, self.table.currentRow())]

    def refresh(self):
        self.table.setRowCount(len(MODELS))
        for row, (key, meta) in enumerate(MODELS.items()):
            state = inspect_install(self.paths.models, key)
            validation = self.paths.models / key / "validation.json"
            check = json.loads(validation.read_text(encoding="utf-8")) if validation.exists() else {}
            values = [meta["name"], "Yes" if state["installed"] else "No", f"{state['size'] / 1024**3:.2f} GiB",
                      check.get("device", self.settings.device), "Malayalam", "Yes" if meta["reference"] else "No", meta["emotion"], check.get("status", meta["status"])]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def run_task(self, function, result):
        for b in self.buttons:
            b.setEnabled(False)
        self.task = FunctionTask(function, self)
        self.task.message.connect(self.status.setText)
        self.task.result.connect(result)
        self.task.error.connect(lambda text: QMessageBox.warning(self, "Model operation failed", text))
        self.task.finished.connect(lambda: [b.setEnabled(True) for b in self.buttons])
        self.task.start()

    def plan(self):
        key = self.selected()
        self.status.setText("Reading model metadata and file sizes…")
        self.run_task(lambda message: download_plan(key), self.confirm_plan)

    def confirm_plan(self, plan):
        # Queue installation after the metadata QThread has exited.
        from PySide6.QtCore import QTimer
        prompt = QMessageBox(self)
        prompt.setWindowTitle("Approve model download")
        prompt.setText(f"Download {MODELS[plan['name']]['name']}?\n{plan['bytes'] / 1024**3:.2f} GiB · {plan['license']}\nGated access terms must already be accepted. Generation remains local.")
        prompt.setDetailedText(json.dumps(plan, indent=2))
        prompt.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if prompt.exec() == QMessageBox.StandardButton.Yes:
            QTimer.singleShot(100, lambda: self.run_task(lambda message: install(self.paths.models, plan, message), lambda _: self.installed()))

    def installed(self):
        self.refresh()
        self.status.setText("Model files installed. Generate a short line to validate inference on this machine.")

    def remove(self):
        if QMessageBox.question(self, "Remove model", "Remove this model's files? Project audio is retained.") == QMessageBox.StandardButton.Yes:
            try:
                remove(self.paths.models, self.selected())
                self.refresh()
            except Exception as exc:
                QMessageBox.warning(self, "Removal failed", str(exc))

    def default(self):
        self.settings.backend = self.selected()
        self.paths.save_settings(self.settings)
        self.status.setText("Default backend saved for new scenes.")

    def reject(self):
        if self.task and self.task.isRunning():
            self.status.setText("Wait for the current model operation to finish before closing.")
            return
        super().reject()

    def closeEvent(self, event):
        if self.task and self.task.isRunning():
            event.ignore()
        else:
            event.accept()
