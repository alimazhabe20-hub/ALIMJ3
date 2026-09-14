# Auto-split part 3: hafez_fal
async def hafez_fal(user_id: int = 0) -> str:
    """
    فال حافظ — شبیه hafez.taktemp.com
    نیت → دعا → غزل کامل → تفسیر
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://api.ganjoor.net/api/ganjoor/hafez/faal")
            if r.status_code == 200:
                data = r.json() or {}
                title = data.get("title") or "غزل حافظ"
                full_title = data.get("fullTitle") or title
                verses = data.get("verses") or []
                body = _format_verses(verses) if verses else (data.get("plainText") or "").replace("\r\n", "\n\n")
                # تفسیر: خلاصه هوش‌مصنوعی گنجور
                meaning = (data.get("poemSummary") or "").strip()
                if not meaning:
                    # از coupletSummary اولین بیت
                    for v in verses:
                        if isinstance(v, dict) and v.get("coupletSummary"):
                            meaning = v["coupletSummary"]
                            break
                if meaning.startswith("هوش مصنوعی:"):
                    meaning = meaning.replace("هوش مصنوعی:", "", 1).strip()

                if body:
                    parts = [
                        "🔮 **فال حافظ**",
                        "",
                        "نیت کنید…",
                        "",
                        f"📿 {HAFEZ_OPENING}",
                        "",
                        "━━━━━━━━━━━━━━━━━━━━",
                        f"📖 **{title}**",
                        f"_{full_title}_" if full_title != title else "",
                        "",
                        body.strip(),
                        "",
                    ]
                    if meaning:
                        parts.extend([
                            "━━━━━━━━━━━━━━━━━━━━",
                            "💡 **تفسیر فال**",
                            "",
                            meaning[:900],
                            "",
                        ])
                    parts.append("🕯️ برای شادی روح حافظ، صلوات یا فاتحه‌ای نثار کنید.")
                    return "\n".join(p for p in parts if p is not None)
    except Exception as e:
        logger.error(f"hafez api: {e}")

    title, body, advice = random.choice(HAFEZ_LOCAL)
    return (
        f"🔮 **فال حافظ**\n\n"
        f"نیت کنید…\n\n"
        f"📿 {HAFEZ_OPENING}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **{title}**\n\n"
        f"{body}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **تفسیر فال**\n\n"
        f"{advice}\n\n"
        f"🕯️ برای شادی روح حافظ، صلوات یا فاتحه‌ای نثار کنید."
    )
