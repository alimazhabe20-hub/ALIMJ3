# Auto-split part 9: get_user_city
def get_user_city(user_id: int) -> str:
    user = get_user(user_id)
    return user[2] if user else "قم"
