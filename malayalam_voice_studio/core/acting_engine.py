from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from xml.sax.saxutils import escape

from .domain import Performance, Segment, new_id
from .emotion_engine import suggest
from .text_normalizer import normalize


@dataclass
class Analysis:
    segments: list[Segment]
    tail_pause_ms: int


def analyze(text: str, character: str, base: Performance,
            substitutions: dict[str, str] | None = None) -> Analysis:
    text = normalize(text, substitutions)
    if not text:
        return Analysis([], 0)
    state = suggest(base)
    stack: list[tuple[str, Performance]] = []
    segments: list[Segment] = []
    pending = 0
    explicit = False
    line_id = new_id()
    emphasis = False
    next_breath = "None"

    def add_text(chunk: str) -> None:
        nonlocal pending, explicit, next_breath, line_id
        # Decimal points and intra-word abbreviations do not end phrases.
        parts = re.split(r"(\.{3}|[!?।]+|[,;:]|\.(?=\s|$)|\n+)", chunk)
        for i in range(0, len(parts), 2):
            phrase = parts[i].strip()
            delimiter = parts[i + 1] if i + 1 < len(parts) else ""
            if phrase:
                words = phrase.split()
                # Bound chunks conservatively; never discard overflow.
                batches: list[str] = []
                current = ""
                for word in words:
                    if len(word) > 350:
                        raise ValueError("A single word exceeds 350 characters. Check the dialogue text.")
                    if current and (len(current) + len(word) > 180 or len(current.split()) >= 22):
                        batches.append(current)
                        current = ""
                    current = f"{current} {word}".strip()
                if current:
                    batches.append(current)
                for j, batch in enumerate(batches):
                    perf = deepcopy(state)
                    if emphasis:
                        perf.emphasis = batch
                    if next_breath != "None":
                        perf.breath = next_breath
                        next_breath = "None"
                    if j == len(batches) - 1 and "?" in delimiter:
                        perf.ending = "Question"
                    elif j == len(batches) - 1 and delimiter in [".", "!", "।"]:
                        perf.ending = "Falling"
                    spoken = batch + (delimiter.strip() if j == len(batches) - 1 else "")
                    segments.append(Segment(text=spoken, character=character, line_id=line_id,
                                            performance=perf, pause_before_ms=pending))
                    pending, explicit = 120, False
            if delimiter:
                delay = 450 if delimiter == "..." else 300 if "\n" in delimiter else 260 if delimiter in [".", "!", "?", "।"] else 150
                if not explicit:
                    pending = round(delay * state.pause_strength)
                if "\n" in delimiter:
                    line_id = new_id()

    for token in re.split(r"(\[[^\]]*\])", text):
        if not token:
            continue
        if not token.startswith("["):
            if "[" in token or "]" in token:
                raise ValueError("Unclosed acting markup. Check square brackets.")
            add_text(token)
            continue
        tag = token[1:-1].upper()
        if tag.startswith("PAUSE:"):
            try:
                value = int(tag.split(":", 1)[1])
            except ValueError as exc:
                raise ValueError("Use [PAUSE:500] with integer milliseconds.") from exc
            if not 0 <= value <= 60000:
                raise ValueError("Pause must be 0–60000 ms.")
            pending, explicit = value, True
        elif tag == "BREATH":
            next_breath = "Short"
        elif tag in ["WHISPER", "EMPHASIS"]:
            stack.append((tag, deepcopy(state)))
            if tag == "WHISPER":
                state.emotion = "Whisper"
            else:
                emphasis = True
        elif tag in ["/WHISPER", "/EMPHASIS"]:
            if not stack or stack[-1][0] != tag[1:]:
                raise ValueError(f"Mismatched markup: {token}")
            _, state = stack.pop()
            emphasis = any(t == "EMPHASIS" for t, _ in stack)
        elif tag in ["LOW", "HIGH"]:
            state.pitch = -2.0 if tag == "LOW" else 2.0
        elif tag.startswith("ANGRY:"):
            try:
                state.intensity = int(tag.split(":", 1)[1]) / 100
                state.validate()
            except ValueError as exc:
                raise ValueError("Use [ANGRY:0] through [ANGRY:100].") from exc
            state.emotion = "Angry"
        else:
            raise ValueError(f"Unknown acting markup: {token}")
    if stack:
        raise ValueError(f"Close [{stack[-1][0]}] before generating.")
    if next_breath != "None":
        raise ValueError("Place [BREATH] before a spoken phrase.")
    return Analysis(segments, pending if explicit else 0)


def to_ssml(segments: list[Segment], tail_ms: int = 0) -> str:
    parts = ["<speak>"]
    for s in segments:
        parts.append(f'<break time="{s.pause_before_ms}ms"/>')
        value = escape(s.text)
        if s.performance.emphasis and s.performance.emphasis in s.text:
            target = escape(s.performance.emphasis)
            value = value.replace(target, f'<emphasis level="strong">{target}</emphasis>')
        parts.append(f'<prosody rate="{s.performance.speed * 100:.0f}%" pitch="{s.performance.pitch:+.1f}st">{value}</prosody>')
    parts.append(f'<break time="{tail_ms}ms"/></speak>')
    return "".join(parts)
