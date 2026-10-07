from typing import Any

# Auto-split part 26: validate_workflow
def validate_workflow(steps: list[dict[str,Any]]) -> tuple[bool,str]:
    if len(steps)>MAX_STEPS: return False,"too_many_steps"
    if any(str(x.get("tool","")) in {"run_workflow","workflow_execute"} for x in steps): return False,"nested_workflow"
    return True,"ok"
