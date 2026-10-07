from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 1: media_ai_handler
async def media_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحلیل عکس و فایل در حالت دستیار هوشمند."""
    # Imported lazily to avoid a circular import with messages.py compatibility facade.
    from bot.handlers.messages import (
        _send_ai_answer, _send_ai_voice, _ask_ai_with_typing, _apply_voice_chat_flags,
    )
    if not update.message:
        return
    if not await check_and_rate_limit(update, context):
        return

    # فقط در حالت AI
    if not context.user_data.get("ai_mode"):
        return

    user_id = update.effective_user.id
    msg = update.message
    caption = (msg.caption or "").strip()
    prompt = caption or ""

    images: list[tuple[bytes, str]] = []
    file_text = None
    filename = ""

    try:
        # ویدیو کوتاه
        if msg.video or msg.video_note:
            notice = await msg.reply_text("🎬 در حال تحلیل ویدیو...")
            try:
                v = msg.video or msg.video_note
                tg_file = await v.get_file()
                data = bytes(await tg_file.download_as_bytearray())
                mime = getattr(msg.video, "mime_type", None) or "video/mp4"
                result = await analyze_video(data, prompt, mime=mime)
                await _send_ai_answer(update, user_id, result)
            except Exception as e:
                await msg.reply_text(f"⚠️ ویدیو: {e}", reply_markup=get_ai_keyboard(user_id))
            finally:
                try:
                    await notice.delete()
                except Exception:
                    pass
            return
        # عکس
        if msg.photo:
            photo = msg.photo[-1]  # بالاترین کیفیت
            tg_file = await photo.get_file()
            data = bytes(await tg_file.download_as_bytearray())
            images.append((data, "image/jpeg"))
        # فایل / سند
        elif msg.document:
            doc = msg.document
            filename = doc.file_name or "file"
            mime = doc.mime_type or ""
            # محدودیت حجم ۱۰ مگ
            if doc.file_size and doc.file_size > 10 * 1024 * 1024:
                await msg.reply_text("❌ حجم فایل بیشتر از ۱۰ مگابایت است.")
                return
            tg_file = await doc.get_file()
            data = bytes(await tg_file.download_as_bytearray())

            if mime.startswith("image/") or filename.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp", ".gif")
            ):
                images.append((data, mime or "image/jpeg"))
            else:
                try:
                    from bot.services.v72_platform import extract_document, store_document, document_context
                    rich_doc = extract_document(data, filename, mime)
                    store_document(user_id, rich_doc)
                    file_text = document_context(rich_doc)
                except ValueError as doc_exc:
                    logger.warning("V72 document extraction rejected: %s", doc_exc)
                    file_text = _extract_text_from_bytes(data, filename, mime)
                if not file_text.strip():
                    await msg.reply_text(
                        "❌ نتوانستم متن این فایل را بخوانم.\n"
                        "فرمت‌های پشتیبانی‌شده: txt, md, csv, json, pdf, docx و عکس."
                    )
                    return
        else:
            return

        # Visual Lens: مسیر کاملاً جدا از تحلیل قدیمی عکس.
        # فقط با درخواست صریح Lens/جستجوی تصویری فعال می‌شود.
        if images and prompt and looks_like_visual_search(prompt):
            notice = await msg.reply_text("🔎 در حال بررسی تصویر با Lens محلی...")
            try:
                result = await visual_search(images[0][0], caption=prompt)
                await msg.reply_text(
                    result[:4000],
                    reply_markup=get_ai_keyboard(user_id),
                )
            finally:
                try:
                    await notice.delete()
                except Exception:
                    pass
            return

        # ویرایش تصویر: عکس + دستور ویرایش
        if images and prompt and looks_like_image_edit(prompt):
            notice = await msg.reply_text("🎨 در حال ویرایش تصویر...")
            try:
                img_bytes, mime = await generate_or_edit_image(
                    prompt,
                    source_image=images[0][0],
                    source_mime=images[0][1],
                )
                from io import BytesIO
                bio = BytesIO(img_bytes)
                bio.name = "edited.png" if "png" in mime else "edited.jpg"
                await msg.reply_photo(
                    photo=bio,
                    caption="🎨 تصویر ویرایش شد",
                    reply_markup=get_ai_keyboard(user_id),
                )
            finally:
                try:
                    await notice.delete()
                except Exception:
                    pass
            return

        # خرید از روی عکس: همه‌چیز داخل همان دستیار هوشمند انجام می‌شود.
        # ابتدا Vision فقط یک عبارت جستجوی کوتاه و قابل‌استفاده می‌سازد؛ سپس موتور خرید واقعاً وب/فروشگاه‌ها را می‌گردد.
        shopping_image_intent = bool(
            images and prompt and re.search(
                r"خرید|قیمت|فروشگاه|فروشنده|لینک|پیدا.?کن|مشابه|ارزان|سرچ|جستجو|شاپ|buy|price|shop|find",
                prompt, re.I,
            )
        )
        if images and shopping_image_intent:
            notice = await msg.reply_text("🛒 در حال تشخیص محصول و جستجوی واقعی فروشگاه‌ها...")
            try:
                vision_prompt = (
                    "این عکس یک محصول است. فقط یک عبارت جستجوی کوتاه برای پیدا کردن همین محصول یا مشابه نزدیک آن بنویس. "
                    "برند، مدل، نوع محصول، رنگ، جنس، طرح و ویژگی‌های قابل‌تشخیص را وارد کن. "
                    "حداکثر 18 کلمه؛ بدون توضیح، بدون قیمت و بدون جمله اضافی."
                )
                search_query, _ = await ask_ai_media(
                    user_id, vision_prompt, images=images, file_text=file_text, filename=filename
                )
                search_query = re.sub(r"[\n\r]+", " ", (search_query or "")).strip()[:500]
                if not search_query:
                    search_query = prompt[:500]

                from bot.features.market.shopping import search_shopping
                shopping_result = await search_shopping(
                    query=search_query, source="all", max_results=10, user_id=user_id
                )
                # اگر موتور خرید هیچ لینک واقعی نداد، Lens وب را به‌عنوان fallback اجرا کن.
                if "🔗" not in shopping_result:
                    shopping_result = await visual_search(
                        images[0][0], caption=search_query, include_web=True
                    )
                await msg.reply_text(
                    "🛒 جستجوی خرید بر اساس عکس\n\n" + shopping_result[:7000],
                    reply_markup=get_ai_keyboard(user_id),
                )
            finally:
                try:
                    await notice.delete()
                except Exception:
                    pass
            return

        notice = await msg.reply_text("✍️ در حال تحلیل...")
        try:
            prompt = enhance_ocr_prompt(prompt, bool(images))
            answer, provider = await ask_ai_media(
                user_id,
                prompt,
                images=images or None,
                file_text=file_text,
                filename=filename,
            )
            await msg.reply_text(
                f"🤖 {answer}",
                reply_markup=get_ai_keyboard(user_id),
            )
        finally:
            try:
                await notice.delete()
            except Exception:
                pass
    except Exception as exc:
        await msg.reply_text(
            "❌ تحلیل ممکن نشد.\n\n" + str(exc)[:2500],
            reply_markup=get_ai_keyboard(user_id),
        )
