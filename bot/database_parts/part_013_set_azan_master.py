# Auto-split part 13: set_azan_master
def set_azan_master(user_id, enabled: bool):
    """روشن/خاموش کردن کل اعلان اذان"""
    update_user_field(user_id, "notification_enabled", 1 if enabled else 0)
