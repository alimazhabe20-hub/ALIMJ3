# Auto-split part 10: v71_due_jobs
async def v71_due_jobs(context):
    """Run due AI tasks exactly once per scheduler pass; delivery stays bounded."""
    try:
        from bot.services.v71_platform import due_ai_jobs, complete_ai_job
        from bot.services.ai_service import ask_ai
        rows=due_ai_jobs(50)
        for jid, uid, prompt, run_at, repeat in rows:
            try:
                answer, _provider = await ask_ai(uid, prompt)
                await context.bot.send_message(chat_id=uid, text=f"🤖 نتیجه وظیفه زمان‌بندی‌شده:\n\n{answer[:3800]}")
                complete_ai_job(jid, int(repeat or 0))
            except Exception as exc:
                logger.warning("V71 scheduled AI job %s failed: %s", jid, type(exc).__name__)
    except Exception as exc:
        logger.warning("V71 scheduled job runner failed: %s", type(exc).__name__)
