from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def v73_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-safe local QA snapshot; no secrets or network probes are returned."""
    from bot.services.v73_platform import qa_snapshot, health_snapshot, performance_snapshot

    q = qa_snapshot(".")
    text = (
        "🛡 V73 Production QA\n\n"
        f"Syntax: {'OK' if q['syntax_ok'] else 'FAIL'}\n"
        f"Python files: {q['python_files']}\n"
        f"Security: {q['security']}\n"
        f"Agent limits: {q['agent_limits']['steps']} steps / {q['agent_limits']['calls']} calls / {q['agent_limits']['repairs']} repairs\n"
        f"Health components: {len(health_snapshot())}\n"
        f"Performance components: {len(performance_snapshot())}"
    )
    if not q["syntax_ok"]:
        text += "\n⚠️ چند خطای نحوی در QA پیدا شد؛ جزئیات داخلی نمایش داده نمی‌شود."
    await update.effective_message.reply_text(text)
