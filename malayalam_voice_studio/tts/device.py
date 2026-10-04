from __future__ import annotations


def detect() -> dict:
    try:
        import torch
        available = torch.cuda.is_available()
        return {"available": available, "gpu": torch.cuda.get_device_name(0) if available else "CPU",
                "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2) if available else 0,
                "torch": torch.__version__}
    except ImportError:
        return {"available": False, "gpu": "PyTorch not installed", "vram_gb": 0, "torch": "Missing"}


def resolve(choice: str, available: bool) -> tuple[str, str]:
    if choice == "CUDA" and not available:
        raise ValueError("CUDA unavailable. Install CUDA-enabled PyTorch or select Auto/CPU in Settings.")
    if choice == "CPU":
        return "cpu", "Using CPU"
    if available:
        return "cuda:0", "Using CUDA"
    return "cpu", "CUDA unavailable; Auto selected CPU. Generation may be slow."
