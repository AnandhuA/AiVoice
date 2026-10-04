from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPen, QFont, QFontMetrics
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsView

from ..core.domain import Project


class SegmentBlock(QGraphicsRectItem):
    def __init__(self, view, index, x, width):
        super().__init__(0, 0, width, 64)
        self.view, self.index = view, index
        self.setPos(x, 25)
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable)
        self.setBrush(QBrush(QColor("#234e50")))
        self.setPen(QPen(QColor("#4e9b91")))

    def mousePressEvent(self, event):
        self.view.selected.emit(self.index)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        target = min(range(len(self.view.positions)), key=lambda i: abs(self.pos().x() - self.view.positions[i]))
        self.view.reordered.emit(self.index, target)


class PauseBlock(QGraphicsRectItem):
    def __init__(self, view, index, x, width, milliseconds):
        super().__init__(x, 25, max(width, 6), 64)
        self.view, self.index, self.milliseconds = view, index, milliseconds
        self.setBrush(QBrush(QColor("#29263b")))
        self.setPen(QPen(QColor("#696080")))
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setToolTip(f"Pause {milliseconds} ms — drag horizontally to adjust")

    def mousePressEvent(self, event):
        self.start_x = event.scenePos().x()

    def mouseReleaseEvent(self, event):
        value = max(0, min(60000, self.milliseconds + round((event.scenePos().x() - self.start_x) / self.view.scale_x * 1000)))
        self.view.pause_changed.emit(self.index, value)


class Timeline(QGraphicsView):
    selected = Signal(int)
    reordered = Signal(int, int)
    pause_changed = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.canvas = QGraphicsScene(self)
        self.setScene(self.canvas)
        self.setMinimumHeight(125)
        self.scale_x = 65
        self.positions = []
        self.setBackgroundBrush(QColor("#0f1622"))
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    def refresh(self, project: Project) -> None:
        self.canvas.clear()
        self.positions = []
        x = 12.0
        for i, s in enumerate(project.segments):
            pause_width = s.pause_before_ms / 1000 * self.scale_x
            self.canvas.addItem(PauseBlock(self, i, x, pause_width, s.pause_before_ms))
            x += pause_width
            self.positions.append(x)
            duration = s.duration or max(.5, len(s.text.split()) / 2.8)
            width = max(65, duration * self.scale_x)
            block = SegmentBlock(self, i, x, width)
            self.canvas.addItem(block)
            font = QFont('Nirmala UI', 9)
            metrics = QFontMetrics(font)
            title = metrics.elidedText(f"{i + 1} · {s.performance.emotion}", Qt.TextElideMode.ElideRight, int(width - 8))
            text = metrics.elidedText(s.text, Qt.TextElideMode.ElideRight, int(width - 8))
            label = self.canvas.addText(f"{title}\n{text}\n{'~' if not s.duration else ''}{duration:.1f}s", font)
            label.setDefaultTextColor(QColor("#ddf6ee"))
            label.setParentItem(block)
            label.setPos(4, 0)
            label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            block.setToolTip(s.text + "\nDrag to reorder. Edit exact pauses in the inspector.")
            x += width + 3
        self.canvas.addItem(PauseBlock(self, len(project.segments), x, project.tail_pause_ms / 1000 * self.scale_x, project.tail_pause_ms))
        self.canvas.setSceneRect(0, 0, x + 80, 108)
