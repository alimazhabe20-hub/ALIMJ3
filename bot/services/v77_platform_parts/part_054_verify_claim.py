from typing import Any
from typing import Iterable

# Auto-split part 54: verify_claim
def verify_claim(claim: str, evidence: Iterable[str]) -> dict[str,Any]:
    tokens=set(re.findall(r"\w{4,}",str(claim).lower()));ev=" ".join(map(str,evidence)).lower();matched=sum(t in ev for t in tokens);confidence=matched/max(1,len(tokens));return {"claim":redact(claim,1500),"supported":confidence>=.5,"confidence":round(confidence,3),"matched_terms":matched,"terms":len(tokens)}
