# Auto-split part 1: _get_usd_rial
async def _get_usd_rial() -> int | None:
    return await _tgju_price("price_dollar_rl")
