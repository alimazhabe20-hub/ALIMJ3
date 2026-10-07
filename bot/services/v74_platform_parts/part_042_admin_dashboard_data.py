from typing import Any

# Auto-split part 42: admin_dashboard_data
def admin_dashboard_data() -> dict[str, Any]:
    data=observability_snapshot()
    # Never return filesystem paths, tokens, raw URLs containing credentials, or raw exceptions.
    return json.loads(redact_secrets(json.dumps(data, ensure_ascii=False)))
