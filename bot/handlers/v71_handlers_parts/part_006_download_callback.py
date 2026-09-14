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
        from pathlib import Path
        media_path = Path(result["path"])
        video_exts = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}
        audio_exts = {".mp3", ".m4a", ".aac", ".ogg", ".wav", ".opus"}
        with media_path.open("rb") as fh:
            if media_path.suffix.lower() in video_exts:
                await q.message.reply_video(
                    video=fh,
                    caption="📥 دانلودر فایل • روز زیبا",
                    supports_streaming=True,
                    filename=result["title"][:120],
                )
            elif media_path.suffix.lower() in audio_exts:
                await q.message.reply_audio(
                    audio=fh,
                    caption="📥 دانلودر فایل • روز زیبا",
                    filename=result["title"][:120],
                )
            else:
                await q.message.reply_document(
                    document=fh,
                    filename=result["title"][:120],
                    caption="📥 دانلودر فایل • روز زیبا",
                )
        return True
    except Exception as exc:
        code=str(exc)
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
