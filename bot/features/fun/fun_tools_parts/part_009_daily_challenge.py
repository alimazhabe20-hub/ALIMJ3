# Auto-split part 9: daily_challenge
async def daily_challenge() -> str:
    return (
        f"💪 **چالش امروز**\n\n"
        f"{random.choice(CHALLENGES)}\n\n"
        f"✅ وقتی انجام دادی به خودت امتیاز بده!"
    )
