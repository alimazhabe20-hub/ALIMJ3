# Auto-split part 10: _vision_caption
def _vision_caption(image_bytes: bytes) -> str:
    if Image is None:
        return ""
    processor, model = _load_vision_model()
    if processor is None or model is None:
        return ""
    try:
        import torch
        with Image.open(io.BytesIO(image_bytes)) as im:
            image = im.convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=45, num_beams=3)
        return processor.decode(output[0], skip_special_tokens=True).strip()
    except Exception:
        return ""
