from typing import Any
from typing import Iterable

# Auto-split part 15: verify_claim
def verify_claim(claim: str, evidence: Iterable[str]) -> dict[str,Any]:
    tokens={x for x in re.findall(r"\w{4,}",claim.lower())}; ev=" ".join(map(str,evidence)).lower(); matched=sum(x in ev for x in tokens)
    confidence=matched/max(1,len(tokens)); return {"claim":redact(claim,1000),"supported":confidence>=0.5,"confidence":round(confidence,3)}
