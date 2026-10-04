from dataclasses import asdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QSlider

from ..core.domain import EMOTIONS, STYLES, Performance
from .widgets import Card, Disclosure, button, combo, form_widget, number


class ActingPanel(Card):
    apply_requested = Signal()
    save_preset = Signal()
    load_preset = Signal()

    def __init__(self):
        super().__init__("DELIVERY")
        widget, form = form_widget()
        advanced_widget, advanced_form = form_widget()
        self.details = Disclosure("Advanced acting controls")
        self.fields = {
            "emotion": combo(EMOTIONS), "style": combo(STYLES),
            "speed": number(.5, 2, 1), "pitch": number(-12, 12, 0, .5),
            "energy": number(0, 1, .7), "breathiness": number(0, 1, 0),
            "pause_strength": number(0, 3, 1), "volume_db": number(-60, 12, 0, .5),
            "emphasis": QLineEdit(), "breath": combo(["None", "Short", "Medium", "Heavy"]),
            "ending": combo(["Auto", "Question", "Falling", "Suspended"]), "direction": QLineEdit(),
            "cfg_weight": number(0, 1, .5),
        }
        self.intensity = QSlider(Qt.Orientation.Horizontal)
        self.intensity.setRange(0, 100)
        self.intensity.setValue(50)
        self.intensity_label = QLabel("Intensity · 50%")
        self.intensity.valueChanged.connect(lambda v: self.intensity_label.setText(f"Intensity · {v}%"))
        form.addRow(self.intensity_label, self.intensity)
        labels = {"pitch": "Pitch · semitones", "volume_db": "Volume · dB", "speed": "Speed · ×",
                  "pause_strength": "Pause strength", "direction": "Custom direction"}
        for key, field in self.fields.items():
            target = form if key in ("emotion", "speed") else advanced_form
            target.addRow(labels.get(key, key.title()), field)
        self.box.addWidget(widget)
        self.details.box.addWidget(advanced_widget)
        self.capability_note = QLabel("Emotion, emphasis and endings are model prompts. Speed, pitch and gain are audio controls. Breathiness is experimental.")
        self.capability_note.setWordWrap(True)
        self.capability_note.setObjectName("muted")
        self.details.box.addWidget(self.capability_note)
        self.box.addWidget(button("Apply to selected segment", self.apply_requested.emit, True))
        row = QHBoxLayout()
        row.addWidget(button("Save preset", self.save_preset.emit))
        row.addWidget(button("Load preset", self.load_preset.emit))
        self.details.box.addLayout(row)
        self.box.addWidget(self.details)

    def value(self) -> Performance:
        values = {key: field.currentText() if hasattr(field, "currentText") else field.value()
                  if hasattr(field, "value") else field.text() for key, field in self.fields.items()}
        result = Performance(**values, intensity=self.intensity.value() / 100)
        result.validate()
        return result

    def set_value(self, performance: Performance) -> None:
        for key, value in asdict(performance).items():
            if key == "intensity":
                self.intensity.setValue(round(value * 100))
                continue
            field = self.fields[key]
            if hasattr(field, "setCurrentText"):
                field.setCurrentText(value)
            elif hasattr(field, "setValue"):
                field.setValue(value)
            else:
                field.setText(value)
