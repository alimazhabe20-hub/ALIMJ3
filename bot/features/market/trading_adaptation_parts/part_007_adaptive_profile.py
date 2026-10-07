# Auto-split part 7: adaptive_profile
def adaptive_profile(symbol, regime="", setup="default", min_samples=12) -> dict:
    d=_load(); key=f"{str(symbol).upper()}|{regime or 'نامشخص'}|{setup or 'default'}"
    st=d.get("stats",{}).get(key,{}); n=int(st.get("samples",0))
    return {"samples":n,"win_rate":st.get("win_rate"),"avg_return":st.get("avg_return"),
            "ready":n>=min_samples,"kill": n>=20 and float(st.get("win_rate",50))<35}
