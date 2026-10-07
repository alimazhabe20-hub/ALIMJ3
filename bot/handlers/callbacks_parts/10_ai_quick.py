async def _handle_ai_quick(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    kind = data.split(":", 1)[1]
    await _safe_answer(query)
    try:
        city = get_user_city(user_id) or "تهران"
        if kind == "weather":
            from bot.api.weather import get_weather, format_weather
            w = get_weather(city)
            txt = format_weather(city, w)
        elif kind == "price":
            from bot.features.market.finance import full_market_prices
            txt = await full_market_prices()
        elif kind == "istikhara":
            from bot.features.religious.istikhara import istikhara
            txt = await istikhara(user_id)
        elif kind == "prayer":
            from bot.api.prayer import get_prayer_times
            pt = get_prayer_times(city)
            if pt:
                txt = f"🕌 اوقات شرعی {city}:\n" + "\n".join(f"{k}: {v}" for k, v in pt.items())
            else:
                txt = "اوقات شرعی در دسترس نیست."
        else:
            txt = "دکمه نامعتبر."
        await query.message.reply_text(txt)
    except Exception as e:
        await query.message.reply_text(f"⚠️ {e}")
    return
