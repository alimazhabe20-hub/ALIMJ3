# Auto-split part 39: provider_health
def provider_health(name:str,ok:bool,latency_ms:float=0)->None:
    p=_PROVIDERS.setdefault(name,{"capabilities":set(),"weight":1.0,"failures":0,"latency":0.0,"enabled":True});p["latency"]=float(latency_ms);p["failures"]=max(0,p["failures"]+(0 if ok else 1));p["enabled"]=p["failures"]<5
