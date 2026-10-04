from .domain import Character, Performance


def characters() -> dict[str, Character]:
    profiles = {
        "Arthur": ("Male", "Harish", "Rough", "Reserved adult outlaw; grounded and deliberate.", .94, -2),
        "Dutch": ("Male", "Harish", "Resonant", "Charismatic leader; theatrical and persuasive.", .97, -1),
        "John": ("Male", "Harish", "Dry", "Direct, guarded adult adventurer.", 1.0, -1),
        "Sadie": ("Female", "Anjali", "Firm", "Determined adult fighter; sharp and assertive.", 1.02, 0),
        "Micah": ("Male", "Harish", "Gravelly", "Unpredictable adult antagonist; sardonic delivery.", .98, 1),
        "Custom Character": ("Male", "Harish", "Warm", "An original character.", 1.0, 0),
    }
    return {name: Character(name=name, gender=v[0], speaker=v[1], voice_type=v[2],
                           description=v[3], performance=Performance(emotion="Calm", speed=v[4], pitch=v[5]))
            for name, v in profiles.items()}


EMOTION_HINTS = {
    "Neutral": "neutral and conversational", "Happy": "happy and bright", "Sad": "sad and restrained",
    "Angry": "angry and firm", "Controlled anger": "restrained anger, controlled and tense",
    "Fear": "fearful and uncertain", "Suspicious": "questioning and wary",
    "Threatening": "quietly commanding and tense", "Calm": "calm and relaxed",
    "Excited": "excited and animated", "Frustrated": "frustrated and impatient",
    "Confused": "uncertain and questioning", "Sarcastic": "dry and ironic",
    "Whisper": "quiet, whispered delivery", "Shouting": "forceful and projected",
    "Crying": "sad with a trembling delivery", "Tired": "weary and subdued",
    "Drunk": "loose and hesitant", "Custom": "expressive",
}
