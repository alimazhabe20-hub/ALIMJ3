# Auto-split part 15: _price_action_analysis
def _price_action_analysis(opens, highs, lows, closes, vols, support=None, resistance=None, atr=None):
    """تحلیل Price Action + الگوهای کلاسیک؛ خروجی خالیِ الگو یعنی چیزی با اطمینان کافی دیده نشده."""
    if len(closes)<30:
        return {'valid':False,'patterns':[],'chart_patterns':[]}
    patterns=_detect_candle_patterns(opens, highs, lows, closes)
    chart_patterns=_detect_chart_patterns(highs,lows,closes,atr)
    struct=_market_structure(highs,lows,closes)
    vol_ratio=None
    if len(vols)>=20:
        av=sum(vols[-20:])/20
        vol_ratio=vols[-1]/av if av else 1.0
    location='میانه رنج'
    cur=closes[-1]
    if support and cur <= support*1.01: location='نزدیک حمایت'
    elif resistance and cur >= resistance*0.99: location='نزدیک مقاومت'
    breakout=None
    if resistance and cur>resistance: breakout='شکست مقاومت'
    elif support and cur<support: breakout='شکست حمایت'
    score=5
    if struct.get('structure','').startswith('صعودی'): score+=1
    elif struct.get('structure','').startswith('نزولی'): score-=1
    return {
        'valid':True,'patterns':patterns,'chart_patterns':chart_patterns,
        'structure':struct.get('structure','رنج'),'bos_choch':struct.get('bos'),
        'liquidity_sweep':None,'equal_highs':None,'equal_lows':None,
        'location':location,'breakout':breakout,'impulse_state':'نرمال',
        'volume_ratio':vol_ratio,'score':max(1,min(10,score)),
    }
