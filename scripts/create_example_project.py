from pathlib import Path

from malayalam_voice_studio.core.acting_engine import analyze
from malayalam_voice_studio.core.domain import Project, Performance
from malayalam_voice_studio.core.presets import characters
from malayalam_voice_studio.core.project_manager import save_project


scene = Project(name='Malayalam confrontation', backend='praha', characters=characters())
scene.original = 'നീ... [PAUSE:400] ഇവിടെ വന്നത് എന്തിനാ?\nനമുക്ക് പോകാം.'
analysis = analyze(scene.original, 'Arthur', Performance(emotion='Suspicious', intensity=.65, style='Cinematic'))
scene.segments = analysis.segments
scene.tail_pause_ms = analysis.tail_pause_ms
save_project(scene, Path('examples/confrontation'))
