"""Late registration/compatibility actions for economic_calendar."""
from .economic_calendar_common import *  # noqa
from . import economic_calendar_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_EN_ABBR = (
    ("Non-Farm Employment Change", "NFP"),
    ("Non-Farm Payrolls", "NFP"),
    ("ADP Non-Farm Employment Change", "ADP NFP"),
    ("Quarterly Unemployment Rate", "Unemp Rate q/q"),
    ("Unemployment Rate", "Unemp Rate"),
    ("Initial Jobless Claims", "Init Claims"),
    ("Continuing Jobless Claims", "Cont Claims"),
    ("Balance of Trade", "Trade Bal"),
    ("Trade Balance", "Trade Bal"),
    ("Current Account", "Curr Acct"),
    ("Index of Services", "Svc Idx"),
    ("Industrial Production", "Ind Prod"),
    ("Manufacturing Production", "Mfg Prod"),
    ("Construction Output", "Const Out"),
    ("Corporate Goods Price Index", "CGPI"),
    ("BusinessNZ Manufacturing Index", "BNZ Mfg"),
    ("BSI Large Manufacturing", "BSI Large Mfg"),
    ("BSI Manufacturing Index", "BSI Mfg"),
    ("Consumer Price Index", "CPI"),
    ("Producer Price Index", "PPI"),
    ("Consumer Confidence", "Cons Conf"),
    ("Consumer Sentiment", "Cons Sent"),
    ("Retail Sales", "Retail"),
    ("Interest Rate Decision", "Rate Dec"),
    ("Monetary Policy Statement", "MPS"),
    ("Press Conference", "Press Conf"),
    ("Building Permits", "Bldg Perm"),
    ("Housing Starts", "Hous Start"),
    ("Durable Goods Orders", "Dur Goods"),
    ("Factory Orders", "Fact Orders"),
    ("Existing Home Sales", "Exist Home"),
    ("New Home Sales", "New Home"),
    ("Average Hourly Earnings", "AHE"),
    ("Personal Spending", "Pers Spend"),
    ("Personal Income", "Pers Inc"),
    ("JOLTS Job Openings", "JOLTS"),
    ("Manufacturing PMI", "Mfg PMI"),
    ("Services PMI", "Svc PMI"),
    ("ISM Manufacturing PMI", "ISM Mfg"),
    ("ISM Services PMI", "ISM Svc"),
)

FF_HTML_URLS = (
    "https://calendar.forexfactory.com/calendar?week=this",
    "https://www.forexfactory.com/calendar?week=this",
    "https://mds-wss.forexfactory.com/calendar?week=this",
    "https://calendar.forexfactory.com/calendar?week=next",
    "https://www.forexfactory.com/calendar?week=next",
)

FF_DAILY_HTML_HOSTS = (
    "https://calendar.forexfactory.com/calendar",
    "https://www.forexfactory.com/calendar",
    "https://mds-wss.forexfactory.com/calendar",
)

BIQUOTE_URL = "https://biquote.io/api/calendar"
