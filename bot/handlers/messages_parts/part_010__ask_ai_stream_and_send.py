async def _ask_ai_stream_and_send(update, context, user_id: int, text: str):
    """استریم AI و ویرایش تدریجی پیام؛ در پایان همه تکه‌ها ارسال و دکمه ادامه اضافه می‌شود."""
    import asyncio
    from bot.services.ai_service import ask_ai_stream
    msg = update.message
    sent = await msg.reply_text("✍️ در حال نوشتن...")
    buf = []
    provider_label = ""
    try:
        last_edit = time.monotonic()
        last_len = 0
        last_rendered = "✍️ در حال نوشتن..."
        async for piece, label in ask_ai_stream(user_id, text):
            if label:
                provider_label = label
                continue
            if piece:
                buf.append(piece)
                current = "".join(buf)
                now = time.monotonic()
                if now - last_edit >= 0.8 and len(current) - last_len >= 80:
                    preview = "🤖 " + current
                    if len(preview) > 4000:
                        preview = preview[:3990] + "…"
                    if preview != last_rendered:
                        try:
                            await sent.edit_text(preview)
                            last_rendered = preview
                            last_edit, last_len = now, len(current)
                        except Exception as edit_error:
                            logger.debug("AI stream edit skipped: %s", edit_error)
                    else:
                        last_edit, last_len = now, len(current)
        answer = "".join(buf).strip()
        if not answer:
            raise RuntimeError("جواب خالی")
        aid = store_answer(user_id, answer, prompt=text)
        chunks = _split_telegram_text("🤖 " + answer, 3900)
        if not chunks:
            chunks = ["🤖 پاسخی دریافت نشد."]
        offer = _looks_truncated(answer) or len(answer) >= 1800
        # فقط دکمه ادامه؛ بدون کلید مدل/حافظه زیر پاسخ
        kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)

        # پیام اول: ویرایش همان «در حال نوشتن»
        first = chunks[0]
        total = len(chunks)
        edit_kwargs = {}
        if total == 1 and kb is not None:
            edit_kwargs["reply_markup"] = kb
        if first != last_rendered:
            try:
                await sent.edit_text(first, **edit_kwargs)
                last_rendered = first
            except Exception as edit_error:
                logger.warning("AI final edit failed; retrying same message: %s", edit_error)
                try:
                    await asyncio.sleep(0.15)
                    await sent.edit_text(first, **edit_kwargs)
                    last_rendered = first
                except Exception as retry_error:
                    logger.warning("AI final edit retry failed: %s", retry_error)
                    try:
                        await msg.reply_text(first, **edit_kwargs)
                    except Exception:
                        pass
        elif total == 1 and kb is not None:
            try:
                await sent.edit_text(first, reply_markup=kb)
            except Exception:
                pass

        # ادامه‌ها در پیام‌های بعدی تا هیچ بخشی حذف نشود
        for i, chunk in enumerate(chunks[1:], start=2):
            try:
                body = chunk
                if body.startswith("🤖 "):
                    body = body[2:].lstrip()
                kwargs = {}
                if i == total and kb is not None:
                    kwargs["reply_markup"] = kb
                await msg.reply_text(f"🤖 ادامه ({i}/{total})\n{body}", **kwargs)
            except Exception as cont_err:
                logger.warning("AI continuation send failed: %s", cont_err)
        return answer, provider_label or "ai"
    except Exception:
        try:
            await sent.delete()
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
        raise
