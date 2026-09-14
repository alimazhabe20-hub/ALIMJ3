# Auto-split part 9: v70_due_jobs
async def v70_due_jobs(app):
    try:
        from bot.services.v70_platform import due_jobs, mark_job
        for jid, uid, prompt, run_at, repeat in due_jobs():
            try:
                await app.bot.send_message(uid, f"🤖 وظیفه زمان‌بندی‌شده:\n{prompt[:3800]}")
                mark_job(jid, repeat)
            except Exception as exc:
                logger.warning("V70 scheduled job %s failed: %s", jid, type(exc).__name__)
    except Exception as exc:
        logger.warning("V70 job runner failed: %s", type(exc).__name__)
