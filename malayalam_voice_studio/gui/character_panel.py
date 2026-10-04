from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit

from ..core.domain import Character
from .widgets import Card, Disclosure, button, combo, form_widget


class CharacterPanel(Card):
    selected = Signal(str)
    save_requested = Signal()
    reference_requested = Signal()

    def __init__(self):
        super().__init__("VOICE & CHARACTER")
        self.selector = combo([])
        self.box.addWidget(self.selector)
        widget, form = form_widget()
        self.fields = {"name": QLineEdit(), "gender": combo(["Male", "Female", "Other"]),
            "age": combo(["Young adult", "Adult", "Middle-aged", "Older adult"]),
            "voice_type": QLineEdit(), "accent": QLineEdit(), "speaker": combo(["Harish", "Anjali", "Anju"])}
        for key, field in self.fields.items():
            form.addRow(key.replace("_", " ").title(), field)
        self.details = Disclosure("Character details and defaults")
        self.details.box.addWidget(widget)
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText("Character motivation and general voice characteristics…")
        self.description.setMaximumHeight(90)
        self.details.box.addWidget(self.description)
        self.details.box.addWidget(button("Save character / defaults", self.save_requested.emit))
        self.reference_label = QLabel("No reference attached")
        self.reference_label.setWordWrap(True)
        self.reference_label.setObjectName("muted")
        self.box.addWidget(self.reference_label)
        self.box.addWidget(button("Reference audio…", self.reference_requested.emit))
        note = QLabel("Character presets describe delivery, not game actors. Parler uses named speakers. Praha and IndicF5 support reference audio; only IndicF5 requires a transcript.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        self.details.box.addWidget(note)
        self.box.addWidget(self.details)
        self.selector.currentTextChanged.connect(self.selected.emit)

    def set_character(self, character: Character) -> None:
        for name, field in self.fields.items():
            if hasattr(field, "setCurrentText"):
                field.setCurrentText(getattr(character, name))
            else:
                field.setText(getattr(character, name))
        self.description.setPlainText(character.description)
        self.reference_label.setText(character.reference or "No reference attached")

    def update_character(self, character: Character) -> None:
        for name, field in self.fields.items():
            setattr(character, name, field.currentText() if hasattr(field, "currentText") else field.text().strip())
        character.description = self.description.toPlainText()
