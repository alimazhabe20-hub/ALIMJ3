async def _handle_ai_continue(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    await _safe_answer(query, "در حال ادامه…")
    answer_id = data.split(":", 1)[1].strip()
    from bot.services.ai_extras import build_continue_prompt, store_answer, get_ai_result_keyboard
    from bot.services.ai_service import ask_ai
    cont_prompt = build_continue_prompt(user_id, answer_id)
    if not cont_prompt:
        await query.message.reply_text(
            "⚠️ پاسخ قبلی برای ادامه پیدا نشد. لطفاً سؤال را دوباره بپرسید.",
        )
        return
    try:
        notice = await query.message.reply_text("✍️ در حال ادامه پاسخ...")
        answer, provider = await ask_ai(user_id, cont_prompt)
        answer = (answer or "").strip()
        if not answer:
            await notice.edit_text("پاسخی برای ادامه دریافت نشد.")
            return
        # ذخیره با همان prompt اصلی اگر موجود باشد
        from bot.services.ai_extras import get_stored_prompt
        orig_prompt = get_stored_prompt(answer_id, user_id) or ""
        aid = store_answer(user_id, answer, prompt=orig_prompt)
        # ارسال تکه‌تکه
        def _split(txt, limit=3900):
            txt = (txt or "").strip()
            if not txt:
                return []
            if len(txt) <= limit:
                return [txt]
            parts, rest = [], txt
            while rest:
                if len(rest) <= limit:
                    parts.append(rest)
                    break
                cut = rest.rfind("\n", 0, limit)
                if cut < limit // 3:
                    cut = rest.rfind(" ", 0, limit)
                if cut < limit // 3:
                    cut = limit
                parts.append(rest[:cut].strip())
                rest = rest[cut:].strip()
            return [p for p in parts if p]

        chunks = _split("🤖 " + answer) or ["🤖 پاسخی دریافت نشد."]
        offer = len(answer) >= 1800
        # فقط دکمه ادامه؛ بدون کلید مدل/حافظه
        kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)
        try:
            await notice.delete()
        except Exception:
            pass
        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            kwargs = {"reply_markup": kb} if is_last and kb is not None else {}
            if i == 0:
                body = chunk
                if not body.startswith("🤖"):
                    body = "🤖 " + body
                await query.message.reply_text(body, **kwargs)
            else:
                body = chunk[2:].lstrip() if chunk.startswith("🤖 ") else chunk
                await query.message.reply_text(
                    f"🤖 ادامه ({i+1}/{len(chunks)})\n{body}", **kwargs
                )
    except Exception as e:
        logger.error("ai_continue failed: %s", e, exc_info=True)
        try:
            await query.message.reply_text(
                f"⚠️ ادامه پاسخ ممکن نشد: {str(e)[:200]}",
            )
        except Exception:
            pass
    return
