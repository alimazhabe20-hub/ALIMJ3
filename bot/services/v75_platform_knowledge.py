"""v75_platform: knowledge responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def rank_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set(); out = []
    for item in items or []:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        key = stable_hash(url or title.lower())
        if key in seen: continue
        seen.add(key)
        trust = float(item.get("trust", 0) or 0)
        if url.startswith("https://"): trust += 0.1
        item = dict(item); item["trust_score"] = round(min(1.0, trust), 3)
        out.append(item)
    return sorted(out, key=lambda x: (-x["trust_score"], x.get("title", "")))

def rag_chunk(text: str, *, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    chunk_size = max(200, min(3000, int(chunk_size))); overlap = max(0, min(chunk_size//2, int(overlap)))
    chunks=[]; start=0
    while start < len(text):
        end=min(len(text), start+chunk_size); chunks.append(text[start:end])
        if end == len(text): break
        start=max(start+1, end-overlap)
    return chunks

def rag_rank(query: str, chunks: list[str], top_k: int = 5) -> list[dict[str, Any]]:
    terms=set(re.findall(r"\w+", (query or "").lower()))
    scored=[]
    for i, chunk in enumerate(chunks):
        words=re.findall(r"\w+", chunk.lower()); counts=Counter(words)
        score=sum(min(3, counts[t]) for t in terms) / max(1, len(terms))
        scored.append({"index":i,"score":round(score,4),"text":chunk})
    return sorted(scored,key=lambda x:(-x["score"],x["index"]))[:max(1,min(20,int(top_k)))]

def score_news(title: str, content: str = "") -> dict[str, Any]:
    text=(title+" "+content).lower()
    positive=sum(x in text for x in ("surge","gain","growth","bullish","افزایش","رشد","مثبت"))
    negative=sum(x in text for x in ("crash","drop","loss","bearish","کاهش","سقوط","منفی"))
    sentiment=(positive-negative)/max(1,positive+negative)
    impact=min(1.0, (len(re.findall(r"!|عاجل|breaking|urgent", text, re.I))*0.2)+0.2)
    return {"sentiment":round(sentiment,3),"impact":round(impact,3),"label":"positive" if sentiment>0.2 else "negative" if sentiment<-0.2 else "neutral"}

def economic_surprise(actual: str, forecast: str) -> dict[str, Any]:
    def num(x):
        m=re.search(r"[-+]?\d+(?:\.\d+)?",str(x or "")); return float(m.group()) if m else None
    a,f=num(actual),num(forecast)
    if a is None or f is None: return {"available":False,"score":0,"direction":"unknown"}
    diff=a-f; scale=max(1,abs(f)); score=max(-1,min(1,diff/scale))
    return {"available":True,"difference":round(diff,6),"score":round(score,4),"direction":"above" if diff>0 else "below" if diff<0 else "inline"}
