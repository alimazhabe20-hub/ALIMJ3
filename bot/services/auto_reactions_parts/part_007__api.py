# Auto-split part 7: _api
async def _api(token: str, method: str, data: dict) -> tuple[bool, dict]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        client = await _get_client()
        response = await client.post(url, data=data)
        try:
            payload = response.json()
        except Exception:
            payload = {"ok": False, "description": response.text[:300]}
        return response.status_code == 200 and bool(payload.get("ok")), payload
    except Exception as exc:
        return False, {"ok": False, "description": str(exc)}
