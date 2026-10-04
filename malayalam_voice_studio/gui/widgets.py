from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QLabel,
                               QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget)


class Disclosure(QWidget):
    """Keep optional controls accessible without crowding the default view."""
    def __init__(self, title: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QToolButton()
        self.toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        from PySide6.QtCore import Qt
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.body = QWidget()
        self.box = QVBoxLayout(self.body)
        self.box.setContentsMargins(0, 8, 0, 0)
        self.body.hide()
        def expand(checked):
            self.body.setVisible(checked)
            self.toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.toggle.toggled.connect(expand)
        layout.addWidget(self.toggle)
        layout.addWidget(self.body)


def button(text: str, callback=None, primary: bool = False) -> QPushButton:
    result = QPushButton(text)
    if primary:
        result.setObjectName("primary")
    if callback:
        result.clicked.connect(callback)
    return result


def combo(items: list[str]) -> QComboBox:
    result = QComboBox()
    result.addItems(items)
    return result


def number(low: float, high: float, value: float, step: float = .05, decimals: int = 2) -> QDoubleSpinBox:
    result = QDoubleSpinBox()
    result.setRange(low, high)
    result.setDecimals(decimals)
    result.setSingleStep(step)
    result.setValue(value)
    return result


def heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("section")
    return label


class Card(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("card")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(14, 12, 14, 12)
        self.box.addWidget(heading(title))


def form_widget() -> tuple[QWidget, QFormLayout]:
    widget = QWidget()
    form = QFormLayout(widget)
    form.setContentsMargins(0, 0, 0, 0)
    form.setVerticalSpacing(8)
    return widget, form
