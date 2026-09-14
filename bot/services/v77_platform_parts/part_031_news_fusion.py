from typing import Any
from typing import Iterable

# Auto-split part 31: news_fusion
def news_fusion(items: Iterable[dict[str,Any]]) -> list[dict[str,Any]]:
    groups: dict[str,list[dict[str,Any]]]={}
    for raw in items:
        x=dict(raw); title=re.sub(r"\W+"," ",str(x.get("title","")).lower()).strip(); words=set(title.split()); key=" ".join(sorted(words))[:220] or hashlib.sha1(str(x).encode()).hexdigest()[:12]
        groups.setdefault(key,[]).append(x)
    out=[]
    for key,group in groups.items():
        text=" ".join(str(x.get("title","")).lower()+" "+str(x.get("content","")).lower() for x in group); pos=sum(w in text for w in _POS); neg=sum(w in text for w in _NEG); sentiment="positive" if pos>neg else "negative" if neg>pos else "neutral"
        out.append({"canonical_key":key,"title":group[0].get("title",key),"sources":len(group),"items":group,"sentiment":sentiment,"impact":round(max([float(x.get("impact",0) or 0) for x in group]+[0]),3),"confidence":round(min(1,.35+.12*len(group)),3)})
    return sorted(out,key=lambda x:(-x["impact"],-x["sources"]))
