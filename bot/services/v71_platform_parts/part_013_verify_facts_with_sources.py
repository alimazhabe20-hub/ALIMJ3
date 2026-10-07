# Auto-split part 13: verify_facts_with_sources
def verify_facts_with_sources(text:str, sources:dict[str,str]|None=None)->dict:
    claims=[x.strip() for x in re.split(r"(?<=[.!؟?])\s+",text.strip()) if len(x.strip())>20][:12]
    sources=sources or {}
    verified=[]
    for claim in claims:
        key=hashlib.sha256(claim.encode()).hexdigest()[:12]
        matched=[url for url,body in sources.items() if any(tok.lower() in body.lower() for tok in re.findall(r"[A-Za-z\u0600-\u06ff]{5,}",claim)[:5])]
        verified.append({"id":key,"claim":claim,"sources":matched[:5],"status":"supported" if matched else "needs_source"})
    return {"verified":bool(verified) and all(x["status"]=="supported" for x in verified),"claims":verified}
