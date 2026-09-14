from typing import List

# Auto-split part 9: make_chart_image
def make_chart_image(
    title: str,
    labels: List[str],
    values: List[float],
    chart_type: str = "bar",
) -> bytes:
    """ساخت تصویر نمودار PNG با matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError("matplotlib نصب نیست. به requirements اضافه کن: matplotlib") from e

    if not labels or not values or len(labels) != len(values):
        raise RuntimeError("برای نمودار به برچسب و عدد هم‌تعداد نیاز است.")

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    chart_type = (chart_type or "bar").lower()
    if chart_type == "line":
        ax.plot(labels, values, marker="o", linewidth=2)
    elif chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    else:
        ax.bar(labels, values, color="#3b82f6")
        ax.tick_params(axis="x", rotation=30)

    if chart_type != "pie":
        ax.set_title(title or "نمودار")
        ax.grid(True, axis="y", alpha=0.3)
    else:
        ax.set_title(title or "نمودار")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
