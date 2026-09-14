# Auto-split part 8: fact_of_day
async def fact_of_day() -> str:
    return f"🧠 **دانستنی**\n\n{random.choice(FACTS)}"
