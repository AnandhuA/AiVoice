import unicodedata
import xml.etree.ElementTree as ET

import pytest

from malayalam_voice_studio.core.acting_engine import analyze, to_ssml
from malayalam_voice_studio.core.domain import Performance
from malayalam_voice_studio.core.text_normalizer import normalize, natural_suggestion


@pytest.mark.parametrize("text", ["നീ എന്താണ് ചെയ്യുന്നത്?", "ഹാ", "നമുക്ക് പോകാം. വേഗം വരൂ!",
                                    "John, നീ ready ആണോ?", "ൻ ൽ ൾ ൺ ർ ൿ ക്‍", "3.14 Dr.Smith", "“നീ?”"])
def test_unicode_preserved(text):
    result = analyze(text, "Arthur", Performance())
    assert result.segments
    spoken = " ".join(s.text for s in result.segments)
    for character in unicodedata.normalize("NFC", text):
        if not character.isspace():
            assert character in spoken


def test_explicit_pause_overrides_ellipsis():
    result = analyze("നീ... [PAUSE:400] ഇവിടെ വന്നത് എന്തിനാ?", "Arthur", Performance())
    assert len(result.segments) == 2
    assert result.segments[1].pause_before_ms == 400
    assert result.segments[1].performance.ending == "Question"
    assert "[" not in "".join(s.text for s in result.segments)


def test_nested_markup_and_emotion():
    result = analyze("[WHISPER][EMPHASIS]നീ[/EMPHASIS][/WHISPER] [ANGRY:80][LOW] പോകൂ [PAUSE:250]", "Arthur", Performance())
    assert result.segments[0].performance.emphasis == "നീ"
    assert result.segments[0].performance.emotion == "Whisper"
    assert result.segments[-1].performance.emotion == "Angry"
    assert result.segments[-1].performance.intensity == .8
    assert result.segments[-1].performance.pitch == -2
    assert result.tail_pause_ms == 250


@pytest.mark.parametrize("text", ["[PAUSE:-1]നീ", "[PAUSE:abc]", "[ANGRY:101]", "[WHISPER]നീ", "[EMPHASIS]നീ[/WHISPER]", "[BOGUS]നീ", "നീ [", "[BREATH]"])
def test_invalid_markup(text):
    with pytest.raises(ValueError):
        analyze(text, "Arthur", Performance())


def test_long_dialogue_no_loss():
    text = " ".join(["മലയാളം"] * 2000)
    result = analyze(text, "Arthur", Performance())
    assert len(result.segments) > 50
    assert sum(s.text.count("മലയാളം") for s in result.segments) == 2000
    assert all(len(s.text) <= 180 for s in result.segments)


def test_normalization_is_conservative():
    assert normalize("  നീ!!!!\r\n എന്താ...... ") == "നീ!\n എന്താ..."
    assert normalize("12 NASA Dr.") == "12 NASA Dr."
    assert normalize("Dr.", {"Dr.": "ഡോക്ടർ"}) == "ഡോക്ടർ"
    assert natural_suggestion("നമുക്ക് പോകാം.") == "നമുക്ക് പോകാം."


def test_ssml_is_valid_and_escaped():
    result = analyze("A & B < C?", "Arthur", Performance())
    document = ET.fromstring(to_ssml(result.segments, 200))
    assert document.tag == "speak"
    assert "A & B < C?" in "".join(document.itertext())


def test_breath_only_at_requested_boundary():
    result = analyze("നീ [BREATH] വരൂ", "Arthur", Performance())
    assert result.segments[0].performance.breath == "None"
    assert result.segments[1].performance.breath == "Short"
