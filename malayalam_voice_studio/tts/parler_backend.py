from pathlib import Path
from typing import Callable

from .base import AudioResult, Capabilities, GenerationRequest, LocalTTSBackend
from ..core.presets import EMOTION_HINTS


def description(request: GenerationRequest) -> str:
    character, p = request.character, request.segment.performance
    intensity = "slightly" if p.intensity < .35 else "moderately" if p.intensity < .7 else "strongly"
    return (f"{character.speaker} speaks in a {intensity} {EMOTION_HINTS.get(p.emotion, p.emotion)} tone. "
            f"The delivery is {p.style.lower()}, with a {character.voice_type.lower()} voice. "
            f"{p.direction} "
            f"{'A breathy delivery. ' if p.breathiness > .5 else ''}"
            f"{'A questioning ending. ' if p.ending == 'Question' else ''}"
            f"{'A falling ending. ' if p.ending == 'Falling' else ''}"
            f"{'Emphasize: ' + p.emphasis + '. ' if p.emphasis else ''}"
            "Moderate speaking rate and pitch. Very clear audio, close microphone, no background noise.")


class ParlerBackend(LocalTTSBackend):
    capabilities = Capabilities(emotion_prompt=True)

    def load(self, model_dir: Path, device: str) -> None:
        self.validate(model_dir)
        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise ValueError("Parler dependencies missing. Run scripts/install_parler.ps1, then restart.") from exc
        self.device = device
        self.model = ParlerTTSForConditionalGeneration.from_pretrained(
            str(model_dir), local_files_only=True,
            torch_dtype=torch.float16 if device.startswith("cuda") else torch.float32).to(device).eval()
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
        self.description_tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir / "description_tokenizer"), local_files_only=True)

    def synthesize(self, request: GenerationRequest, cancelled: Callable[[], bool]) -> AudioResult:
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList

        class Cancel(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return cancelled()

        torch.manual_seed(request.segment.seed)
        prompt = self.tokenizer(request.segment.text, return_tensors="pt").to(self.device)
        caption = self.description_tokenizer(description(request), return_tensors="pt").to(self.device)
        if prompt.input_ids.shape[-1] > 256:
            raise ValueError("Segment exceeds 256 model tokens. Split it into shorter phrases.")
        with torch.inference_mode():
            output = self.model.generate(input_ids=caption.input_ids, attention_mask=caption.attention_mask,
                prompt_input_ids=prompt.input_ids, prompt_attention_mask=prompt.attention_mask,
                max_new_tokens=1800, stopping_criteria=StoppingCriteriaList([Cancel()]))
        if cancelled():
            raise InterruptedError("Generation cancelled.")
        return AudioResult(output.float().cpu().numpy().squeeze(), int(self.model.config.sampling_rate))
