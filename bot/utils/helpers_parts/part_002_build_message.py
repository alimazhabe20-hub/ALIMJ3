# Auto-split part 2: build_message
async def build_message(user_id, user_name, city):
    """ساخت پیام اصلی — کاملاً مقاوم؛ هیچ خطایی بیرون نمی‌رود."""
    import asyncio

    try:
        return await _build_message_inner(user_id, user_name, city)
    except Exception as e:
        try:
            from bot.logger import logger
            logger.error("build_message fatal: %s", e, exc_info=True)
        except Exception:
            pass
        name = str(user_name or "کاربر")
        return (
            f"🌟 سلام {name} عزیز!\n\n"
            f"⚠️ بارگذاری اطلاعات موقتاً ممکن نیست.\n"
            f"کد: {type(e).__name__}\n"
            f"/start را دوباره بفرستید."
        )
