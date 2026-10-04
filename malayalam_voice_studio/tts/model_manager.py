from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

from ..core.config import atomic_json


MODELS = {
    "praha": {"name": "PrahaTTS-ML + Chatterbox", "repo": "Praha-Labs/PrahaTTS-ML", "license": "Apache-2.0 adapter + MIT base",
              "reference": True, "emotion": "Native exaggeration; named emotions approximate", "status": "Requires local validation"},
    "parler": {"name": "Indic Parler-TTS", "repo": "ai4bharat/indic-parler-tts", "license": "Apache-2.0",
               "reference": False, "emotion": "Descriptive prompts", "status": "Requires local validation"},
    "indicf5": {"name": "IndicF5", "repo": "ai4bharat/IndicF5", "license": "MIT",
                "reference": True, "emotion": "Reference prosody; no emotion slider API", "status": "Experimental Windows adapter"},
}

PARLER_REVISION = "7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca"


def inspect_install(root: Path, name: str) -> dict:
    folder = root / name
    manifest = folder / "studio-model.json"
    data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    complete = bool(data.get("files")) and all((folder / f["target"] / f["file"]).is_file() for f in data.get("files", []))
    return {"installed": complete, "size": sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) if folder.exists() else 0,
            "manifest": data}


def download_plan(name: str) -> dict:
    from huggingface_hub import HfApi
    # Public Praha/base repositories need no credentials; an expired unrelated
    # cached login must not prevent public downloads.
    api = HfApi(token=False if name == "praha" else None)
    sources = [(MODELS[name]["repo"], "")]
    if name == "praha":
        sources.append(("ResembleAI/chatterbox", "base"))
    if name == "parler":
        sources.append(("google/flan-t5-large", "description_tokenizer"))
    entries = []
    for repo, target in sources:
        revisions = {"Praha-Labs/PrahaTTS-ML": "4f93701eb2ccfa19d3b3bfd86e60b0b0778c07f6",
                     "ResembleAI/chatterbox": "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"}
        info = api.model_info(repo, revision=revisions.get(repo, PARLER_REVISION if name == "parler" and not target else "main"), files_metadata=True)
        for file in info.siblings:
            filename = file.rfilename
            if name == "praha":
                keep = filename in (["ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors", "tokenizer.json", "conds.pt"]
                                    if target else ["adapter_config.json", "adapter_model.safetensors", "tokenizer_indic.json"])
            elif target:
                keep = filename in ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "spiece.model", "added_tokens.json", "config.json")
            else:
                keep = filename.endswith((".json", ".safetensors", ".model", ".txt", ".py")) and "/" not in filename
            if keep:
                entries.append({"repo": repo, "revision": info.sha, "file": filename,
                                "target": target, "bytes": file.size or 0,
                                "sha256": getattr(file.lfs, "sha256", None) if file.lfs else None})
    return {"name": name, "files": entries, "bytes": sum(e["bytes"] for e in entries), "license": MODELS[name]["license"]}


def install(root: Path, plan: dict, progress=lambda message: None, cancelled=lambda: False) -> None:
    from huggingface_hub import hf_hub_download
    folder = root / plan["name"]
    folder.mkdir(parents=True, exist_ok=True)
    for index, entry in enumerate(plan["files"]):
        if cancelled():
            raise InterruptedError("Model installation cancelled; downloaded files retained for resume.")
        progress(f"Downloading {index + 1}/{len(plan['files'])}: {entry['file']}")
        for attempt in range(6):
            try:
                downloaded = hf_hub_download(entry["repo"], entry["file"], revision=entry["revision"],
                    local_dir=folder / entry["target"], token=False if plan["name"] == "praha" else None)
                if entry["bytes"] and Path(downloaded).stat().st_size != entry["bytes"]:
                    raise ValueError(f"Downloaded size mismatch for {entry['file']}. Remove the incomplete file and retry.")
                if entry.get('sha256'):
                    from hashlib import sha256
                    checksum = sha256()
                    progress(f"Verifying {entry['file']}…")
                    with open(downloaded, 'rb') as stream:
                        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                            checksum.update(chunk)
                    if checksum.hexdigest() != entry['sha256']:
                        raise ValueError(f"Checksum mismatch for {entry['file']}. File was not accepted; reinstall this model.")
                break
            except Exception as exc:
                from requests import RequestException
                if not isinstance(exc, (RequestException, OSError)) or attempt == 5:
                    raise
                if getattr(getattr(exc, 'response', None), 'status_code', None) in (401, 403, 404):
                    raise
                progress(f"Transfer interrupted; resuming {entry['file']} (retry {attempt + 1}/5).")
                time.sleep(min(2 ** attempt, 16))
    atomic_json(folder / "studio-model.json", plan)


def remove(root: Path, name: str) -> None:
    if name not in MODELS:
        raise ValueError("Unknown model.")
    root = root.resolve()
    folder = root / name
    if folder.is_symlink() or folder.resolve().parent != root:
        raise ValueError("Refusing to remove a model outside the model directory.")
    if folder.exists():
        shutil.rmtree(folder)
