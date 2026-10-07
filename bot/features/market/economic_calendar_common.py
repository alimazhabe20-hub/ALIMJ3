"""Shared imports and module state for the refactored economic_calendar."""

from __future__ import annotations

"""Ordered compatibility loader for cleaned source chunks."""

"""تقویم اقتصادی زنده برای بخش بازار.

منبع پیش‌فرض: خروجی هفتگی عمومی Forex Factory/faireconomy.media.
دریافت عمداً کم‌دفعات انجام می‌شود تا به محدودیت منبع احترام گذاشته شود.
"""

import asyncio

import hashlib

import html

import re

import time

from datetime import datetime, timedelta, timezone

from typing import Any

import pytz

import requests

from bs4 import BeautifulSoup

from bot.config import config

from bot.logger import logger

FF_URLS = (
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
)

FF_FALLBACK_URLS = (
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://cdn-nfs.faireconomy.media/ff_calendar_nextweek.json",
)

CACHE_TTL = 5 * 60

MAJOR_CURRENCIES = ("USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF")

_MAX_EVENTS = 600

_cache: list[dict[str, Any]] = []

_cache_expires = 0.0

_cache_fetched_at = 0.0

_cache_lock: asyncio.Lock | None = None

CURRENCY_NAMES = {
    "USD": "دلار آمریکا", "EUR": "یورو", "GBP": "پوند انگلیس", "JPY": "ین ژاپن",
    "CHF": "فرانک سوئیس", "CAD": "دلار کانادا", "AUD": "دلار استرالیا",
    "NZD": "دلار نیوزیلند", "CNY": "یوان چین", "NOK": "کرون نروژ",
    "SEK": "کرون سوئد", "HKD": "دلار هنگ‌کنگ", "SGD": "دلار سنگاپور",
    "MXN": "پزوی مکزیک", "INR": "روپیه هند", "TRY": "لیر ترکیه", "ZAR": "رند آفریقای جنوبی",
}

IMPACT_FA = {"High": "زیاد", "Medium": "متوسط", "Low": "کم", "Holiday": "تعطیلی", "": "نامشخص"}

IMPACT_ICON = {"High": "🔴", "Medium": "🟠", "Low": "🟡", "Holiday": "⚪"}

TITLE_MAP = {
    "Non-Farm Employment Change": "تغییر اشتغال غیرکشاورزی",
    "Non-Farm Payrolls": "اشتغال غیرکشاورزی",
    "Unemployment Rate": "نرخ بیکاری",
    "Unemployment Claims": "درخواست‌های بیمه بیکاری",
    "Initial Jobless Claims": "درخواست‌های اولیه بیمه بیکاری",
    "Continuing Jobless Claims": "درخواست‌های مستمر بیمه بیکاری",
    "CPI m/m": "شاخص قیمت مصرف‌کننده ماهانه",
    "Core CPI m/m": "شاخص قیمت مصرف‌کننده هسته ماهانه",
    "CPI y/y": "شاخص قیمت مصرف‌کننده سالانه",
    "Core CPI y/y": "شاخص قیمت مصرف‌کننده هسته سالانه",
    "PPI m/m": "شاخص قیمت تولیدکننده ماهانه",
    "Core PPI m/m": "شاخص قیمت تولیدکننده هسته ماهانه",
    "PPI y/y": "شاخص قیمت تولیدکننده سالانه",
    "GDP m/m": "تولید ناخالص داخلی ماهانه",
    "GDP q/q": "رشد تولید ناخالص داخلی فصلی",
    "GDP y/y": "رشد تولید ناخالص داخلی سالانه",
    "GDP 3m/3m": "تولید ناخالص داخلی سه‌ماهه",
    "Retail Sales m/m": "فروش خرده‌فروشی ماهانه",
    "Core Retail Sales m/m": "فروش خرده‌فروشی هسته ماهانه",
    "Industrial Production m/m": "تولید صنعتی ماهانه",
    "Industrial Production y/y": "تولید صنعتی سالانه",
    "Manufacturing Production m/m": "تولید کارخانه‌ای ماهانه",
    "Manufacturing Production y/y": "تولید کارخانه‌ای سالانه",
    "Construction Output m/m": "تولید ساختمانی ماهانه",
    "Construction Output y/y": "تولید ساختمانی سالانه",
    "Index of Services": "شاخص خدمات",
    "Balance of Trade": "تراز تجاری",
    "BusinessNZ Manufacturing Index": "شاخص تولید BusinessNZ",
    "BSI Large Manufacturing": "شاخص BSI تولیدکنندگان بزرگ",
    "BSI Manufacturing Index": "شاخص تولید BSI",
    "BoJ Corporate Goods Price Index m/m": "شاخص قیمت کالاهای شرکتی بانک ژاپن ماهانه",
    "BoJ Corporate Goods Price Index y/y": "شاخص قیمت کالاهای شرکتی بانک ژاپن سالانه",
    "Manufacturing PMI": "شاخص مدیران خرید تولیدی",
    "Services PMI": "شاخص مدیران خرید خدمات",
    "PMI": "شاخص مدیران خرید",
    "Consumer Confidence": "اعتماد مصرف‌کننده",
    "Consumer Sentiment": "احساسات مصرف‌کننده",
    "Consumer Price Index": "شاخص قیمت مصرف‌کننده",
    "Producer Price Index": "شاخص قیمت تولیدکننده",
    "Interest Rate Decision": "تصمیم نرخ بهره",
    "Main Refinancing Rate": "نرخ اصلی بازتأمین مالی",
    "Monetary Policy Statement": "بیانیه سیاست پولی",
    "ECB Press Conference": "کنفرانس خبری بانک مرکزی اروپا",
    "FOMC Statement": "بیانیه کمیته بازار آزاد فدرال رزرو",
    "FOMC Meeting Minutes": "صورت‌جلسه کمیته بازار آزاد فدرال رزرو",
    "Fed Interest Rate Decision": "تصمیم نرخ بهره فدرال رزرو",
    "BOE Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی انگلیس",
    "BOJ Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی ژاپن",
    "RBA Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی استرالیا",
    "RBNZ Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی نیوزیلند",
    "Speaks": "سخنرانی مقام اقتصادی",
    "President Trump Speaks": "سخنرانی رئیس‌جمهور ترامپ",
    "Central Bank": "بانک مرکزی",
    "Trade Balance": "تراز تجاری",
    "Current Account": "حساب جاری",
    "Building Permits": "مجوزهای ساخت‌وساز",
    "Housing Starts": "شروع ساخت مسکن",
    "Durable Goods Orders": "سفارش کالاهای بادوام",
    "Factory Orders": "سفارش‌های کارخانه‌ای",
    "Existing Home Sales": "فروش خانه‌های موجود",
    "New Home Sales": "فروش خانه‌های جدید",
    "ISM Manufacturing PMI": "شاخص تولیدی ISM",
    "ISM Services PMI": "شاخص خدمات ISM",
    "ADP Non-Farm Employment Change": "تغییر اشتغال غیرکشاورزی ADP",
    "JOLTS Job Openings": "فرصت‌های شغلی JOLTS",
    "Average Hourly Earnings m/m": "میانگین دستمزد ساعتی ماهانه",
    "Personal Spending m/m": "مخارج شخصی ماهانه",
    "Personal Income m/m": "درآمد شخصی ماهانه",
}

TERM_MAP = {
    "Balance of Trade": "تراز تجاری",
    "Index of Services": "شاخص خدمات",
    "Industrial Production": "تولید صنعتی",
    "Manufacturing Production": "تولید کارخانه‌ای",
    "Construction Output": "تولید ساختمانی",
    "Corporate Goods Price Index": "شاخص قیمت کالاهای شرکتی",
    "BusinessNZ Manufacturing Index": "شاخص تولید BusinessNZ",
    "BSI Large Manufacturing": "شاخص BSI تولیدکنندگان بزرگ",
    "BSI Manufacturing Index": "شاخص تولید BSI",
    "Current Account": "حساب جاری",
    "Trade Balance": "تراز تجاری",
    "Press Conference": "کنفرانس خبری",
    "Interest Rate": "نرخ بهره",
    " m/m": " ماهانه",
    " y/y": " سالانه",
    " q/q": " فصلی",
    " 3m/3m": " سه‌ماهه",
    "Core": "هسته",
    "Final": "نهایی",
    "Prelim": "اولیه",
    "Preliminary": "اولیه",
    "Flash": "اولیه سریع",
    "Index": "شاخص",
    "Rate": "نرخ",
    "Statement": "بیانیه",
    "Sales": "فروش",
    "Orders": "سفارش‌ها",
    "Change": "تغییر",
    "Balance": "تراز",
    "Expectations": "انتظارات",
    "Forecast": "پیش‌بینی",
    "Previous": "قبلی",
    "Actual": "واقعی",
    "Estimate": "برآورد",
    "Minutes": "صورت‌جلسه",
    "Manufacturing": "تولید",
    "Production": "تولید",
    "Construction": "ساختمان",
    "Services": "خدمات",
    "Output": "خروجی",
    "GDP": "تولید ناخالص داخلی",
}
