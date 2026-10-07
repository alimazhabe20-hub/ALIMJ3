from typing import Any
from typing import Iterable

# Auto-split part 19: fuse_news
def fuse_news(items: Iterable[dict[str,Any]]) -> list[dict[str,Any]]:
    groups={}
    for x in items:
        title=str(x.get("title","")).strip(); key=re.sub(r"\W+"," ",title.lower()).strip()[:180]
        groups.setdefault(key,[]).append(x)
    return [{"title":k,"sources":len(v),"items":v,"impact":max(float(x.get("impact",0)) for x in v)} for k,v in groups.items()]
