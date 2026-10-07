from typing import Any

# Auto-split part 9: _load_vision_model
def _load_vision_model() -> tuple[Any, Any] | tuple[None, None]:
    if _VISION_STATE["ready"]:
        return _VISION_STATE["processor"], _VISION_STATE["model"]
    if _VISION_STATE["failed"]:
        return None, None
    try:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch  # noqa: F401

        source = _vision_model_source()
        # Do not silently download on Render when a local path was explicitly requested.
        if LOCAL_VISION_MODEL_PATH and not os.path.exists(LOCAL_VISION_MODEL_PATH):
            _VISION_STATE["failed"] = True
            return None, None

        processor = BlipProcessor.from_pretrained(source, local_files_only=bool(LOCAL_VISION_MODEL_PATH))
        model = BlipForConditionalGeneration.from_pretrained(source, local_files_only=bool(LOCAL_VISION_MODEL_PATH))
        model.eval()
        _VISION_STATE.update({"ready": True, "processor": processor, "model": model})
        return processor, model
    except Exception:
        _VISION_STATE["failed"] = True
        return None, None
