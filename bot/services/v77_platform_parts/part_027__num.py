from typing import Any
from typing import Iterable

# Auto-split part 27: _num
def _num(values: Iterable[Any]) -> list[float]:
    out=[]
    for x in values:
        try: out.append(float(x))
        except (TypeError,ValueError): pass
    return out
