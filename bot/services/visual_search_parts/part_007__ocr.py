# Auto-split part 7: _ocr
def _ocr(image_bytes: bytes) -> str:
    """Run Tesseract locally. Returns empty text when OCR is unavailable."""
    try:
        import pytesseract
        if TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        elif shutil.which("tesseract") is None:
            return ""
        if Image is None:
            return ""
        with Image.open(io.BytesIO(image_bytes)) as im:
            im = im.convert("RGB")
            texts = []
            for lang in ("fas+eng", "eng"):
                try:
                    txt = pytesseract.image_to_string(im, lang=lang, config="--psm 6")
                    if txt and len(txt.strip()) > 1:
                        texts.append(txt.strip())
                        if lang == "fas+eng":
                            break
                except Exception:
                    continue
            return "\n".join(_unique(texts))[:2500]
    except Exception:
        return ""
