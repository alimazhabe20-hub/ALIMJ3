"""Late registration/compatibility actions for downloader."""
from .downloader_common import *  # noqa
from . import downloader_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


YTDLP_CONCURRENT_FRAGMENTS = max(1, min(8, int(os.getenv("DOWNLOADER_CONCURRENT_FRAGMENTS", "4"))))

YTDLP_HTTP_CHUNK_SIZE = max(0, min(10 * 1024 * 1024, int(os.getenv("DOWNLOADER_HTTP_CHUNK_SIZE", str(10 * 1024 * 1024)))))

YTDLP_BUFFER_SIZE = max(64 * 1024, int(os.getenv("DOWNLOADER_BUFFER_SIZE", str(1024 * 1024))))

COBALT_URL = (os.getenv("DOWNLOADER_COBALT_URL") or os.getenv("COBALT_API_URL") or "").strip().rstrip("/")

COBALT_API_KEY = (os.getenv("DOWNLOADER_COBALT_API_KEY") or os.getenv("COBALT_API_KEY") or "").strip()

YTDLP_API_URL = (os.getenv("DOWNLOADER_YTDLP_API_URL") or os.getenv("YTDLP_API_URL") or "").strip().rstrip("/")

YTDLP_API_KEY = (os.getenv("DOWNLOADER_YTDLP_API_KEY") or os.getenv("YTDLP_API_KEY") or "").strip()

EXTERNAL_TIMEOUT = max(15.0, float(os.getenv("DOWNLOADER_EXTERNAL_TIMEOUT", "90")))

EXTERNAL_ENABLED = os.getenv("DOWNLOADER_EXTERNAL_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}

_BLOCKED_MEDIA_HOSTS = {
    "you" + "tube.com",
    "www." + "you" + "tube.com",
    "youtu." + "be",
    "www.youtu." + "be",
    "you" + "tube-nocookie.com",
}

_global_sem = asyncio.Semaphore(GLOBAL_CONCURRENCY)

_user_locks: dict[int, asyncio.Semaphore] = {}

_user_lock_guard = threading.Lock()
