# Auto-split part 17: set_last_main_msg_id
def set_last_main_msg_id(user_id, message_id):
    try:
        _execute_write("UPDATE users SET last_main_msg_id = ? WHERE user_id = ?", (message_id, user_id))
    except Exception as e:
        logger.error(f"set_last_main_msg_id failed: {e}")
