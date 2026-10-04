from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit

from .widgets import Card, Disclosure, button


class DialogueEditor(Card):
    action = Signal(str)

    def __init__(self):
        super().__init__("DIALOGUE")
        self.editor = QPlainTextEdit()
        font = QFont("Nirmala UI", 15)
        self.editor.setFont(font)
        self.editor.setStyleSheet("QPlainTextEdit { font-family: 'Nirmala UI'; font-size: 18px; }")
        self.editor.setPlaceholderText("നീ എന്താണ് ചെയ്യുന്നതെന്ന് എനിക്ക് അറിയില്ലെന്ന് കരുതുന്നുണ്ടോ?\n\nWrite a scene. Shape the performance below.")
        self.editor.setMinimumHeight(160)
        self.box.addWidget(self.editor, 1)
        self.details = Disclosure("Text tools and timing markup")
        for actions in [[("Generate voice", "generate"), ("Play dialogue", "preview")],
                        [("Add line", "add"), ("Split into segments", "analyze"), ("Clear", "clear"), ("Regenerate", "regenerate")]]:
            row = QHBoxLayout()
            for label, action in actions:
                b = button(label, primary=action == "generate")
                b.clicked.connect(lambda checked=False, a=action: self.action.emit(a))
                row.addWidget(b)
            (self.box if actions[0][1] == "generate" else self.details.box).addLayout(row)
        row = QHBoxLayout()
        row.addWidget(button("Natural Malayalam…", lambda: self.action.emit("adapt")))
        row.addWidget(button("Pronunciations…", lambda: self.action.emit("pronunciations")))
        self.details.box.addLayout(row)
        help_text = QLabel("Timing markup: …  [PAUSE:500]  [BREATH]\n[WHISPER]text[/WHISPER]  [EMPHASIS]text[/EMPHASIS]\n[LOW]  [HIGH]  [ANGRY:80] · all decisions remain editable")
        help_text.setWordWrap(True)
        help_text.setObjectName("muted")
        self.details.box.addWidget(help_text)
        self.box.addWidget(self.details)
