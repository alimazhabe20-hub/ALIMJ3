from typing import Any
from typing import Iterable

# Auto-split part 17: rag_search
def rag_search(query: str, chunks: Iterable[str], limit: int=5) -> list[dict[str,Any]]:
    q=set(re.findall(r"\w{2,}",query.lower())); scored=[]
    for ch in chunks:
        words=set(re.findall(r"\w{2,}",str(ch).lower())); score=len(q&words)/max(1,len(q)); scored.append({"text":str(ch)[:4000],"score":round(score,4)})
    return sorted(scored,key=lambda x:x["score"],reverse=True)[:max(1,min(20,int(limit)))]
