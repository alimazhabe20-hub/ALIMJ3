from typing import Any

# Auto-split part 22: validate_workflow
def validate_workflow(steps: list[dict[str, Any]]) -> tuple[bool,str]:
    if not isinstance(steps,list) or not steps: return False,"workflow_empty"
    if len(steps)>MAX_WORKFLOW_STEPS: return False,"workflow_too_long"
    for i,s in enumerate(steps,1):
        if not isinstance(s,dict) or not str(s.get("tool") or "").strip(): return False,f"invalid_step_{i}"
        if s.get("tool") == "run_workflow": return False,"nested_workflow"
    return True,"ok"
