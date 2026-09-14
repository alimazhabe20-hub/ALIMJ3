# Auto-split part 10: detect_language
def detect_language(text:str)->str:
    t=text or ""
    ar=len(re.findall(r"[\u0621-\u0638\u0660-\u0669]",t)); fa=len(re.findall(r"[\u067e\u0686\u0698\u06af\u06cc]",t)); en=len(re.findall(r"[A-Za-z]",t))
    if ar and not fa: return "ar"
    if fa or (ar and re.search(r"[یکگپچژ]",t)): return "fa"
    if en: return "en"
    return "fa"
