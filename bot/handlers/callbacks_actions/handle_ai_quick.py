"""Callback action: ai_quick.

Extracted from the legacy callback router while preserving its public behavior.
"""
from importlib import import_module

_CORE = import_module("bot.handlers.callbacks_core")

async def handle(update, context):
    # The old callback implementation exposes many helpers as module globals.
    # Mirror those globals here so the extracted action remains behavior-compatible.
    globals().update({k: v for k, v in vars(_CORE).items() if k != "button_handler"})
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data.startswith("ai_quick:"):
        kind = data.split(":", 1)[1]
        await _safe_answer(query)
        try:
            city = get_user_city(user_id) or "تهران"
            if kind == "weather":
                from bot.api.api_weather import get_weather, format_weather
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
