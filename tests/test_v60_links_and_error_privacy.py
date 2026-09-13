import pytest

import asyncio


def test_link_query_extracts_search_phrase_from_previous_answer():
    pytest.importorskip("telegram")
    from bot.handlers.messages import _extract_link_search_query

    answer = (
        "برای خرید، عبارت «خرید جا کارتی چرم طبیعی» را در موتور جستجو سرچ کنید."
    )
    assert _extract_link_search_query("لینکش بفرست", answer) == "خرید جا کارتی چرم طبیعی"


def test_link_query_is_not_triggered_without_previous_answer():
    pytest.importorskip("telegram")
    from bot.handlers.messages import _extract_link_search_query

    assert _extract_link_search_query("لینکش بفرست", "") == ""


def test_web_search_failure_hides_exception_details(monkeypatch):
    import bot.services.ai_extras as extras

    class BrokenClient:
        async def __aenter__(self):
            raise RuntimeError("SECRET_API_KEY_123")
        async def __aexit__(self, *args):
            return False

    class FakeHttpx:
        def AsyncClient(self, **kwargs):
            return BrokenClient()

    monkeypatch.setitem(__import__("sys").modules, "httpx", FakeHttpx())
    result = asyncio.run(extras.web_search("test"))
    assert "SECRET_API_KEY_123" not in result
    assert "جستجوی وب فعلاً در دسترس نیست" in result
