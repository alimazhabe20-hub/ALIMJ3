from typing import Any

# Auto-split part 14: rag_rank
def rag_rank(query: str, chunks: list[str], top_k: int = 5) -> list[dict[str, Any]]:
    terms=set(re.findall(r"\w+", (query or "").lower()))
    scored=[]
    for i, chunk in enumerate(chunks):
        words=re.findall(r"\w+", chunk.lower()); counts=Counter(words)
        score=sum(min(3, counts[t]) for t in terms) / max(1, len(terms))
        scored.append({"index":i,"score":round(score,4),"text":chunk})
    return sorted(scored,key=lambda x:(-x["score"],x["index"]))[:max(1,min(20,int(top_k)))]
