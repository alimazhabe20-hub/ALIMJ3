"""Shared imports and module state for the refactored messages."""

"""Ordered compatibility loader for cleaned source chunks."""

"""هندلر پیام‌ها — همه قابلیت‌ها"""

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import ContextTypes

from bot.database import (
    update_user_field, get_user_city, set_last_main_msg_id,
    add_reminder, track_usage,
    get_user_usage, set_birth_date, get_birth_date, get_user,
    get_azan_settings, set_azan_master, toggle_azan_prayer,
)

from bot.utils.helpers import (
    build_message, get_main_keyboard, get_refresh_button,
    get_country_keyboard, get_smart_settings_keyboard, get_iran_cities_keyboard, get_iraq_cities_keyboard,
    get_language_keyboard, get_more_keyboard, get_date_tools_keyboard,
    get_religious_keyboard, get_market_keyboard, get_weather_geo_keyboard,
    get_tools_keyboard, get_fun_keyboard, get_profile_keyboard, get_joke_keyboard,
    get_calendar_text, get_calendar_buttons, ALL_CITIES, CITY_COUNTRY,
    get_azan_keyboard, get_ai_keyboard, get_ai_model_keyboard,
)

from bot.api.calendar import get_today_tehran

from bot.handlers.middleware import check_and_rate_limit

from bot.handlers.feature_handlers import (
    _h_date_convert, _h_age_calc, _h_birthday, _h_zodiac, _h_lunar,
    _h_date_diff, _h_age_diff, _h_event_search, _h_countdown, _h_calc,
    _h_profit, _h_currency, _h_crypto_full, _h_crypto_pos, _h_crypto_chart,
    _h_crypto_analyze, _h_economic_calendar, _h_distance, _h_birth_save, _h_count_text,
    _h_font_text, _h_font_all, _h_reminder_manager, _h_reminder_input,
)

from bot.utils.motivation import get_motivation

from bot.features.date.features_date_date_tools import (
    parse_shamsi, parse_any_date, parse_two_dates, parse_countdown,
    birthday_countdown, zodiac_animal, lunar_age, date_diff, age_diff,
    convert_with_weekday, month_calendar, search_events, nowruz_countdown,
    world_clock, custom_countdown,
)

from bot.features.date.features_date_converters import calculate_age, parse_birth_datetime

from bot.features.religious import (
    qibla_direction, daily_adhkar, daily_verse_hadith,
    religious_countdown, religious_month_view, istikhara, istikhara_intro,
)

from bot.features.market.finance import full_market_prices, convert_currency, profit_loss, parse_profit, get_top_crypto, convert_crypto, get_crypto_chart, get_gold_chart, analyze_crypto, analyze_gold, parse_currency_input, get_crypto_analysis_keyboard, trading_recommendation, derivatives_radar, risk_scenarios, position_size_guide, calc_position_size, entry_alert_text, register_price_alert

from bot.features.tools.features_tools_app_tools import calculator, generate_password, count_text, world_distance

from bot.features.fun.features_fun_fun_tools import hafez_fal, joke_of_day, fact_of_day, daily_challenge, random_joke, get_joke_categories

from bot.features.weather.features_weather_weather_extra import weather_forecast, air_quality

from bot.features.fonts import apply_font, list_fonts, get_font_preview, apply_all_fonts

from bot.features.profile import profile_text

from bot.utils.helpers import get_font_keyboard, get_font_en_keyboard, get_font_fa_keyboard

from bot.features.fonts.styles import FONT_NAMES

from bot.features.fonts.converter import EN_STYLES, FA_STYLES

import re

import time

import asyncio

from datetime import datetime, timedelta

import pytz

from bot.config import config

from bot.logger import logger

from bot.services.ai_extras import (
    store_answer, get_last_answer, get_ai_result_keyboard, parse_chart_request, make_chart_image,
    web_search, parse_natural_reminder, enhance_ocr_prompt,
    get_last_answer_id, build_continue_prompt,
)

from bot.services.visual_search import visual_search, looks_like_visual_search

from bot.services.ai_service import (
    ask_ai, ask_ai_media, clear_history, enabled_providers,
    _extract_text_from_bytes, generate_or_edit_image,
    looks_like_image_request, looks_like_image_edit,
    text_to_speech, wants_voice_reply, strip_voice_prefix, speech_to_text,
    analyze_voice_emotion, wants_emotion_analysis, should_auto_voice_reply,
    wants_voice_chat_mode, wants_end_voice_chat, is_voice_only_request,
    generate_music, analyze_video, translate_voice,
)

from bot.handlers.feature_handlers import (
    _h_date_convert, _h_age_calc, _h_birthday, _h_zodiac, _h_lunar,
    _h_date_diff, _h_age_diff, _h_event_search, _h_countdown, _h_calc,
    _h_profit, _h_currency, _h_crypto_full, _h_crypto_pos, _h_crypto_chart,
    _h_crypto_analyze, _h_distance, _h_birth_save, _h_count_text,
    _h_font_text, _h_font_all,
)
