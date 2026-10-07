from typing import Any
from typing import Iterable

# Auto-split part 53: rank_sources
def rank_sources(items: Iterable[dict[str,Any]], query: str="") -> list[dict[str,Any]]:
    seen=set();out=[];terms=set(re.findall(r"\w{3,}",query.lower()))
    for raw in list(items)[:200]:
        x=dict(raw);url=str(x.get("url","")).strip();title=str(x.get("title","")).strip();key=hashlib.sha256((url or title).lower().encode()).hexdigest()
        if key in seen:continue
        seen.add(key);text=(title+" "+str(x.get("content", ""))).lower();match=sum(t in text for t in terms);trust=float(x.get("trust",0) or 0)+(0.1 if url.startswith("https://") else 0);x.update(score=round(match+trust,3),untrusted=True);out.append(x)
    return sorted(out,key=lambda x:x["score"],reverse=True)
