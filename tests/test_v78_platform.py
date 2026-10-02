import ast
from pathlib import Path


def test_v71_handler_imports_detect_language_from_v71_platform():
    tree = ast.parse(Path("bot/handlers/v71_handlers.py").read_text(encoding="utf-8"))
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom)]
    assert any(
        n.module == "bot.services.v71_platform" and any(a.name == "detect_language" for a in n.names)
        for n in imports
    )
    assert not any(
        n.module == "bot.services.v72_platform" and any(a.name == "detect_language" for a in n.names)
        for n in imports
    )


def test_v78_release_is_declared():
    # V78 is historical; the runtime release is newer.
    text = Path("V78_RELEASE.md").read_text(encoding="utf-8")
    assert "V78.0.0" in text
