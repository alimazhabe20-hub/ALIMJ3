"""ابزارها — ماشین‌حساب، پسورد، شمارش متن، فاصله جهانی"""
import re
import math
import ast
import operator
import asyncio
import secrets
import string
import httpx
from bot.logger import logger

# ===== merged from bot/features/tools/app_tools_parts/features_tools_app_tools_parts_part_001_pn.py =====
# Auto-split part 1: pn
def pn(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

# ===== end merged part =====


_CALC_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_CALC_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _calc_fact(n):
    n = int(n)
    if n < 0 or n > 170:
        raise ValueError("fact range 0..170")
    return math.factorial(n)


_CALC_FUNCS = {
    "sqrt": lambda x: math.sqrt(x),
    "cbrt": lambda x: x ** (1 / 3) if x >= 0 else -((-x) ** (1 / 3)),
    "sin": lambda x: math.sin(math.radians(x)),  # درجه
    "cos": lambda x: math.cos(math.radians(x)),
    "tan": lambda x: math.tan(math.radians(x)),
    "asin": lambda x: math.degrees(math.asin(x)),
    "acos": lambda x: math.degrees(math.acos(x)),
    "atan": lambda x: math.degrees(math.atan(x)),
    "sind": lambda x: math.sin(math.radians(x)),
    "cosd": lambda x: math.cos(math.radians(x)),
    "tand": lambda x: math.tan(math.radians(x)),
    "sinr": math.sin,  # رادیان
    "cosr": math.cos,
    "tanr": math.tan,
    "log": math.log10,
    "log10": math.log10,
    "ln": math.log,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "fabs": math.fabs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": lambda x, n=0: round(x, int(n)),
    "trunc": math.trunc,
    "fact": _calc_fact,
    "factorial": _calc_fact,
    "pow": lambda a, b: a ** b,
    "min": min,
    "max": max,
    "hypot": math.hypot,
    "degrees": math.degrees,
    "radians": math.radians,
    "pct": lambda a, b: (a / 100.0) * b,  # pct(20, 500) = 20% از 500
    "percent": lambda a, b: (a / 100.0) * b,
}

_CALC_CONSTS = {
    "pi": math.pi,
    "π": math.pi,
    "e": math.e,
    "phi": (1 + math.sqrt(5)) / 2,
    "tau": math.tau,
}


def _safe_calc(node: ast.AST, depth: int = 0):
    if depth > 40:
        raise ValueError("expression too deep")
    if isinstance(node, ast.Expression):
        return _safe_calc(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        if abs(node.value) > 10 ** 100:
            raise ValueError("number too large")
        return float(node.value) if isinstance(node.value, float) else node.value
    # Python 3.8 compat Num
    if hasattr(ast, "Num") and isinstance(node, ast.Num):  # pragma: no cover
        if abs(node.n) > 10 ** 100:
            raise ValueError("number too large")
        return node.n
    if isinstance(node, ast.UnaryOp) and type(node.op) in _CALC_UNARY:
        return _CALC_UNARY[type(node.op)](_safe_calc(node.operand, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_BINOPS:
        left = _safe_calc(node.left, depth + 1)
        right = _safe_calc(node.right, depth + 1)
        if isinstance(node.op, ast.Pow):
            if abs(float(right)) > 1000 or (abs(float(left)) > 1e6 and abs(float(right)) > 10):
                raise ValueError("power too large")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and float(right) == 0:
            raise ZeroDivisionError("division by zero")
        result = _CALC_BINOPS[type(node.op)](left, right)
        if isinstance(result, complex):
            raise ValueError("complex not supported")
        if isinstance(result, (int, float)) and abs(result) > 10 ** 100:
            raise ValueError("result too large")
        return result
    if isinstance(node, ast.Name):
        key = node.id.lower() if node.id.isascii() else node.id
        if key in _CALC_CONSTS:
            return _CALC_CONSTS[key]
        if node.id in _CALC_CONSTS:
            return _CALC_CONSTS[node.id]
        raise ValueError(f"unknown name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("unsupported call")
        fname = node.func.id.lower()
        if fname not in _CALC_FUNCS:
            raise ValueError(f"unknown function: {fname}")
        if len(node.args) > 3 or node.keywords:
            raise ValueError("bad arguments")
        args = [_safe_calc(a, depth + 1) for a in node.args]
        result = _CALC_FUNCS[fname](*args)
        if isinstance(result, complex):
            raise ValueError("complex not supported")
        return result
    raise ValueError("unsupported expression")


def _format_number(result) -> str:
    if isinstance(result, bool):
        return str(result)
    if isinstance(result, int) or (isinstance(result, float) and result == int(result) and abs(result) < 1e15):
        iv = int(result)
        return pn(f"{iv:,}")
    if isinstance(result, float):
        if abs(result) >= 1e12 or (abs(result) < 1e-6 and result != 0):
            s = f"{result:.8g}"
        else:
            s = f"{result:.10f}".rstrip("0").rstrip(".")
        return pn(s)
    return pn(str(result))


def _preprocess_expr(expr: str) -> str:
    """نرمال‌سازی ورودی فارسی و نمادهای رایج."""
    t = expr.strip()
    t = t.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩×÷٫",
        "01234567890123456789*/.",
    ))
    # درصد تکی: 25% → (25/100)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", t)
    # توان: 2^3 → 2**3
    t = t.replace("^", "**")
    # رادیکال ساده: √9 یا sqrt
    t = t.replace("√", "sqrt")
    t = t.replace("π", "pi")
    # فاصله‌ها
    t = re.sub(r"\s+", "", t)
    # ضرب ضمنی ساده: 2pi → 2*pi ، 2(3+1) → 2*(3+1)
    t = re.sub(r"(\d)(pi|e|phi|tau|sqrt|sin|cos|tan|log|ln|abs|fact)\b", r"\1*\2", t, flags=re.I)
    t = re.sub(r"(\d)\(", r"\1*(", t)
    t = re.sub(r"\)(\d)", r")*\1", t)
    t = re.sub(r"\)(\()", r")*(", t)
    return t


def calculator(expr: str) -> str:
    """ماشین‌حساب پیشرفته و امن با توابع ریاضی."""
    if not expr or not str(expr).strip():
        return chr(10).join([
            '🔢 **ماشین\u200cحساب هوشمند**',
            '',
            'عبارت ریاضی را بفرستید.',
            '',
            '📌 عملگرها: +  -  *  /  **  ^  %  ()',
            '📌 توابع: sqrt sin cos tan log ln abs floor ceil fact pct round',
            '📌 ثابت\u200cها: pi  e  tau  phi',
            '',
            'مثال\u200cها:',
            '• 2+3*4',
            '• (10+5)/3',
            '• 2^8',
            '• sqrt(144)',
            '• sin(30)     ← درجه',
            '• log(1000) · ln(e)',
            '• fact(6)',
            '• pi*5^2     ← مساحت دایره r=5',
            '• pct(20,500) ← ۲۰٪ از ۵۰۰',
            '• ۲۵×۴',
        ])

    raw = str(expr).strip()
    t = _preprocess_expr(raw)

    if len(t) > 300:
        return "❌ عبارت خیلی طولانی است."
    if not re.fullmatch(r"[0-9+*/().%,a-zA-Z_\-]+", t):
        return chr(10).join([
            "❌ عبارت نامعتبر است.",
            "",
            "عملگرها: + - * / ** ^ % ()",
            "توابع: sqrt sin cos tan log ln abs floor ceil fact pct",
            "ثابت‌ها: pi e",
            "مثال: sqrt(2)*pi",
        ])

    try:
        tree = ast.parse(t, mode="eval")
        result = _safe_calc(tree)
        out = _format_number(result)
        lines = [
            "🔢 **نتیجه**",
            "────────────────────",
            f"📥 ورودی: `{raw}`",
            f"📤 خروجی: **{out}**",
        ]
        try:
            fv = float(result)
            if abs(fv) >= 1e9 or (0 < abs(fv) < 1e-4):
                lines.append(f"🔬 علمی: {pn(f'{fv:.6e}')}")
        except Exception:
            pass
        lines.append("────────────────────")
        lines.append("💡 عبارت بعدی را بفرستید (یا از منو خارج شوید).")
        return chr(10).join(lines)
    except ZeroDivisionError:
        return "❌ تقسیم بر صفر مجاز نیست."
    except Exception as e:
        logger.debug("calculator error: %s | expr=%s", e, raw)
        return chr(10).join([
            "❌ محاسبه ممکن نشد.",
            "",
            "مثال: 15*1.09 | (100-20)/4 | 2^10 | sqrt(81) | sin(90) | pct(15,200000)",
        ])


def generate_password(length: int = 16) -> str:
    length = max(6, min(64, length))
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_005_count_text.py =====
# Auto-split part 5: count_text
def count_text(text: str) -> str:
    """شمارش متن — UI مرتب و کامل‌تر."""
    import re as _re
    if text is None:
        text = ""
    chars = len(text)
    chars_no_space = len(text.replace(" ", "").replace(chr(10), "").replace(chr(9), ""))
    words = len([w for w in text.split() if w.strip()])
    lines_n = text.count(chr(10)) + (1 if text else 0)
    raw_paras = text.strip().split(chr(10)+chr(10)) if text.strip() else []
    paras = len([p for p in raw_paras if p.strip()])
    fa = len(_re.findall("[\u0600-\u06ff]", text))
    en = len(_re.findall("[A-Za-z]", text))
    digits = len(_re.findall("[0-9]", text))
    lang = "فارسی" if fa >= en else ("انگلیسی" if en > 0 else "—")
    return chr(10).join([
        "📝  **شمارش متن**",
        "・ ・ ・ ・ ・",
        "",
        f"🔤  کاراکتر (با فاصله): **{pn(chars)}**",
        f"🔡  کاراکتر (بدون فاصله): **{pn(chars_no_space)}**",
        f"📖  کلمه: **{pn(words)}**",
        f"📄  خط: **{pn(lines_n)}**",
        f"📦  پاراگراف: **{pn(paras)}**",
        "",
        f"🌍  زبان غالب: {lang}",
        f"🔢  رقم: {pn(digits)}",
        "",
        "・ ・ ・ ・ ・",
        "💡 متن دیگری بفرست تا دوباره بشمارم.",
    ])


# ===== end merged part =====

# ——— فاصله جهانی ———
_geo_cache = {}

# مکان‌های از پیش‌تعریف‌شده: کلید normalized → (lat, lon, "نمایش")
KNOWN_PLACES = {
    # ایران
    "تهران": (35.6892, 51.3890, "تهران، ایران"),
    "tehran": (35.6892, 51.3890, "تهران، ایران"),
    "قم": (34.6416, 50.8746, "قم، ایران"),
    "qom": (34.6416, 50.8746, "قم، ایران"),
    "مشهد": (36.2605, 59.6168, "مشهد، ایران"),
    "mashhad": (36.2605, 59.6168, "مشهد، ایران"),
    "اصفهان": (32.6546, 51.6680, "اصفهان، ایران"),
    "isfahan": (32.6546, 51.6680, "اصفهان، ایران"),
    "esfahan": (32.6546, 51.6680, "اصفهان، ایران"),
    "شیراز": (29.5918, 52.5837, "شیراز، ایران"),
    "shiraz": (29.5918, 52.5837, "شیراز، ایران"),
    "تبریز": (38.0962, 46.2738, "تبریز، ایران"),
    "tabriz": (38.0962, 46.2738, "تبریز، ایران"),
    "اهواز": (31.3183, 48.6706, "اهواز، ایران"),
    "کرمان": (30.2832, 57.0788, "کرمان، ایران"),
    "یزد": (31.8974, 54.3569, "یزد، ایران"),
    "رشت": (37.2808, 49.5832, "رشت، ایران"),
    "کرج": (35.8400, 50.9391, "کرج، ایران"),
    "همدان": (34.7992, 48.5146, "همدان، ایران"),
    "ارومیه": (37.5527, 45.0761, "ارومیه، ایران"),
    "کرمانشاه": (34.3142, 47.0650, "کرمانشاه، ایران"),
    "بندرعباس": (27.1832, 56.2666, "بندرعباس، ایران"),
    "زاهدان": (29.4963, 60.8629, "زاهدان، ایران"),
    "ساری": (36.5633, 53.0601, "ساری، ایران"),
    "اردبیل": (38.2498, 48.2933, "اردبیل، ایران"),
    "بوشهر": (28.9234, 50.8203, "بوشهر، ایران"),
    "خرم آباد": (33.4878, 48.3558, "خرم‌آباد، ایران"),
    "خرم‌آباد": (33.4878, 48.3558, "خرم‌آباد، ایران"),
    "سنندج": (35.3219, 46.9862, "سنندج، ایران"),
    "قزوین": (36.2797, 50.0049, "قزوین، ایران"),
    "زنجان": (36.6769, 48.4963, "زنجان، ایران"),
    "گرگان": (36.8427, 54.4439, "گرگان، ایران"),
    "ایلام": (33.6374, 46.4227, "ایلام، ایران"),
    "شهرکرد": (32.3256, 50.8644, "شهرکرد، ایران"),
    "یاسوج": (30.6684, 51.5876, "یاسوج، ایران"),
    "بیرجند": (32.8663, 59.2211, "بیرجند، ایران"),
    "بجنورد": (37.4747, 57.3290, "بجنورد، ایران"),
    "سمنان": (35.5769, 53.3953, "سمنان، ایران"),
    "کیش": (26.5570, 53.9800, "کیش، ایران"),
    "قشم": (26.9581, 56.2719, "قشم، ایران"),
    # عراق
    "کربلا": (32.6160, 44.0240, "کربلا، عراق"),
    "کربلاء": (32.6160, 44.0240, "کربلا، عراق"),
    "karbala": (32.6160, 44.0240, "کربلا، عراق"),
    "نجف": (31.9996, 44.3333, "نجف، عراق"),
    "najaf": (31.9996, 44.3333, "نجف، عراق"),
    "بغداد": (33.3152, 44.3661, "بغداد، عراق"),
    "baghdad": (33.3152, 44.3661, "بغداد، عراق"),
    "کاظمین": (33.3803, 44.3419, "کاظمین، عراق"),
    "سامرا": (34.1959, 43.8730, "سامرا، عراق"),
    "بصره": (30.5081, 47.7835, "بصره، عراق"),
    "موصل": (36.3350, 43.1189, "موصل، عراق"),
    "اربیل": (36.1911, 44.0094, "اربیل، عراق"),
    # عربستان
    "مکه": (21.4225, 39.8262, "مکه، عربستان"),
    "مکه مکرمه": (21.4225, 39.8262, "مکه، عربستان"),
    "mecca": (21.4225, 39.8262, "مکه، عربستان"),
    "مدینه": (24.4672, 39.6111, "مدینه، عربستان"),
    "مدینه منوره": (24.4672, 39.6111, "مدینه، عربستان"),
    "medina": (24.4672, 39.6111, "مدینه، عربستان"),
    "ریاض": (24.7136, 46.6753, "ریاض، عربستان"),
    "جده": (21.4858, 39.1925, "جده، عربستان"),
    "jeddah": (21.4858, 39.1925, "جده، عربستان"),
    # منطقه
    "دمشق": (33.5138, 36.2765, "دمشق، سوریه"),
    "حلب": (36.2021, 37.1343, "حلب، سوریه"),
    "بیروت": (33.8938, 35.5018, "بیروت، لبنان"),
    "استانبول": (41.0082, 28.9784, "استانبول، ترکیه"),
    "istanbul": (41.0082, 28.9784, "استانبول، ترکیه"),
    "آنکارا": (39.9334, 32.8597, "آنکارا، ترکیه"),
    "ankara": (39.9334, 32.8597, "آنکارا، ترکیه"),
    "دبی": (25.2048, 55.2708, "دبی، امارات"),
    "dubai": (25.2048, 55.2708, "دبی، امارات"),
    "ابوظبی": (24.4539, 54.3773, "ابوظبی، امارات"),
    "کابل": (34.5553, 69.2075, "کابل، افغانستان"),
    "هرات": (34.3482, 62.1997, "هرات، افغانستان"),
    # جهان
    "پاریس": (48.8566, 2.3522, "پاریس، فرانسه"),
    "paris": (48.8566, 2.3522, "پاریس، فرانسه"),
    "لندن": (51.5074, -0.1278, "لندن، انگلیس"),
    "london": (51.5074, -0.1278, "لندن، انگلیس"),
    "نیویورک": (40.7128, -74.0060, "نیویورک، آمریکا"),
    "new york": (40.7128, -74.0060, "نیویورک، آمریکا"),
    "tokyo": (35.6762, 139.6503, "توکیو، ژاپن"),
    "توکیو": (35.6762, 139.6503, "توکیو، ژاپن"),
    "مسکو": (55.7558, 37.6173, "مسکو، روسیه"),
    "moscow": (55.7558, 37.6173, "مسکو، روسیه"),
    "پکن": (39.9042, 116.4074, "پکن، چین"),
    "beijing": (39.9042, 116.4074, "پکن، چین"),
    "دهلی": (28.6139, 77.2090, "دهلی نو، هند"),
    "سیدنی": (-33.8688, 151.2093, "سیدنی، استرالیا"),
    "sydney": (-33.8688, 151.2093, "سیدنی، استرالیا"),
    "تورنتو": (43.6532, -79.3832, "تورنتو، کانادا"),
    "برلین": (52.5200, 13.4050, "برلین، آلمان"),
    "berlin": (52.5200, 13.4050, "برلین، آلمان"),
    "مادرید": (40.4168, -3.7038, "مادرید، اسپانیا"),
    "رم": (41.9028, 12.4964, "رم، ایتالیا"),
    "rome": (41.9028, 12.4964, "رم، ایتالیا"),
    "قاهره": (30.0444, 31.2357, "قاهره، مصر"),
    "cairo": (30.0444, 31.2357, "قاهره، مصر"),
}

# کشورها → مرکز/پایتخت تقریبی
COUNTRY_CENTERS = {
    "ایران": (32.4279, 53.6880, "ایران (مرکز)"),
    "iran": (32.4279, 53.6880, "ایران (مرکز)"),
    "ترکیه": (39.9334, 32.8597, "ترکیه (آنکارا)"),
    "turkey": (39.9334, 32.8597, "ترکیه (آنکارا)"),
    "عراق": (33.3152, 44.3661, "عراق (بغداد)"),
    "iraq": (33.3152, 44.3661, "عراق (بغداد)"),
    "عربستان": (24.7136, 46.6753, "عربستان (ریاض)"),
    "saudi arabia": (24.7136, 46.6753, "عربستان (ریاض)"),
    "امارات": (25.2048, 55.2708, "امارات (دبی)"),
    "آمریکا": (38.9072, -77.0369, "آمریکا (واشنگتن)"),
    "usa": (38.9072, -77.0369, "آمریکا (واشنگتن)"),
    "united states": (38.9072, -77.0369, "آمریکا (واشنگتن)"),
    "چین": (39.9042, 116.4074, "چین (پکن)"),
    "china": (39.9042, 116.4074, "چین (پکن)"),
    "روسیه": (55.7558, 37.6173, "روسیه (مسکو)"),
    "russia": (55.7558, 37.6173, "روسیه (مسکو)"),
    "هند": (28.6139, 77.2090, "هند (دهلی)"),
    "india": (28.6139, 77.2090, "هند (دهلی)"),
    "آلمان": (52.5200, 13.4050, "آلمان (برلین)"),
    "germany": (52.5200, 13.4050, "آلمان (برلین)"),
    "فرانسه": (48.8566, 2.3522, "فرانسه (پاریس)"),
    "france": (48.8566, 2.3522, "فرانسه (پاریس)"),
    "انگلیس": (51.5074, -0.1278, "انگلیس (لندن)"),
    "england": (51.5074, -0.1278, "انگلیس (لندن)"),
    "uk": (51.5074, -0.1278, "انگلیس (لندن)"),
    "ژاپن": (35.6762, 139.6503, "ژاپن (توکیو)"),
    "japan": (35.6762, 139.6503, "ژاپن (توکیو)"),
    "افغانستان": (34.5553, 69.2075, "افغانستان (کابل)"),
    "پاکستان": (33.6844, 73.0479, "پاکستان (اسلام‌آباد)"),
    "سوریه": (33.5138, 36.2765, "سوریه (دمشق)"),
    "لبنان": (33.8938, 35.5018, "لبنان (بیروت)"),
}

# ===== merged from bot/features/tools/app_tools_parts/part_006__norm_place.py =====
# Auto-split part 6: _norm_place
def _norm_place(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("‌", " ").replace("  ", " ")
    return s.strip().lower()

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_007__short_name.py =====
# Auto-split part 7: _short_name
def _short_name(display_name: str, place_hint: str = "") -> str:
    if not display_name:
        return place_hint or "?"
    parts = [p.strip() for p in str(display_name).split(",") if p.strip()]
    if not parts:
        return place_hint or "?"
    skip = ("بخش", "شهرستان", "استان", "دهستان", "روستا", "county", "province",
            "district", "village", "region", "oblast", "governorate", "municipality")
    cleaned = []
    for p in parts:
        low = p.lower()
        if any(sw in low for sw in skip):
            continue
        if re.match(r"^[\d\s\-]+$", p):
            continue
        cleaned.append(p)
    if not cleaned:
        cleaned = parts[:2]
    if len(cleaned) >= 2:
        return f"{cleaned[0]}، {cleaned[-1]}"
    return cleaned[0]

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_008_geocode.py =====
# Auto-split part 8: geocode
async def geocode(place: str):
    """(lat, lon, display_name) یا None"""
    place_raw = (place or "").strip()
    if not place_raw:
        return None
    key = _norm_place(place_raw)
    if key in _geo_cache:
        return _geo_cache[key]

    # ۱) لیست داخلی — فقط match دقیق
    if key in KNOWN_PLACES:
        lat, lon, short = KNOWN_PLACES[key]
        _geo_cache[key] = (lat, lon, short)
        return lat, lon, short
    if key in COUNTRY_CENTERS:
        lat, lon, short = COUNTRY_CENTERS[key]
        _geo_cache[key] = (lat, lon, short)
        return lat, lon, short

    headers = {"User-Agent": "ALIMJBot/2.2 (telegram-bot; distance)"}
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # ۲) Open-Meteo Geocoding (دقیق و پایدار)
            try:
                r = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": place_raw, "count": 5, "language": "fa"},
                )
                if r.status_code == 200:
                    results = (r.json() or {}).get("results") or []
                    if results:
                        # ترجیح ایران/منطقه اگر چند نتیجه
                        best = results[0]
                        for item in results:
                            cc = (item.get("country_code") or "").upper()
                            if cc in ("IR", "IQ", "TR", "AF", "SA", "AE", "SY", "LB"):
                                # اگر کوئری فارسی است اولویت خاورمیانه
                                if any("\u0600" <= ch <= "\u06FF" for ch in place_raw):
                                    best = item
                                    break
                        lat = float(best["latitude"])
                        lon = float(best["longitude"])
                        name = best.get("name") or place_raw
                        country = best.get("country") or ""
                        short = f"{name}، {country}" if country else name
                        _geo_cache[key] = (lat, lon, short)
                        return lat, lon, short
            except Exception as e:
                logger.warning(f"open-meteo geo: {e}")

            # ۳) Nominatim
            queries = [place_raw]
            if not any(x in key for x in ("iran", "ایران", ",")):
                queries.append(f"{place_raw}, Iran")
            for q in queries:
                try:
                    r = await client.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={
                            "q": q,
                            "format": "json",
                            "limit": 5,
                            "accept-language": "fa,en",
                        },
                    )
                    if r.status_code != 200:
                        continue
                    results = r.json() or []
                    if not results:
                        continue

                    def score(item):
                        t = (item.get("type") or "").lower()
                        cls = (item.get("class") or "").lower()
                        imp = float(item.get("importance") or 0)
                        bonus = 0
                        if t in ("city", "town", "municipality", "administrative", "country", "state"):
                            bonus += 3
                        if cls in ("place", "boundary"):
                            bonus += 1
                        dn = (item.get("display_name") or "").lower()
                        if any(x in dn for x in ("village", "hamlet", "روستا", "دهستان", "بخش")):
                            bonus -= 4
                        return imp + bonus

                    results.sort(key=score, reverse=True)
                    best = results[0]
                    lat = float(best["lat"])
                    lon = float(best["lon"])
                    short = _short_name(best.get("display_name") or place_raw, place_raw)
                    _geo_cache[key] = (lat, lon, short)
                    return lat, lon, short
                except Exception:
                    continue

            # ۴) Photon
            try:
                r = await client.get(
                    "https://photon.komoot.io/api/",
                    params={"q": place_raw, "limit": 3},
                )
                if r.status_code == 200:
                    for f in (r.json() or {}).get("features") or []:
                        coords = f.get("geometry", {}).get("coordinates") or []
                        props = f.get("properties") or {}
                        if len(coords) < 2:
                            continue
                        nm = props.get("name") or place_raw
                        country = props.get("country") or ""
                        city = props.get("city") or props.get("state") or nm
                        short = f"{city}، {country}" if country else city
                        _geo_cache[key] = (float(coords[1]), float(coords[0]), short)
                        return _geo_cache[key]
            except Exception:
                pass
    except Exception as e:
        logger.error(f"geocode [{place_raw}]: {e}")
    return None

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_009_haversine.py =====
# Auto-split part 9: haversine
def haversine(lat1, lon1, lat2, lon2):
    """فاصله خط مستقیم روی کره زمین (کیلومتر) — دقیق"""
    R = 6371.0088  # میانگین شعاع زمین
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_010__fmt_duration.py =====
# Auto-split part 10: _fmt_duration
def _fmt_duration(hours: float) -> str:
    if hours is None or hours < 0:
        return "—"
    if hours < 0.02:
        return "کمتر از ۱ دقیقه"
    if hours < 1:
        return f"{pn(int(hours * 60))} دقیقه"
    h = int(hours)
    m = int((hours - h) * 60)
    if h >= 24:
        d, h2 = h // 24, h % 24
        return f"{pn(d)} روز و {pn(h2)} ساعت" if h2 else f"{pn(d)} روز"
    return f"{pn(h)} ساعت و {pn(m)} دقیقه" if m else f"{pn(h)} ساعت"

# ===== end merged part =====

# نام‌های چندکلمه‌ای معروف برای پارس
_MULTIWORD = sorted(
    [k for k in list(KNOWN_PLACES.keys()) + list(COUNTRY_CENTERS.keys()) if " " in k],
    key=len,
    reverse=True,
)

# ===== merged from bot/features/tools/app_tools_parts/part_011_parse_two_places.py =====
# Auto-split part 11: parse_two_places
def parse_two_places(text: str):
    """استخراج دو مکان از متن کاربر — دقیق‌تر از قبل"""
    t = (text or "").strip()
    if not t:
        return None

    # جداکننده‌های صریح
    for sep in [
        " تا ", " به ", " -> ", " → ", " — ", " – ",
        " to ", " - ", "\t", "،", ",",
    ]:
        if sep in t:
            a, b = [p.strip() for p in t.split(sep, 1)]
            if a and b:
                return a, b

    # اگر کل متن دو مکان معروف پشت‌سرهم باشد
    low = _norm_place(t)
    # چندکلمه‌ای از ابتدا
    for mw in _MULTIWORD:
        if low.startswith(mw + " "):
            rest = t[len(mw):].strip() if len(t) >= len(mw) else ""
            # try original length match approximately
            rest = low[len(mw):].strip()
            if rest:
                return mw, rest
        if low.endswith(" " + mw):
            first = low[: -len(mw)].strip()
            if first:
                return first, mw

    # دو توکن فارسی/انگلیسی ساده
    parts = t.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 3:
        # احتمال: New York London  یا  تهران شهرکرد ؟
        # امتحان 2+1 و 1+2
        return None  # بهتر است کاربر جداکننده بگذارد
    if len(parts) == 4:
        return f"{parts[0]} {parts[1]}", f"{parts[2]} {parts[3]}"
    if len(parts) > 2:
        mid = len(parts) // 2
        return " ".join(parts[:mid]), " ".join(parts[mid:])
    return None

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_012__osrm_driving.py =====
# Auto-split part 12: _osrm_driving
async def _osrm_driving(lat1, lon1, lat2, lon2):
    """فاصله جاده‌ای رایگان با OSRM — ممکن است برای بعضی مسیرها None باشد"""
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(url, params={"overview": "false"})
            if r.status_code != 200:
                return None
            js = r.json() or {}
            if js.get("code") != "Ok":
                return None
            routes = js.get("routes") or []
            if not routes:
                return None
            meters = float(routes[0].get("distance") or 0)
            seconds = float(routes[0].get("duration") or 0)
            return meters / 1000.0, seconds / 3600.0
    except Exception as e:
        logger.warning(f"osrm: {e}")
        return None

# ===== end merged part =====

# ===== merged from bot/features/tools/app_tools_parts/part_013_world_distance.py =====
# Auto-split part 13: world_distance
async def world_distance(place1: str, place2: str = None) -> str:
    if place2 is None:
        parsed = parse_two_places(place1)
        if not parsed:
            return (
                "❌ دو مکان بنویسید.\n\n"
                "مثال‌ها:\n"
                "• تهران تا مشهد\n"
                "• قم کربلا\n"
                "• تهران تا ترکیه\n"
                "• Paris to Tokyo\n"
                "• New York to London"
            )
        place1, place2 = parsed

    place1, place2 = place1.strip(), place2.strip()
    g1, g2 = await asyncio.gather(geocode(place1), geocode(place2))
    if not g1:
        return f"❌ «{place1}» پیدا نشد.\nنام شهر یا کشور را دقیق‌تر بنویسید."
    if not g2:
        return f"❌ «{place2}» پیدا نشد.\nنام شهر یا کشور را دقیق‌تر بنویسید."

    lat1, lon1, n1 = g1
    lat2, lon2, n2 = g2
    km = haversine(lat1, lon1, lat2, lon2)
    miles = km * 0.621371

    if km < 0.05:
        return (
            f"🗺 فاصله جهانی\n\n"
            f"از: {n1}\nتا: {n2}\n\n"
            f"📏 این دو نقطه تقریباً یکی هستند (کمتر از ۵۰ متر)."
        )

    # فاصله جاده‌ای (اختیاری)
    driving_info = ""
    try:
        from bot.config import config
        gkey = getattr(config, "GOOGLE_MAPS_API_KEY", "") or ""
        if gkey:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(
                    "https://maps.googleapis.com/maps/api/distancematrix/json",
                    params={
                        "origins": f"{lat1},{lon1}",
                        "destinations": f"{lat2},{lon2}",
                        "mode": "driving",
                        "language": "fa",
                        "units": "metric",
                        "key": gkey,
                    },
                )
                if r.status_code == 200:
                    el = ((r.json().get("rows") or [{}])[0].get("elements") or [{}])[0]
                    if el.get("status") == "OK":
                        dist_txt = (el.get("distance") or {}).get("text", "")
                        dur_txt = (el.get("duration") or {}).get("text", "")
                        if dist_txt:
                            driving_info = f"🚗 جاده (گوگل): {dist_txt} — حدود {dur_txt}\n"
        if not driving_info and km < 3000:
            osrm = await _osrm_driving(lat1, lon1, lat2, lon2)
            if osrm:
                d_km, d_hr = osrm
                driving_info = (
                    f"🚗 جاده (تقریبی OSRM): {pn(f'{d_km:,.0f}')} کیلومتر — "
                    f"حدود {_fmt_duration(d_hr)}\n"
                )
    except Exception as e:
        logger.warning(f"driving: {e}")

    return (
        f"🗺 فاصله جهانی\n\n"
        f"📍 از: {n1}\n"
        f"📍 تا: {n2}\n\n"
        f"📏 خط مستقیم (هوایی):\n"
        f"   {pn(f'{km:,.1f}')} کیلومتر\n"
        f"   {pn(f'{miles:,.1f}')} مایل\n\n"
        f"{driving_info}"
        f"⏱ زمان تقریبی با خط مستقیم:\n"
        f"🚗 خودرو (~۸۰km/h): {_fmt_duration(km / 80)}\n"
        f"✈️ هواپیما: {_fmt_duration(km / 800 + 0.5)}\n"
        f"🚶 پیاده: {_fmt_duration(km / 5)}\n\n"
        f"📌 مختصات:\n"
        f"{n1}: {lat1:.4f}, {lon1:.4f}\n"
        f"{n2}: {lat2:.4f}, {lon2:.4f}"
    )

# ===== end merged part =====
