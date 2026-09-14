def _cancel_previous_operation_if_menu_button(context, text: str) -> bool:
    """Cancel per-user transient state before routing a new menu button.

    This is intentionally limited to the current user's transient state; it
    never touches global/background workers belonging to other users.
    """
    if not _is_menu_button(text):
        return False

    data = context.user_data
    # Cancel an explicitly registered foreground task if a feature created one.
    for key in ("_active_task", "active_task", "operation_task", "_operation_task"):
        task = data.pop(key, None)
        if task is not None and hasattr(task, "cancel") and not task.done():
            task.cancel()

    # Clear all known conversation/input modes.  Feature handlers can then
    # process the button normally instead of seeing stale waiting_for data.
    for key in (
        "waiting_for", "ai_mode", "ai_voice_chat", "_ai_already_sent",
        "downloader_url", "downloader_mode", "pending_url", "pending_download",
        "pending_action", "pending_input", "pending_operation",
    ):
        data.pop(key, None)

    return True
