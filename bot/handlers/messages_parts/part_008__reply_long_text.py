async def _reply_long_text(msg, text: str, *, prefix: str = "🤖 ", reply_markup=None):
    """ارسال پاسخ کامل؛ اگر بلند بود ادامه در پیام‌های بعدی. کیبورد فقط روی آخرین تکه."""
    body = (text or "").strip()
    chunks = _split_telegram_text(prefix + body, 3900)
    if not chunks:
        chunks = [prefix + "پاسخی دریافت نشد."]
    first = None
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        is_last = i == total - 1
        kwargs = {}
        if is_last and reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        if i == 0:
            first = await msg.reply_text(chunk, **kwargs)
        else:
            body_chunk = chunk
            if body_chunk.startswith("🤖 "):
                body_chunk = body_chunk[2:].lstrip()
            await msg.reply_text(f"🤖 ادامه ({i+1}/{total})\n{body_chunk}", **kwargs)
    return first
