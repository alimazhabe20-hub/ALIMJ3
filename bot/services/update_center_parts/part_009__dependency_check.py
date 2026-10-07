from typing import Any

# Auto-split part 9: _dependency_check
def _dependency_check() -> dict[str, Any]:
    required = {
        "telegram": "python-telegram-bot",
        "requests": "requests",
        "httpx": "httpx",
        "flask": "Flask",
        "pypdf": "pypdf",
        "openpyxl": "openpyxl",
        "reportlab": "reportlab",
        "docx": "python-docx",
        "yt_dlp": "yt-dlp",
    }
    missing = [label for module, label in required.items() if importlib.util.find_spec(module) is None]
    return {"ok": not missing, "missing": missing}
