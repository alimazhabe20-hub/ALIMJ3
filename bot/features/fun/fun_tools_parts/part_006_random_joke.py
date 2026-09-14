# Auto-split part 6: random_joke
def random_joke(category: str = None, user_id: int = None) -> str:
    """جوک تصادفی — برای هر کاربر تکراری نمی‌فرستد"""
    import hashlib
    data = _load_jokes()
    jokes_map = data.get("jokes", {})
    labels = data.get("labels", {})

    if category and category in jokes_map and jokes_map[category]:
        pool = list(jokes_map[category])
        label = labels.get(category, category)
    else:
        pool = []
        for lst in jokes_map.values():
            pool.extend(lst)
        label = "تصادفی"

    if not pool:
        return "جوکی موجود نیست."

    # حذف جوک‌هایی که این کاربر قبلاً دیده
    if user_id:
        try:
            from bot.database import get_sent_joke_hashes, mark_joke_sent, reset_sent_jokes
            seen = get_sent_joke_hashes(user_id)
            fresh = [j for j in pool if hashlib.md5(j.encode("utf-8")).hexdigest() not in seen]
            if not fresh:
                # همه را دیده — از نو شروع کن
                reset_sent_jokes(user_id)
                fresh = pool
            text = random.choice(fresh)
            mark_joke_sent(user_id, hashlib.md5(text.encode("utf-8")).hexdigest())
        except Exception:
            text = random.choice(pool)
    else:
        text = random.choice(pool)

    return f"😂 **جوک ({label})**\n\n{text}"
