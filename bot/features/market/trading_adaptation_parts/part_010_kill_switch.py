# Auto-split part 10: kill_switch
def kill_switch(profile, gate_allowed=True) -> tuple[bool,str]:
    if not gate_allowed: return True,"گیت کیفیت فعال است"
    if profile.get("kill"): return True,"عملکرد تاریخی این ستاپ در این رژیم ضعیف است"
    return False,""
