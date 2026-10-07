"""finance: analysis responsibilities."""
from .finance_common import *  # noqa: F401,F403
from . import finance_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def analyze_crypto(*args, **kwargs):
    from bot.features.market.finance_crypto import analyze_crypto as _fn
    return await _fn(*args, **kwargs)

async def analyze_gold(*args, **kwargs):
    from bot.features.market.finance_crypto import analyze_gold as _fn
    return await _fn(*args, **kwargs)

async def get_gold_chart(*args, **kwargs):
    from bot.features.market.finance_crypto import get_gold_chart as _fn
    return await _fn(*args, **kwargs)

def _default_guide(*args, **kwargs):
    from bot.features.market.finance_crypto import _default_guide as _fn
    return _fn(*args, **kwargs)

def _build_smart_summary_pair(*args, **kwargs):
    from bot.features.market.finance_crypto import _build_smart_summary_pair as _fn
    return _fn(*args, **kwargs)

def _build_smart_summary(*args, **kwargs):
    from bot.features.market.finance_crypto import _build_smart_summary as _fn
    return _fn(*args, **kwargs)

async def _fetch_klines_for_ta(*args, **kwargs):
    from bot.features.market.finance_ta import _fetch_klines_for_ta as _fn
    return await _fn(*args, **kwargs)

def _sma(*args, **kwargs):
    from bot.features.market.finance_ta import _sma as _fn
    return _fn(*args, **kwargs)

def _rsi(*args, **kwargs):
    from bot.features.market.finance_ta import _rsi as _fn
    return _fn(*args, **kwargs)

def _adx_approx(*args, **kwargs):
    from bot.features.market.finance_ta import _adx_approx as _fn
    return _fn(*args, **kwargs)

def _compute_ta(*args, **kwargs):
    from bot.features.market.finance_ta import _compute_ta as _fn
    return _fn(*args, **kwargs)

def _atr(*args, **kwargs):
    from bot.features.market.finance_ta import _atr as _fn
    return _fn(*args, **kwargs)

def _detect_candle_patterns(*args, **kwargs):
    from bot.features.market.finance_ta import _detect_candle_patterns as _fn
    return _fn(*args, **kwargs)

def _score_timeframe(*args, **kwargs):
    from bot.features.market.finance_ta import _score_timeframe as _fn
    return _fn(*args, **kwargs)

async def _mtf_bundle(*args, **kwargs):
    from bot.features.market.finance_ta import _mtf_bundle as _fn
    return await _fn(*args, **kwargs)

def _market_structure(*args, **kwargs):
    from bot.features.market.finance_ta import _market_structure as _fn
    return _fn(*args, **kwargs)

def _rsi_divergence(*args, **kwargs):
    from bot.features.market.finance_ta import _rsi_divergence as _fn
    return _fn(*args, **kwargs)

def _volume_breakout(*args, **kwargs):
    from bot.features.market.finance_ta import _volume_breakout as _fn
    return _fn(*args, **kwargs)

def _demand_supply_zone(*args, **kwargs):
    from bot.features.market.finance_ta import _demand_supply_zone as _fn
    return _fn(*args, **kwargs)

def _price_action_analysis(*args, **kwargs):
    from bot.features.market.finance_ta import _price_action_analysis as _fn
    return _fn(*args, **kwargs)

def _advanced_levels(*args, **kwargs):
    from bot.features.market.finance_ta import _advanced_levels as _fn
    return _fn(*args, **kwargs)

def _market_regime(*args, **kwargs):
    from bot.features.market.finance_ta import _market_regime as _fn
    return _fn(*args, **kwargs)

def _professional_score(*args, **kwargs):
    from bot.features.market.finance_ta import _professional_score as _fn
    return _fn(*args, **kwargs)

def _mtf_convergence(*args, **kwargs):
    from bot.features.market.finance_ta import _mtf_convergence as _fn
    return _fn(*args, **kwargs)

def _scenarios(signal, support, resistance, current, atr) -> list:
    """سناریو A/B با احتمال تقریبی"""
    lines = []
    try:
        cur = float(current) if current is not None else None
        sup = float(support) if support is not None else None
        res = float(resistance) if resistance is not None else None
        a = float(atr) if atr else None
    except Exception:
        return ["سناریو: داده ناکافی"]
    if "لانگ" in (signal or ""):
        lines.append(f"سناریو A (~۶۰٪): نگه داشتن بالای {sup or 'حمایت'} و حرکت به {res or 'مقاومت'}")
        lines.append(f"سناریو B (~۴۰٪): از دست رفتن حمایت و برگشت تا {(sup - a) if (sup and a) else 'پایین‌تر'}")
    elif "شورت" in (signal or ""):
        lines.append(f"سناریو A (~۶۰٪): رد شدن از {res or 'مقاومت'} و حرکت به {sup or 'حمایت'}")
        lines.append(f"سناریو B (~۴۰٪): شکست مقاومت و ادامه تا {(res + a) if (res and a) else 'بالاتر'}")
    else:
        lines.append("سناریو A (~۵۰٪): ادامه رنج بین حمایت و مقاومت")
        lines.append("سناریو B (~۵۰٪): شکست یکی از دو سمت با حجم و شروع روند")
    return lines
