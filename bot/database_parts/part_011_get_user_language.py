# Auto-split part 11: get_user_language
def get_user_language(user_id: int) -> str:
    user = get_user(user_id)
    return user[4] if user else "fa"
