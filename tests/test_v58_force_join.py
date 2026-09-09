from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "bot/handlers/middleware.py"
COMMANDS = ROOT / "bot/handlers/commands.py"


def test_start_handler_uses_full_membership_middleware():
    text = COMMANDS.read_text(encoding="utf-8")
    start = text.index("async def start(")
    body = text[start:text.index("async def ", start + 10)]
    assert "check_and_rate_limit(update, context)" in body
    assert "start_rate_limit(update, context)" not in body


def test_middleware_does_not_bypass_membership_for_start():
    text = MIDDLEWARE.read_text(encoding="utf-8")
    start = text.index("async def check_and_rate_limit(")
    body = text[start:]
    assert "Force-join is enforced for every user-facing update, including /start." in body
    assert "if not await check_membership(update, context):" in body
    assert "is_start" not in body


def test_membership_is_fail_closed_and_accepts_restricted_members():
    text = MIDDLEWARE.read_text(encoding="utf-8")
    assert "return False" in text[text.index("async def check_membership("):text.index("async def ensure_user_registered(")]
    assert 'member.status == "restricted"' in text
    assert 'getattr(member, "is_member", False)' in text
