from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..audio.processor import read_audio


class Waveform(QWidget):
    selection_changed = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(85)
        self.samples = np.zeros(0)
        self.rate = 48000
        self.selection = (0.0, 0.0)
        self.anchor = 0.0
        self.setToolTip("Drag to select a reference trim range")

    def load(self, path: str) -> None:
        self.samples, self.rate = read_audio(Path(path))
        self.selection = (0.0, len(self.samples) / self.rate)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0c1420"))
        if not len(self.samples):
            painter.setPen(QColor("#6c809b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waveform appears after audio generation")
            return
        duration = len(self.samples) / self.rate
        start, end = self.selection
        painter.fillRect(round(start / duration * self.width()), 0,
                         round((end - start) / duration * self.width()), self.height(), QColor("#17332f"))
        painter.setPen(QPen(QColor("#6cdcbc"), 1))
        width = max(1, self.width())
        for x in range(width):
            chunk = self.samples[int(x * len(self.samples) / width):max(int((x + 1) * len(self.samples) / width), int(x * len(self.samples) / width) + 1)]
            if len(chunk):
                lo, hi = float(chunk.min()), float(chunk.max())
                painter.drawLine(x, int(self.height() * (.5 - hi * .45)), x, int(self.height() * (.5 - lo * .45)))

    def position_seconds(self, event) -> float:
        return max(0, min(1, event.position().x() / max(1, self.width()))) * len(self.samples) / self.rate

    def mousePressEvent(self, event) -> None:
        self.anchor = self.position_seconds(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.selection = tuple(sorted((self.anchor, self.position_seconds(event))))
            self.selection_changed.emit(*self.selection)
            self.update()
