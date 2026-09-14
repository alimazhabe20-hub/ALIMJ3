# Auto-split part 7: joke_of_day
async def joke_of_day(category: str = None, user_id: int = None) -> str:
    return random_joke(category, user_id=user_id)
