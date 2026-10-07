# Auto-split part 1: _db
def _db():
    from bot.database import get_db_connection
    return get_db_connection()
