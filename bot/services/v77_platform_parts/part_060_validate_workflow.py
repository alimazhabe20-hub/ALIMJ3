from typing import Any

# Auto-split part 60: validate_workflow
def validate_workflow(steps: list[dict[str,Any]]) -> tuple[bool,str]:
    if not isinstance(steps,list) or len(steps)>MAX_STEPS:return False,"too_many_steps"
    if any(str(x.get("tool", "")) in {"run_workflow","workflow_execute"} for x in steps):return False,"nested_workflow"
    ids=[str(x.get("id",i)) for i,x in enumerate(steps)]
    if len(ids)!=len(set(ids)):return False,"duplicate_step_ids"
    return True,"ok"
