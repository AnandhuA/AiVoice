import re
import unicodedata


def normalize(text: str, substitutions: dict[str, str] | None = None) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("…", "...")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\.{4,}", "...", text)
    text = re.sub(r"([!?])\1+", r"\1", text)
    for original, spoken in sorted((substitutions or {}).items(), key=lambda pair: -len(pair[0])):
        if original:
            text = text.replace(original, spoken)
    return text.strip()


def natural_suggestion(text: str) -> str:
    # Deliberately narrow: no translation model and no inferred story changes.
    return text.replace("നീ എന്താണ് ചെയ്യുന്നത് എന്ന്", "നീ എന്താ ചെയ്യുന്നതെന്ന്").replace(
        "എനിക്ക് അറിയില്ലെന്ന് കരുതുന്നുണ്ടോ?", "എനിക്ക് അറിയില്ലെന്നാണോ കരുതുന്നത്?")
