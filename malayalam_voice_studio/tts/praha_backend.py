"""Praha Malayalam adapter on Chatterbox non-turbo; no online loading."""
from copy import deepcopy
import json
from pathlib import Path
from typing import Callable

from .base import AudioResult, Capabilities, GenerationRequest, LocalTTSBackend


class PrahaBackend(LocalTTSBackend):
    capabilities = Capabilities(reference=True)

    def validate(self, model_dir: Path) -> None:
        required = ['adapter_config.json', 'adapter_model.safetensors', 'tokenizer_indic.json',
                    'base/ve.safetensors', 'base/t3_cfg.safetensors', 'base/s3gen.safetensors',
                    'base/tokenizer.json', 'base/conds.pt']
        missing = [name for name in required if not (model_dir / name).is_file()]
        if missing:
            raise ValueError('Praha model missing files: ' + ', '.join(missing) + '. Install Praha + Chatterbox from Models.')

    def load(self, model_dir: Path, device: str) -> None:
        self.validate(model_dir)
        try:
            import torch
            from torch import nn
            from chatterbox.tts import ChatterboxTTS
            from chatterbox.models.tokenizers import EnTokenizer
            from peft import PeftModel
            from safetensors import safe_open
        except ImportError as exc:
            raise ValueError('Praha dependencies missing. Run scripts/install_praha.ps1 and use its environment in Settings.') from exc
        self.model = ChatterboxTTS.from_local(model_dir / 'base', device=device)
        tokenizer_file = model_dir / 'tokenizer_indic.json'
        self.model.tokenizer = EnTokenizer(str(tokenizer_file))
        tokenizer_data = json.loads(tokenizer_file.read_text(encoding='utf-8'))
        ids = list(tokenizer_data['model']['vocab'].values())
        ids.extend(t['id'] for t in tokenizer_data.get('added_tokens', []))
        vocab_size = max(ids) + 1
        with safe_open(model_dir / 'adapter_model.safetensors', framework='pt', device='cpu') as weights:
            embedding_keys = [k for k in weights.keys() if 'text_emb' in k and k.endswith('weight')]
            if not embedding_keys:
                raise ValueError('Praha adapter does not contain the trained text embeddings; refusing random vocabulary weights.')
            shape = weights.get_slice(embedding_keys[0]).get_shape()
            if shape[0] != vocab_size:
                raise ValueError(f'Adapter/tokenizer vocabulary mismatch: {shape[0]} versus {vocab_size}.')
        target = self.model.t3
        target.text_emb = nn.Embedding(vocab_size, target.text_emb.embedding_dim).to(device)
        target.text_head = nn.Linear(target.text_head.in_features, vocab_size,
                                    bias=target.text_head.bias is not None).to(device)
        self.model.t3 = PeftModel.from_pretrained(target, str(model_dir), local_files_only=True).eval()
        self.default_conditionals = deepcopy(self.model.conds)

    def unload(self) -> None:
        if hasattr(self, 'default_conditionals'):
            del self.default_conditionals
        super().unload()

    def synthesize(self, request: GenerationRequest, cancelled: Callable[[], bool]) -> AudioResult:
        import torch
        if cancelled():
            raise InterruptedError('Generation cancelled.')
        reference = request.character.reference
        if reference and not Path(reference).is_file():
            raise ValueError('Reference audio is missing. Reimport it or clear the reference.')
        # Chatterbox caches reference conditioning; reset it to prevent a previous
        # character reference leaking into a later default-voice generation.
        self.model.conds = deepcopy(self.default_conditionals)
        torch.manual_seed(request.segment.seed)
        with torch.inference_mode():
            wav = self.model.generate(request.segment.text, audio_prompt_path=reference or None,
                exaggeration=request.segment.performance.intensity, cfg_weight=request.segment.performance.cfg_weight)
        if cancelled():
            raise InterruptedError('Generation cancelled.')
        return AudioResult(wav.detach().float().cpu().numpy().squeeze(), self.model.sr)
