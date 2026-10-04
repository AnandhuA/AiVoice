from .base import TTSBackend


def create_backend(name: str) -> TTSBackend:
    if name == "praha":
        from .praha_backend import PrahaBackend
        return PrahaBackend()
    if name == "parler":
        from .parler_backend import ParlerBackend
        return ParlerBackend()
    if name == "indicf5":
        from .indic_backend import IndicF5Backend
        return IndicF5Backend()
    if name == "xtts":
        raise ValueError("Stock XTTS-v2 does not support Malayalam. Select Indic Parler-TTS or IndicF5.")
    raise ValueError(f"Unregistered TTS backend: {name}")
