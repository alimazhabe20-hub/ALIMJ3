from typing import Any

# Auto-split part 16: score_news
def score_news(title: str, content: str = "") -> dict[str, Any]:
    text=(title+" "+content).lower()
    positive=sum(x in text for x in ("surge","gain","growth","bullish","افزایش","رشد","مثبت"))
    negative=sum(x in text for x in ("crash","drop","loss","bearish","کاهش","سقوط","منفی"))
    sentiment=(positive-negative)/max(1,positive+negative)
    impact=min(1.0, (len(re.findall(r"!|عاجل|breaking|urgent", text, re.I))*0.2)+0.2)
    return {"sentiment":round(sentiment,3),"impact":round(impact,3),"label":"positive" if sentiment>0.2 else "negative" if sentiment<-0.2 else "neutral"}
