from typing import Any

# Auto-split part 11: verify_result
def verify_result(result: Any, *, expected: str = "") -> dict[str, Any]:
    text = redact(result, 6000).strip()
    failed = not text or text.startswith(("خطا", "Error", "ابزار ناشناخته", "Tool blocked", "زمان اجرای"))
    return {"ok": not failed, "nonempty": bool(text), "expected_match": bool(expected and expected.lower() in text.lower()), "safe": not bool(_SECRET.search(text)), "preview": text[:1000]}
