from __future__ import annotations

import torch
from loguru import logger


def best_torch_device() -> str:
    """Return the best available PyTorch device string.

    Order: CUDA → Apple Silicon MPS → CPU.
    """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return "mps"
    return "cpu"


_logged_once = False


def log_device_once(model_label: str, device: str) -> None:
    """Log the active device once (avoids spam when models share a helper)."""
    global _logged_once
    if not _logged_once:
        logger.info(f"PyTorch device for {model_label}: {device}")
        _logged_once = True
    else:
        logger.debug(f"PyTorch device for {model_label}: {device}")
