from copy import deepcopy

from .domain import Project, Segment, new_id


def invalidate(segment: Segment) -> None:
    segment.raw_path = segment.processed_path = segment.audio_key = ""
    segment.duration = 0
    segment.status = "Not generated"


def split(project: Project, index: int, position: int) -> None:
    original = project.segments[index]
    left, right = original.text[:position].strip(), original.text[position:].strip()
    if not left or not right:
        raise ValueError("Split inside the segment, between words.")
    second = deepcopy(original)
    second.id = new_id()
    original.text, second.text = left, right
    second.pause_before_ms = 120
    for segment in (original, second):
        invalidate(segment)
        segment.manual = True
    project.segments.insert(index + 1, second)


def merge(project: Project, index: int) -> None:
    if index + 1 >= len(project.segments):
        raise ValueError("Select a segment with a following segment to merge.")
    first, second = project.segments[index:index + 2]
    if first.character != second.character:
        raise ValueError("Segments from different characters cannot be merged.")
    first.text = first.text.rstrip() + " " + second.text.lstrip()
    first.manual = True
    invalidate(first)
    del project.segments[index + 1]


def reorder(project: Project, source: int, target: int) -> None:
    segment = project.segments.pop(source)
    project.segments.insert(target, segment)
