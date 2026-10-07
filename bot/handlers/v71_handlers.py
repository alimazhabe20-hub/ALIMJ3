from __future__ import annotations
import asyncio, re, secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.logger import logger
from bot.services.downloader import is_url, extract_url, probe, download, cleanup, user_message
from bot.services.v71_platform import (
    SUPPORTED_LANGS, detect_language, personalize, self_test, set_workspace,
    get_workspace, save_branch, list_branches, schedule_ai,
)
from bot.services.v72_platform import format_options, record_download, update_download, normalize_download_mode, ux_text

# ===== merged from bot/handlers/v71_handlers_parts/part_001__dl_lang.py =====
# Auto-split part 1: _dl_lang
def _dl_lang(update):
    try:
        from bot.database import get_user_language
        lang = get_user_language(update.effective_user.id) if update.effective_user else "fa"
        return lang if lang in {"fa", "en", "ar"} else "fa"
    except Exception:
        return "fa"

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_002_downloader_entry_v71.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 2: downloader_entry_v71
async def downloader_entry_v71(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args or []).strip() if getattr(context, "args", None) else ""
    url = extract_url(args) if args else None
    if url:
        await _start_probe(update, context, url)
        return
    context.user_data["waiting_for"] = "downloader_url_v71"
    from bot.services.v72_platform import ux_text
    lang = _dl_lang(update)
    await update.message.reply_text(ux_text(lang, "download_title") + "\n\n" + ux_text(lang, "intro"))

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_003__start_probe.py =====
# Auto-split part 3: _start_probe
async def _start_probe(update, context, url: str):
    url = extract_url(url) or ""
    if not url:
        await update.message.reply_text(ux_text(_dl_lang(update), "invalid"))
        return
    from bot.services.v72_platform import ux_text
    lang = _dl_lang(update)
    notice = await update.message.reply_text(ux_text(lang, "checking"))
    try:
        info = await probe(url)
        token = secrets.token_urlsafe(9)
        context.user_data[f"dl:{token}"] = {"url": url, "info": info}
        title = str(info.get("title") or "فایل")[:100]
        labels = {
            "fa": {"best":"🎬 بهترین کیفیت","1080p":"📺 تا 1080p","720p":"📺 تا 720p","480p":"📺 تا 480p","audio":"🎵 فقط صدا (MP3)","direct":"📦 دریافت مستقیم","cancel":"❌ لغو"},
            "en": {"best":"🎬 Best quality","1080p":"📺 Up to 1080p","720p":"📺 Up to 720p","480p":"📺 Up to 480p","audio":"🎵 Audio only (MP3)","direct":"📦 Direct download","cancel":"❌ Cancel"},
            "ar": {"best":"🎬 أفضل جودة","1080p":"📺 حتى 1080p","720p":"📺 حتى 720p","480p":"📺 حتى 480p","audio":"🎵 صوت فقط (MP3)","direct":"📦 تنزيل مباشر","cancel":"❌ إلغاء"},
        }[lang]
        rows = [
            [InlineKeyboardButton(labels["best"], callback_data=f"dl:q:{token}:best"), InlineKeyboardButton(labels["1080p"], callback_data=f"dl:q:{token}:1080p")],
            [InlineKeyboardButton(labels["720p"], callback_data=f"dl:q:{token}:720p"), InlineKeyboardButton(labels["480p"], callback_data=f"dl:q:{token}:480p")],
            [InlineKeyboardButton(labels["audio"], callback_data=f"dl:q:{token}:audio")],
            [InlineKeyboardButton(labels["cancel"], callback_data=f"dl:cancel:{token}")],
        ]
        if not info.get("supported"):
            rows = [[InlineKeyboardButton(labels["direct"], callback_data=f"dl:q:{token}:best")],[InlineKeyboardButton(labels["cancel"], callback_data=f"dl:cancel:{token}")]]
        await notice.edit_text(f"{ux_text(lang, 'prepared')}\n\n📄 {title}\n\n{ux_text(lang, 'choose')}", reply_markup=InlineKeyboardMarkup(rows))
    except Exception:
        logger.exception("downloader probe failed")
        await notice.edit_text(ux_text(lang, "probe_failed"))
    finally:
        context.user_data.pop("waiting_for", None)

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_004_handle_downloader_url_v71.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 4: handle_downloader_url_v71
async def handle_downloader_url_v71(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    waiting = context.user_data.get("waiting_for")
    if waiting != "downloader_url_v71":
        return False
    url = extract_url(text)
    if not url:
        # Do not consume ReplyKeyboard buttons while waiting for a downloader URL.
        # Buttons such as "🔙 بازگشت" are routed by the normal menu handler;
        # they are not downloader input and must never trigger the invalid-URL message.
        stripped = (text or "").strip()
        if (
            "بازگشت" in stripped
            or stripped.startswith(("📥", "🔙", "🏠", "📊", "🥇", "🗓", "🧠", "⚙️", "🔔", "💾", "🌐", "📚", "🛠", "⬅️", "➡️"))
        ):
            context.user_data.pop("waiting_for", None)
            return False
        await update.message.reply_text(ux_text(_dl_lang(update), "invalid"))
        return True
    context.user_data.pop("waiting_for", None)

    # Instagram / social: same UX as insta-downloader-bot — download immediately
    try:
        from bot.services.insta_downloader import is_social_url
    except Exception:
        is_social_url = lambda _u: False  # type: ignore

    if is_social_url(text):
        await _download_social_direct(update, context, url)
        return True

    await _start_probe(update, context, url)
    return True

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_005__download_social_direct.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 5: _download_social_direct
async def _download_social_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    """Mirror insta-downloader-bot handle_link: download then reply_video/document."""
    from bot.services.insta_downloader import download as insta_download, is_video_path, cleanup_path
    from bot.services.downloader import MAX_BYTES, user_message

    notice = await update.message.reply_text("⏳ در حال دانلود...")
    path = None
    try:
        path = await insta_download(url)
        size = 0
        try:
            from pathlib import Path as _P
            size = _P(path).stat().st_size
        except Exception:
            size = 0
        if size > MAX_BYTES:
            await notice.edit_text(user_message("too_large"))
            return

        try:
            await notice.edit_text("📤 در حال ارسال...")
        except Exception as exc:
            logger.debug("non-fatal exception: %s", exc)

        from bot.services.telegram_upload import send_media
        await send_media(update.message, path, title=__import__("pathlib").Path(path).name)
        try:
            await notice.delete()
        except Exception as exc:
            logger.debug("non-fatal exception: %s", exc)
    except Exception as exc:
        logger.exception("social direct download failed: %s", exc)
        err = str(exc)
        if err in {"telegram_standard_api_limit", "telegram_upload_too_large"}:
            from bot.services.telegram_upload import upload_error_message
            try:
                await notice.edit_text(upload_error_message(err))
            except Exception:
                await update.message.reply_text(upload_error_message(err))
            return
        low = err.lower()
        if "gallery-dl" in low and ("نصب" in err or "not found" in low or "no such file" in low):
            code = "gallery_dl_missing"
        elif any(x in low for x in ("login", "captcha", "403", "401", "private", "cookie")):
            code = "site_blocked"
        elif "too large" in low or "max-filesize" in low:
            code = "too_large"
        else:
            code = "failed"
        try:
            await notice.edit_text(user_message(code))
        except Exception:
            await update.message.reply_text(user_message(code))
    finally:
        cleanup_path(path)

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_006_download_callback.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 6: download_callback
async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    q = update.callback_query
    if data.startswith("dl:cancel:"):
        token=data.split(":",2)[2]; context.user_data.pop(f"dl:{token}",None)
        await q.answer(ux_text(_dl_lang(update), "cancelled"))
        try: await q.edit_message_text(ux_text(_dl_lang(update), "cancelled"))
        except Exception: pass
        return True
    m=re.fullmatch(r"dl:q:([^:]+):(best|1080p|720p|480p|audio)",data or "")
    if not m: return False
    token,mode=m.groups(); payload=context.user_data.pop(f"dl:{token}",None)
    await q.answer(ux_text(_dl_lang(update), "downloading"))
    if not payload:
        try: await q.edit_message_text(ux_text(_dl_lang(update), "expired"))
        except Exception: pass
        return True
    url=str((payload.get("info") or {}).get("url") or payload["url"]); notice=None; result=None; job_id=None
    try:
        notice=await q.edit_message_text(ux_text(_dl_lang(update), "downloading"))
        job_id=record_download(update.effective_user.id, url, mode)
        last=[0.0]
        async def progress(p):
            now=asyncio.get_running_loop().time()
            if now-last[0] < 2: return
            last[0]=now
            done=int(p.get("downloaded") or 0); total=int(p.get("total") or 0)
            if job_id: update_download(job_id, progress=(done * 100 / total) if total else 0, status="downloading")
            txt=f"⏬ دانلود… {done/1024/1024:.1f}MB"
            if total: txt += f" / {total/1024/1024:.1f}MB"
            try: await notice.edit_text(txt)
            except Exception: pass
        loop=asyncio.get_running_loop()
        def progress_thread(p):
            asyncio.run_coroutine_threadsafe(progress(p), loop)
        result=await download(url,mode=normalize_download_mode(mode),user_id=update.effective_user.id,progress_cb=progress_thread,preflight=False)
        if job_id: update_download(job_id, status="completed", progress=100)
        if notice:
            try: await notice.edit_text(f"{ux_text(_dl_lang(update), 'ready')}\n📄 {result['title']}\n📦 {result['size']/1024/1024:.1f}MB\n\n{ux_text(_dl_lang(update), 'sending')}")
            except Exception: pass
        from bot.services.telegram_upload import send_media
        await send_media(q.message, result["path"], title=result["title"])
        return True
    except Exception as exc:
        code=str(exc)
        if code in {"telegram_standard_api_limit", "telegram_upload_too_large"}:
            from bot.services.telegram_upload import upload_error_message
            message = upload_error_message(code)
            if job_id: update_download(job_id, status="failed", error_code=code)
            logger.warning("telegram upload rejected: %s", code)
            await q.message.reply_text(message)
            return True
        if code not in {"invalid_url","blocked_host","dns_error","rate_limited","site_blocked","access_restricted","unsupported","too_large","yt_dlp_missing","failed"}: code="failed"
        if job_id: update_download(job_id, status="failed", error_code=code)
        logger.warning("downloader callback failed: %s",code)
        await q.message.reply_text(user_message(code))
        return True
    finally:
        cleanup(result.get("path") if result else None)
        if notice:
            try: await notice.delete()
            except Exception: pass

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_007_v71_command.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 7: v71_command
async def v71_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 V71 Production Hardening فعال است.\n\nDownloader 2.0، امنیت، cache، صف دانلود، شخصی‌سازی، Workspace، شاخه مکالمه، وظایف AI زمان‌بندی‌شده، اعلان هوشمند، observability و self-test فعال هستند.\n\n⚠️ خلاصه‌سازی خودکار گفتگوهای طولانی در این نسخه اضافه نشده است.")

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_008_v71_selftest_command.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 8: v71_selftest_command
async def v71_selftest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result=self_test(); await update.message.reply_text("🧪 Self-Test\n"+str(result))

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_009_workspace_command.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 9: workspace_command
async def workspace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    if not args or "=" not in args:
        await update.message.reply_text("📁 فرمت: /workspace نام=داده")
        return
    name,data=args.split("=",1); set_workspace(update.effective_user.id,name.strip(),data.strip()); await update.message.reply_text("✅ Workspace ذخیره شد.")

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_010_branch_command.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 10: branch_command
async def branch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip(); uid=update.effective_user.id
    if not args:
        rows=list_branches(uid); await update.message.reply_text("🌿 شاخه‌ها:\n"+("\n".join("• "+x for x in rows) if rows else "خالی است.")); return
    if "=" not in args:
        await update.message.reply_text("🌿 فرمت: /branch نام=زمینه")
        return
    name,data=args.split("=",1); save_branch(uid,name.strip(),data.strip()); await update.message.reply_text("✅ شاخه ذخیره شد.")

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_011_schedule_ai_command.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 11: schedule_ai_command
async def schedule_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    m=re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s+(\d+))?\s+(.+)$",args)
    if not m:
        await update.message.reply_text("⏰ فرمت: /scheduleai 2026-09-14 09:00 60 متن وظیفه\nعدد 60 یعنی تکرار هر 60 دقیقه؛ حذفش کنید برای یک‌بار.")
        return
    run_at,repeat,prompt=m.groups(); jid=schedule_ai(update.effective_user.id,prompt,run_at,int(repeat or 0)); await update.message.reply_text(f"✅ وظیفه AI ثبت شد. شناسه: {jid}")

# ===== end merged part =====

# ===== merged from bot/handlers/v71_handlers_parts/part_012_personalize_command.py =====
from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 12: personalize_command
async def personalize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    if not args:
        await update.message.reply_text("⚙️ فرمت: /personalize fa|en|ar [short|balanced|long] [fast|balanced|quality]")
        return
    parts=args.split()
    lang=parts[0].lower() if parts else None
    style=parts[1].lower() if len(parts)>1 else None
    mode=parts[2].lower() if len(parts)>2 else None
    if lang not in SUPPORTED_LANGS:
        await update.message.reply_text("❌ زبان فقط fa / en / ar است."); return
    if style and style not in {"short","balanced","long"}:
        await update.message.reply_text("❌ سبک پاسخ: short / balanced / long"); return
    if mode and mode not in {"fast","balanced","quality"}:
        await update.message.reply_text("❌ حالت AI: fast / balanced / quality"); return
    current=personalize(update.effective_user.id,lang,style,mode,None)
    await update.message.reply_text(f"✅ شخصی‌سازی ذخیره شد.\n🌍 {current['language']}\n✍️ {current['response_style']}\n🤖 {current['ai_mode']}")

# ===== end merged part =====
