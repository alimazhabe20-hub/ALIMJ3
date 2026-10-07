"""ai_service: memory responsibilities."""
from .ai_service_common import *  # noqa: F401,F403
from . import ai_service_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _memory_block(user_id: int) -> str:
    """بلوک حافظه بلندمدت + خلاصه تاریخچه برای تزریق به سیستم."""
    parts = []
    try:
        from bot.database import get_ai_memory, get_ai_history_summary
        mem = get_ai_memory(user_id, limit=30)
        if mem:
            lines = [f"- {k}: {v}" for k, v in mem]
            parts.append("حافظه بلندمدت درباره این کاربر:\n" + "\n".join(lines))
        summary = get_ai_history_summary(user_id)
        if summary:
            parts.append("خلاصه گفتگوهای قبلی:\n" + summary)
    except Exception as e:
        logger.warning("memory_block: %s", e)
    return "\n\n".join(parts)

def _extract_and_store_memory(user_id: int, prompt: str) -> None:
    """اگر کاربر گفت چیزی را به خاطر بسپار، ذخیره کن."""
    import re
    t = (prompt or "").strip()
    m = re.search(
        r"(?:یادت\s*باشه|به\s*خاطر\s*بسپار|یادت\s*باشه\s*که|من\s*(?:اسمم|نامم)\s*)[:：]?\s*(.+)$",
        t,
        re.I | re.S,
    )
    if not m:
        m2 = re.search(r"اسمم\s+([^\n.،,]{2,40})", t)
        if m2:
            try:
                from bot.database import set_ai_memory
                set_ai_memory(user_id, "name", m2.group(1).strip())
            except Exception:
                pass
        return
    fact = m.group(1).strip()[:500]
    if not fact:
        return
    key = "note"
    if re.search(r"اسم|نام", t):
        key = "name"
    elif re.search(r"شهر|زندگی", t):
        key = "city"
    elif re.search(r"علاقه|دوست\s*دارم", t):
        key = "interest"
    try:
        from bot.database import set_ai_memory
        set_ai_memory(user_id, key, fact)
    except Exception as e:
        logger.warning("store memory: %s", e)

async def _maybe_summarize_history(user_id: int) -> None:
    """وقتی تاریخچه پر شد، یک‌بار خلاصه می‌سازد و بخش قدیمی را سبک می‌کند."""
    history = _HISTORY[user_id]
    if len(history) < HISTORY_ITEMS or user_id in _SUMMARY_RUNNING:
        return

    _SUMMARY_RUNNING.add(user_id)
    try:
        snapshot = list(history)
        lines = []
        for role, content in snapshot:
            tag = "کاربر" if role == "user" else "دستیار"
            lines.append(f"{tag}: {content[:500]}")
        blob = "\n".join(lines)[:5000]
        summary_prompt = (
            "این گفتگو را در حداکثر ۸ خط فارسی خلاصه کن. "
            "حقایق مهم درباره کاربر، تصمیم‌ها و موضوعات اصلی را نگه دار:\n\n" + blob
        )

        summary = None
        for provider, _label, model in available_model_options():
            try:
                if provider == "groq":
                    summary = await _openai_compatible(
                        "Groq", "groq", 0, summary_prompt,
                        url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
                        + "/chat/completions",
                        model=model,
                        use_tools=False,
                    )
                elif provider == "gemini":
                    summary = await _gemini(0, summary_prompt, model, use_tools=False)
                else:
                    continue
                if summary:
                    break
            except Exception:
                continue

        if summary:
            from bot.database import get_ai_history_summary, set_ai_history_summary
            prev = get_ai_history_summary(user_id) or ""
            merged = (prev + "\n" + summary).strip() if prev else summary
            set_ai_history_summary(user_id, merged[-3500:])

            # نصف جدیدتر تاریخچه را نگه می‌داریم.
            keep = max(2, HISTORY_ITEMS // 2)
            while len(history) > keep:
                history.popleft()
    except Exception as e:
        logger.warning("auto summarize failed: %s", e)
    finally:
        _SUMMARY_RUNNING.discard(user_id)

def _messages(user_id: int, prompt: str) -> List[dict]:
    system = SYSTEM_PROMPT
    mem = _memory_block(user_id)
    if mem:
        system = system + "\n\n" + mem
    messages = [{"role": "system", "content": system}]
    for role, content in _HISTORY[user_id]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})
    return messages

def _save_turn(user_id: int, prompt: str, answer: str) -> None:
    history = _HISTORY[user_id]
    history.append(("user", prompt))
    history.append(("assistant", answer))
    # خلاصه‌سازی در پس‌زمینه وقتی پر شد
    if len(history) >= HISTORY_ITEMS:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_maybe_summarize_history(user_id))
        except Exception:
            pass
