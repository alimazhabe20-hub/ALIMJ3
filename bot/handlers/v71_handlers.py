from __future__ import annotations
import asyncio, re, secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.logger import logger
from bot.services.downloader import is_url, probe, download, cleanup, user_message
from bot.services.v71_platform import (
    SUPPORTED_LANGS, detect_language, personalize, self_test, set_workspace,
    get_workspace, save_branch, list_branches, schedule_ai,
)
from bot.services.v72_platform import format_options, record_download, update_download, normalize_download_mode, ux_text

def _dl_lang(update):
    try:
        from bot.database import get_user_language
        lang = get_user_language(update.effective_user.id) if update.effective_user else "fa"
        return lang if lang in {"fa", "en", "ar"} else "fa"
    except Exception:
        return "fa"


async def downloader_entry_v71(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args or []).strip() if getattr(context, "args", None) else ""
    if args and is_url(args):
        await _start_probe(update, context, args)
        return
    context.user_data["waiting_for"] = "downloader_url_v71"
    from bot.services.v72_platform import ux_text
    lang = _dl_lang(update)
    await update.message.reply_text(ux_text(lang, "download_title") + "\n\n" + ux_text(lang, "intro"))

async def _start_probe(update, context, url: str):
    if not is_url(url):
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

async def handle_downloader_url_v71(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    waiting = context.user_data.get("waiting_for")
    if waiting != "downloader_url_v71":
        return False
    if not is_url(text):
        await update.message.reply_text(ux_text(_dl_lang(update), "invalid"))
        return True
    context.user_data.pop("waiting_for", None)
    await _start_probe(update, context, text)
    return True

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
    url=payload["url"]; notice=None; result=None; job_id=None
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
        result=await download(url,mode=normalize_download_mode(mode),user_id=update.effective_user.id,progress_cb=progress_thread)
        if job_id: update_download(job_id, status="completed", progress=100)
        if notice:
            try: await notice.edit_text(f"{ux_text(_dl_lang(update), 'ready')}\n📄 {result['title']}\n📦 {result['size']/1024/1024:.1f}MB\n\n{ux_text(_dl_lang(update), 'sending')}")
            except Exception: pass
        with open(result["path"],"rb") as fh:
            await q.message.reply_document(document=fh, filename=result["title"][:120], caption="📥 دانلودر فایل • روز زیبا")
        return True
    except Exception as exc:
        code=str(exc)
        if code not in {"invalid_url","blocked_host","dns_error","rate_limited","site_blocked","access_restricted","unsupported","too_large","yt_dlp_missing","gallery_dl_missing","failed"}: code="failed"
        if job_id: update_download(job_id, status="failed", error_code=code)
        logger.warning("downloader callback failed: %s",code)
        await q.message.reply_text(user_message(code))
        return True
    finally:
        cleanup(result.get("path") if result else None)
        if notice:
            try: await notice.delete()
            except Exception: pass

async def v71_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 V71 Production Hardening فعال است.\n\nDownloader 2.0، امنیت، cache، صف دانلود، شخصی‌سازی، Workspace، شاخه مکالمه، وظایف AI زمان‌بندی‌شده، اعلان هوشمند، observability و self-test فعال هستند.\n\n⚠️ خلاصه‌سازی خودکار گفتگوهای طولانی در این نسخه اضافه نشده است.")

async def v71_selftest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result=self_test(); await update.message.reply_text("🧪 Self-Test\n"+str(result))

async def workspace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    if not args or "=" not in args:
        await update.message.reply_text("📁 فرمت: /workspace نام=داده")
        return
    name,data=args.split("=",1); set_workspace(update.effective_user.id,name.strip(),data.strip()); await update.message.reply_text("✅ Workspace ذخیره شد.")

async def branch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip(); uid=update.effective_user.id
    if not args:
        rows=list_branches(uid); await update.message.reply_text("🌿 شاخه‌ها:\n"+("\n".join("• "+x for x in rows) if rows else "خالی است.")); return
    if "=" not in args:
        await update.message.reply_text("🌿 فرمت: /branch نام=زمینه")
        return
    name,data=args.split("=",1); save_branch(uid,name.strip(),data.strip()); await update.message.reply_text("✅ شاخه ذخیره شد.")

async def schedule_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    m=re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s+(\d+))?\s+(.+)$",args)
    if not m:
        await update.message.reply_text("⏰ فرمت: /scheduleai 2026-09-14 09:00 60 متن وظیفه\nعدد 60 یعنی تکرار هر 60 دقیقه؛ حذفش کنید برای یک‌بار.")
        return
    run_at,repeat,prompt=m.groups(); jid=schedule_ai(update.effective_user.id,prompt,run_at,int(repeat or 0)); await update.message.reply_text(f"✅ وظیفه AI ثبت شد. شناسه: {jid}")

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
