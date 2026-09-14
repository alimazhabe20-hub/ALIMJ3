# Auto-split part 3: calculator
def calculator(expr: str) -> str:
    t = expr.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩×÷", "01234567890123456789*/"))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 200 or not t or not re.fullmatch(r"[0-9+\-*/().%\s]+", t):
        return "❌ عبارت نامعتبر. مثال: 2+3*4"
    try:
        tree = ast.parse(t, mode="eval")
        result = _safe_calc(tree)
        return f"🔢 نتیجه: {pn(result)}"
    except Exception:
        return "❌ عبارت نامعتبر. مثال: 2+3*4"
