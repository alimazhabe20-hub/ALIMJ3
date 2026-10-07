# Auto-split part 4: get_calendar_buttons
def get_calendar_buttons(year, month, day, user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️ روز قبل", callback_data=f"day_{year}_{month}_{day-1}"),
            InlineKeyboardButton("📅 امروز", callback_data="calendar_today"),
            InlineKeyboardButton("روز بعد ▶️", callback_data=f"day_{year}_{month}_{day+1}"),
        ],
        [
            InlineKeyboardButton("◀️ ماه قبل", callback_data=f"cal_{year}_{month-1}_{day}"),
            InlineKeyboardButton("ماه بعد ▶️", callback_data=f"cal_{year}_{month+1}_{day}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")],
    ])
