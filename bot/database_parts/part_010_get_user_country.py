# Auto-split part 10: get_user_country
def get_user_country(user_id: int) -> str:
    user = get_user(user_id)
    return user[3] if user else "Iran"
