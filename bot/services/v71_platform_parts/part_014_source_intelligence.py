# Auto-split part 14: source_intelligence
def source_intelligence(urls:list[str])->dict:
    out=[]
    for url in urls[:30]:
        try:
            from urllib.parse import urlparse
            p=urlparse(url); host=(p.hostname or "").lower(); out.append({"url":url,"domain":host,"https":p.scheme=="https"})
        except Exception: pass
    return {"sources":out,"unique_domains":sorted({x["domain"] for x in out if x["domain"]})}
