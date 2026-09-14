# Auto-split part 5: get_joke_categories
def get_joke_categories() -> dict:
    """برگرداندن {key: label} دسته‌ها"""
    data = _load_jokes()
    return data.get("labels", {})
