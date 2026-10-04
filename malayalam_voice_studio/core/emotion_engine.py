from copy import deepcopy

from .domain import Performance


# Mild performance suggestions, not claimed model emotion parameters.
# speed multiplier, pitch semitones, energy change, pause multiplier
PRESETS = {
    "Neutral": (1, 0, 0, 1), "Happy": (1.04, .3, .08, .9),
    "Sad": (.92, -.4, -.12, 1.25), "Angry": (1.03, -.2, .16, .9),
    "Controlled anger": (.95, -.3, .05, 1.2), "Fear": (1.02, .4, -.03, 1.1),
    "Suspicious": (.94, -.2, -.03, 1.3), "Threatening": (.91, -.5, .04, 1.35),
    "Calm": (.97, -.1, -.03, 1.1), "Excited": (1.07, .5, .12, .85),
    "Frustrated": (1.02, .1, .08, 1.1), "Confused": (.96, .2, -.03, 1.2),
    "Sarcastic": (.95, -.1, -.02, 1.2), "Whisper": (.96, 0, -.2, 1.15),
    "Shouting": (1.03, .3, .2, .9), "Crying": (.91, .2, -.13, 1.3),
    "Tired": (.9, -.4, -.15, 1.3), "Drunk": (.9, -.2, -.08, 1.3),
}


def suggest(base: Performance) -> Performance:
    result = deepcopy(base)
    speed, pitch, energy, pause = PRESETS.get(base.emotion, (1, 0, 0, 1))
    strength = base.intensity
    result.speed = max(.5, min(2, base.speed * (1 + (speed - 1) * strength)))
    result.pitch = max(-12, min(12, base.pitch + pitch * strength))
    result.energy = max(0, min(1, base.energy + energy * strength))
    result.pause_strength = max(0, min(3, base.pause_strength * (1 + (pause - 1) * strength)))
    return result
